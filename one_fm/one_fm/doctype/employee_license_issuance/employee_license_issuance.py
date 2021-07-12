# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document

class EmployeeLicenseIssuance(Document):
	def validate(self):
		if self.issue_date and self.expiry_date:
			if getdate(self.issue_date) >= getdate(self.expiry_date):
				frappe.throw(_("Expiry date cannot be on or before Issue date"))

		elif not self.issue_date and self.expiry_date and getdate(self.expiry_date) <= getdate():
			frappe.throw(_("Expiry date cannot be on or before today"))

	def on_submit(self):
		for employee in self.employees:
			if frappe.db.exists("Employee License", {'license_name': self.license_name, 'employee': employee.employee}):
				doc_el = frappe.get_doc("Employee License", {'license_name': self.license_name, 'employee': employee.employee})
				doc_el.issue_date = self.issue_date
				doc_el.expiry_date = self.expiry_date
				doc_el.save()
			else:
				doc_el = frappe.new_doc("Employee License")
				doc_el.license_name = self.license_name
				doc_el.issuing_authority = frappe.db.get_value("License", {'license_name': self.license_name}, "issuing_authority")
				doc_el.employee = employee.employee
				doc_el.employee_name = get_employee_name(employee.employee)
				doc_el.issue_date = self.issue_date
				doc_el.expiry_date = self.expiry_date
				doc_el.save()

@frappe.whitelist()
def get_employee_name(employee_code):
	return frappe.db.get_value("Employee", employee_code, "employee_name")
