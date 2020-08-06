# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import get_link_to_form, nowdate, getdate, now_datetime

class LegalInvestigation(Document):
	def after_insert(self):
		self.validate_lead()
		self.notify_supervisor()

	def validate_lead(self):
		investigation_employees = frappe.db.sql("""
			SELECT employee_id
			FROM `tabLegal Investigation Employees`
			WHERE
				parent="{legal_inv}"
			AND employee_id="{inv_lead}"	
		""".format(legal_inv=self.name, inv_lead=self.investigation_lead))

		if len(investigation_employees) > 0:
			self.db_set("investigation_lead", None)
			self.db_set("lead_name", None)

	def notify_supervisor(self):
		supervisor= frappe.get_value("Penalty", self.penalty_code, ["issuer_employee"])
		supervisor_user = frappe.get_value("Employee", supervisor, "user_id")
		link = get_link_to_form(self.doctype, self.name)
		subject = _("Legal Investigation opened for Penalty: {penalty}".format(penalty=self.penalty_code))
		message = _("Please review and add the necessary details.<br> Link: {link}".format(link=link))
		frappe.sendmail([supervisor_user], subject=subject, message=message, reference_doctype=self.doctype, reference_name=self.name)


	def on_update(self):
		if self.workflow_state == "Investigation Completed":
			self.validate_results_and_sessions()
			self.end_date = nowdate()
			self.validate_penalty_details()
			self.issue_penalty()

	def validate_penalty_details(self):
		for penalty in self.legal_investigation_penalty:
			date = getdate(penalty.penalty_occurence_time)
			if not frappe.db.exists("Shift Assignment", {"date": date, "employee": penalty.employee_id, "shift": penalty.shift}):
				frappe.throw(_("Please check the penalty occurence details. Shift assignment for {name}:{employee_id} does not match for selected date in Row {idx}"
							.format(name=penalty.employee_name, employee_id=penalty.employee_id, idx=penalty.idx)))

	def validate_results_and_sessions(self):
		if self.investigation_results is None:
			frappe.throw(_("Investigations results field cannot be empty. Please update investigation results."))
		if len(self.session_summary) == 0 or len(frappe.get_all("Legal Investigation Session", {"legal_investigation_code": self.name})) == 0:
			frappe.throw(_("Cannot complete Legal investigation. No Legal Investigation session conducted."))
			
	def issue_penalty(self):
		for penalty in self.legal_investigation_penalty:
			penalty_issuance = frappe.new_doc("Penalty Issuance")
			penalty_issuance.issuing_time = now_datetime()
			penalty_issuance.penalty_location = penalty.penalty_location
			penalty_issuance.penalty_occurence_time = penalty.penalty_occurence_time
			penalty_issuance.shift = penalty.shift
			penalty_issuance.site = penalty.site
			penalty_issuance.project = penalty.project
			penalty_issuance.site_location = penalty.site_location
			penalty_issuance.append("employees", {
				"employee_id": penalty.employee_id,
				"employee_name": penalty.employee_name,
				"designation": penalty.designation,
			})
			penalty_issuance.append("penalty_issuance_details",{
				"penalty_type": penalty.penalty_type,
				"exact_notes": penalty.investigation_results
			})
			penalty_issuance.issuing_employee = self.investigation_lead
			# penalty_issuance.employee_name = self.lead_name
			penalty_issuance.flags.ignore_permissions = True
			penalty_issuance.insert()
			penalty_issuance.submit()
			
@frappe.whitelist()
def filter_employees(doctype, txt, searchfield, start, page_len, filters):
	doctype = filters.get('doctype')
	docname = filters.get('name')
	return frappe.db.sql("""
		SELECT employee_id, employee_name
		FROM `tabLegal Investigation Employees` 
		WHERE parent="{docname}" AND parenttype="{doctype}"
	""".format(doctype=doctype, docname=docname))