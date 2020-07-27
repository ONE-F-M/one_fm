# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import get_link_to_form

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



@frappe.whitelist()
def filter_employees(doctype, txt, searchfield, start, page_len, filters):
	doctype = filters.get('doctype')
	docname = filters.get('name')
	return frappe.db.sql("""
		SELECT employee_id, employee_name
		FROM `tabLegal Investigation Employees` 
		WHERE parent="{docname}" AND parenttype="{doctype}"
	""".format(doctype=doctype, docname=docname))