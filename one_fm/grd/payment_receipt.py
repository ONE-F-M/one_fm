# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""Read the Payment Date from a government payment receipt PDF.

The receipts are text PDFs, so the text layer is read with pypdf and matched with
one regex rule per issuer. Image uploads have no text and are left for manual entry.
"""

import io
import re
import unicodedata
from datetime import datetime

import frappe
from frappe import _

RECEIPT_FIELDS = {
	"Work Permit": "attach_invoice",
	"Medical Insurance": "upload_medical_insurance",
	"Residency": "invoice_attachment",
	"PACI": "upload_civil_id_payment",
}

# Values are glued to the following text (e.g. "4:39 PM6277..."), so no word boundary after AM/PM.
DMY_12H = r"(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2})[:.](\d{2})\s*([AP]M)"
PACI_RULE = re.compile(r"Payment Date\s*" + DMY_12H)
DMY_12H_RULE = re.compile(DMY_12H)
# MOI prints time first, then date, sometimes with spaces around the hyphen.
MOI_RULE = re.compile(r"(\d{2}:\d{2}:\d{2})\s*-\s*(\d{4}-\d{2}-\d{2})")
# PAM K-Net payment section heading. The receipt also carries a print date in the same format.
PAM_KNET_HEADING = "تفاصيل دفع عن طريق الكي نت"


def receipt_text(content: bytes) -> str:
	from pypdf import PdfReader

	reader = PdfReader(io.BytesIO(content))
	text = "\n".join(page.extract_text() or "" for page in reader.pages)
	# pypdf returns Arabic presentation forms (U+FExx); NFKC maps them to plain letters.
	return unicodedata.normalize("NFKC", text)


def _dmy_12h(match: re.Match | None) -> str | None:
	if not match:
		return None
	date, hour, minute, meridiem = match.groups()
	value = datetime.strptime(f"{date} {hour}:{minute} {meridiem}", "%d/%m/%Y %I:%M %p")
	return value.strftime("%Y-%m-%d %H:%M:%S")


def payment_date_from_text(doctype: str, text: str) -> str | None:
	"""Return the payment date as "YYYY-MM-DD HH:MM:SS", or None when it is not found."""
	if not text:
		return None

	if doctype == "PACI":
		return _dmy_12h(PACI_RULE.search(text))

	if doctype == "Work Permit":
		start = text.find(PAM_KNET_HEADING)
		if start == -1:
			return None
		return _dmy_12h(DMY_12H_RULE.search(text, start))

	if doctype == "Medical Insurance":
		return _dmy_12h(DMY_12H_RULE.search(text))

	if doctype == "Residency":
		match = MOI_RULE.search(text)
		if not match:
			return None
		time, date = match.groups()
		return datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

	return None


@frappe.whitelist()
def read_payment_date(doctype: str, name: str, file_url: str) -> str | None:
	if doctype not in RECEIPT_FIELDS:
		frappe.throw(_("Payment Date cannot be read for {0}").format(doctype))

	frappe.get_doc(doctype, name).check_permission("write")

	# One receipt is often attached to several records, so match the attachment, not the URL alone.
	file_name = frappe.db.get_value(
		"File", {"file_url": file_url, "attached_to_doctype": doctype, "attached_to_name": name}
	)
	if not file_name:
		return None

	try:
		content = frappe.get_doc("File", file_name).get_content()
		# get_content decodes content that happens to be valid UTF-8.
		if isinstance(content, str):
			content = content.encode()
		return payment_date_from_text(doctype, receipt_text(content))
	except Exception:
		frappe.log_error(title=_("Payment receipt not read"))
		return None
