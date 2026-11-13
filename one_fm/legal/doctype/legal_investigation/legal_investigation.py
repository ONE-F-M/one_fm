# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.utils import get_link_to_form

from one_fm.processor import sendemail

# Field holding the issuing supervisor on each document an investigation can come from.
ISSUER_FIELD = {
	"Penalty": "issuer_employee",
	"Penalty Issuance": "issuing_employee",
	"HR Enquiry": "issuing_employee",
}


# The Initiate Legal Investigation process owns the lifecycle: states, session check,
# outcome and the Penalty created when the outcome is Penalty Applicable.
class LegalInvestigation(Document):
	def after_insert(self):
		self.validate_lead()
		self.notify_supervisor()

	def validate_lead(self):
		# The lead cannot be a party to the investigation.
		if self.investigation_lead and frappe.db.exists(
			"Legal Investigation Employees", {"parent": self.name, "employee_id": self.investigation_lead}
		):
			self.db_set({"investigation_lead": None, "lead_name": None})

	def notify_supervisor(self):
		issuer_field = ISSUER_FIELD.get(self.reference_doctype)
		if not issuer_field or not self.reference_docname:
			return

		supervisor = frappe.db.get_value(self.reference_doctype, self.reference_docname, issuer_field)
		supervisor_user = supervisor and frappe.db.get_value("Employee", supervisor, "user_id")
		if not supervisor_user:
			return

		subject = _("Legal Investigation opened from {0}: {1}").format(
			_(self.reference_doctype), self.reference_docname
		)
		message = _("Please review and add the necessary details.<br> Link: {0}").format(
			get_link_to_form(self.doctype, self.name)
		)
		sendemail(
			[supervisor_user],
			subject=subject,
			message=message,
			reference_doctype=self.doctype,
			reference_name=self.name,
		)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def filter_employees(doctype, txt, searchfield, start, page_len, filters):
	frappe.has_permission("Legal Investigation", "read", throw=True)
	Employees = DocType("Legal Investigation Employees")
	return (
		frappe.qb.from_(Employees)
		.select(Employees.employee_id, Employees.employee_name)
		.where(
			(Employees.parent == filters.get("name"))
			& (Employees.parenttype == filters.get("doctype"))
			& (Employees.employee_id.like(f"%{txt}%") | Employees.employee_name.like(f"%{txt}%"))
		)
		.limit(page_len)
		.offset(start)
	).run()
