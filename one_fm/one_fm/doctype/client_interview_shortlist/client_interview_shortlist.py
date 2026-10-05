# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, formatdate, getdate, today


class ClientInterviewShortlist(Document):
	def validate(self):
		self.validate_project_or_prospective_client()

	def validate_project_or_prospective_client(self):
		if self.is_prospective_client:
			if not self.prospective_client:
				frappe.throw(_("Prospective Client is required when 'Is Prospective Client' is checked."))
			self.project = None
		else:
			if not self.project:
				frappe.throw(_("Project is required when 'Is Prospective Client' is not checked."))
			self.prospective_client = None
			self.customer_name = None


def send_pending_operations_supervisor_reminder():
	"""Story 1: Send daily email reminder at 7:45 AM to the creator of Client Interview Shortlist
	documents that have been in 'Pending Operations Supervisor' state for more than 1 day."""
	cutoff_date = add_days(today(), -1)

	stale_docs = frappe.get_all(
		"Client Interview Shortlist",
		filters={
			"workflow_state": "Pending Operations Supervisor",
			"creation": ["<=", cutoff_date],
		},
		fields=["name", "owner", "creation"],
	)

	for doc in stale_docs:
		creator_email = frappe.db.get_value("User", doc.owner, "email")
		if not creator_email:
			continue

		creation_date = formatdate(getdate(doc.creation))
		subject = _(
			"Action Required: Client Interview Shortlist {0} is in Pending Operations Supervisor state"
		).format(doc.name)

		doc_link = frappe.utils.get_url_to_form("Client Interview Shortlist", doc.name)
		reminder_message = _(
			"Hello, this is an automated reminder. The Client Interview Shortlist {0} you created"
			" on {1} is currently in Pending Operations Supervisor state."
			" Please take necessary action."
		).format(doc.name, creation_date)

		msg_details = [
			{"label": _("Document Name"), "value": doc.name},
			{"label": _("Document Type"), "value": _("Client Interview Shortlist")},
			{
				"label": _("Description"),
				"value": reminder_message,
			},
			{
				"label": _("Document Link"),
				"value": '<a href="{0}">{0}</a>'.format(doc_link),
			},
		]

		table_html = """
		<table cellpadding="0" cellspacing="0" border="1" style="border-collapse: collapse; border: 1px solid #d1d8dd;">
			<tbody>
		"""
		for detail in msg_details:
			table_html += """
			<tr>
				<td style="padding: 10px; font-weight: bold; border: 1px solid #d1d8dd;">{label}</td>
				<td style="padding: 10px; border: 1px solid #d1d8dd;">{value}</td>
			</tr>
			""".format(label=detail["label"], value=detail["value"])
		table_html += "</tbody></table>"

		email_header = _("Pending Reminder on {0}").format(doc.name)

		try:
			frappe.sendmail(
				recipients=[creator_email],
				subject=subject,
				template="new_notification",
				args={
					"body_content": email_header,
					"description": table_html,
					"doc_link": doc_link,
				},
				header=[email_header, "orange"],
			)
		except Exception:
			frappe.log_error(
				title=_("Client Interview Shortlist Reminder Error"),
				message=frappe.get_traceback(),
			)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_prospective_client_list(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	"""Return Opportunity records for the Prospective Client link field.

	Excludes Opportunities with status Closed or Lost.
	Shows columns: Opportunity ID, Customer Name, Status, Opportunity Type.
	Supports searching by name and customer_name.
	"""
	from frappe.query_builder import DocType
	from frappe.query_builder.functions import Locate

	Opportunity = DocType("Opportunity")

	query = (
		frappe.qb.from_(Opportunity)
		.select(
			Opportunity.name,
			Opportunity.customer_name,
			Opportunity.status,
			Opportunity.opportunity_type,
		)
		.where(Opportunity.status.notin(["Closed", "Lost"]))
		.where(
			(Opportunity.name.like(f"%{txt}%"))
			| (Opportunity.customer_name.like(f"%{txt}%"))
		)
		.orderby(Locate(txt, Opportunity.name))
		.orderby(Opportunity.modified, order=frappe.qb.desc)
		.offset(start)
		.limit(page_len)
	)

	return query.run()
