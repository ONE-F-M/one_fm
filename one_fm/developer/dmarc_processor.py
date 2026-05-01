import frappe
import imaplib
import email
import gzip
import zipfile
import io
import parsedmarc
from datetime import datetime, timedelta
from frappe.utils import get_datetime, now_datetime, cint, flt

# Maximum size for attachment payload (e.g. 10MB)
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
# Maximum size for decompressed XML (e.g. 50MB)
MAX_XML_SIZE = 50 * 1024 * 1024

@frappe.whitelist()
def fetch_and_process_dmarc_reports():
	"""
	Fetches DMARC aggregate reports using settings from ONEFM General Setting,
	parses them using parsedmarc, and creates DMARC Report records.
	"""
	# Security check
	frappe.only_for("System Manager")
	
	result_data = {
		"processed_count": 0,
		"status": "Success",
		"error": None
	}

	mail = None
	try:
		settings = frappe.get_single("ONEFM General Setting")
		
		# Point 3: Use get_password for presence check as well
		if not settings.email_account or not settings.get_password("email_password"):
			result_data["status"] = "Error"
			result_data["error"] = "DMARC email credentials are not configured in ONEFM General Setting."
			return result_data

		# Get credentials
		imap_host = settings.imap_host or "imap.gmail.com"
		imap_port = settings.imap_port or 993
		username = settings.email_account
		password = settings.get_password("email_password")
		
		# Connect to IMAP
		mail = imaplib.IMAP4_SSL(imap_host, int(imap_port))
		mail.login(username, password)
		
		# Select Inbox
		mail.select("INBOX")
		
		# Search for DMARC emails from the last 7 days using server-side SUBJECT filter
		date_str = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
		
		# IMAP server-side search: only fetch emails with "report" or "dmarc" in subject
		dmarc_ids = set()
		for keyword in ("report", "dmarc"):
			result, data = mail.search(None, f'(SINCE "{date_str}" SUBJECT "{keyword}")')
			if result == "OK" and data[0]:
				dmarc_ids.update(data[0].split())

		if not dmarc_ids:
			return result_data

		for num in sorted(dmarc_ids, reverse=True):
			result, msg_data = mail.fetch(num, '(RFC822)')
			if result != "OK":
				continue
				
			raw_email = msg_data[0][1]
			msg = email.message_from_bytes(raw_email)

				
			for part in msg.walk():
				if part.get_content_maintype() == "multipart":
					continue
				if part.get("Content-Disposition") is None:
					continue
					
				filename = part.get_filename()
				if filename and (filename.endswith(".gz") or filename.endswith(".zip")):
					payload = part.get_payload(decode=True)
					
					# Point 8: Size limit check
					if len(payload) > MAX_ATTACHMENT_SIZE:
						frappe.log_error(f"Attachment {filename} exceeds max size {MAX_ATTACHMENT_SIZE}", "DMARC Processor")
						continue

					xml_content = None
					
					if filename.endswith(".gz"):
						try:
							# Check decompressed size roughly if possible or just decompress safely
							# Gzip doesn't store uncompressed size easily in a way that's always reliable without reading
							decompressed = gzip.decompress(payload)
							if len(decompressed) > MAX_XML_SIZE:
								continue
							xml_content = decompressed.decode("utf-8")
						except Exception:
							continue
					elif filename.endswith(".zip"):
						try:
							with zipfile.ZipFile(io.BytesIO(payload)) as z:
								for z_info in z.infolist():
									if z_info.filename.endswith(".xml"):
										# Point 8: Check ZipInfo size
										if z_info.file_size > MAX_XML_SIZE:
											continue
										xml_content = z.read(z_info.filename).decode("utf-8")
										break
						except Exception:
							continue
					
					if xml_content:
						if process_xml_report(xml_content):
							result_data["processed_count"] += 1

		settings.db_set("last_fetch_time", now_datetime())

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "DMARC Processor Error")
		result_data["status"] = "Error"
		result_data["error"] = str(e)
	finally:
		# Point 7: Always logout
		if mail:
			try:
				mail.logout()
			except Exception:
				pass
	
	return result_data

def process_xml_report(xml_content):
	"""
	Parses the XML content and creates DMARC Report records.
	"""
	try:
		report = parsedmarc.parse_aggregate_report_xml(xml_content)
		
		def get_val(obj, key, default=None):
			if isinstance(obj, dict):
				return obj.get(key, default)
			return getattr(obj, key, default)

		report_meta = get_val(report, "report_metadata", {})
		report_id = get_val(report_meta, "report_id")
		
		if not report_id:
			return False
			
		if frappe.db.exists("DMARC Report", {"report_id": report_id}):
			return False
			
		policy_pub = get_val(report, "policy_published", {})
		
		doc = frappe.new_doc("DMARC Report")
		doc.report_id = report_id
		doc.org_name = get_val(report_meta, "org_name")
		doc.org_email = get_val(report_meta, "email")
		doc.domain = get_val(policy_pub, "domain")
		
		# Dates: parsedmarc flattens date_range into begin_date/end_date strings
		# directly on report_metadata (e.g. '2026-04-22 03:00:00')
		begin_str = get_val(report_meta, "begin_date")
		end_str = get_val(report_meta, "end_date")

		if begin_str:
			doc.begin_date = get_datetime(begin_str)
		if end_str:
			doc.end_date = get_datetime(end_str)

		doc.published_policy = get_val(policy_pub, "p")
		doc.published_spf_alignment = get_val(policy_pub, "aspf")
		doc.published_dkim_alignment = get_val(policy_pub, "adkim")
		doc.published_pct = get_val(policy_pub, "pct")
		doc.raw_xml = xml_content
		doc.status = "Processed"
		
		total_msgs = 0
		total_pass = 0
		total_fail = 0
		
		records = get_val(report, "records", [])
		for r in records:
			row = doc.append("records", {})
			
			source = get_val(r, "source", {})
			alignment = get_val(r, "alignment", {})
			policy_eval = get_val(r, "policy_evaluated", {})
			identifiers = get_val(r, "identifiers", {})
			
			row.source_ip = get_val(source, "ip_address")
			row.source_country = get_val(source, "country")
			row.source_reverse_dns = get_val(source, "reverse_dns")
			row.source_base_domain = get_val(source, "base_domain")
			
			row.message_count = get_val(r, "count", 0)
			row.disposition = get_val(policy_eval, "disposition")
			
			row.dkim_aligned = 1 if get_val(alignment, "dkim") else 0
			row.spf_aligned = 1 if get_val(alignment, "spf") else 0
			row.dmarc_aligned = 1 if get_val(alignment, "dmarc") else 0
			
			row.dkim_result = get_val(policy_eval, "dkim")
			row.spf_result = get_val(policy_eval, "spf")
			
			row.header_from = get_val(identifiers, "header_from")
			row.envelope_from = get_val(identifiers, "envelope_from")
			
			overrides = get_val(policy_eval, "policy_override_reasons", [])
			if overrides:
				row.policy_override_reasons = ", ".join(overrides)
			
			total_msgs += row.message_count
			if row.dmarc_aligned:
				total_pass += row.message_count
			else:
				total_fail += row.message_count
				
		doc.total_messages = total_msgs
		doc.total_pass = total_pass
		doc.total_fail = total_fail
		if total_msgs > 0:
			doc.pass_rate = (total_pass / total_msgs) * 100
			
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
		return True
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "DMARC XML Parsing Error")
		return False
