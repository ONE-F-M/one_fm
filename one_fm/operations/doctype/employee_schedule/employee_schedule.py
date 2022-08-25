# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr
class EmployeeSchedule(Document):
	def before_insert(self):
		if frappe.db.exists("Employee Schedule", {"employee": self.employee, "date": self.date, "roster_type" : self.roster_type}):
			frappe.throw(_("Employee Schedule already scheduled for {employee} on {date}.".format(employee=self.employee_name, date=cstr(self.date))))

		# validate employee is active
		if not frappe.db.exists("Employee", {'status':'Active', 'name':self.employee}):
			frappe.throw(f"{self.employee} - {self.employee_name} is not active and cannot be scheduled.")

@frappe.whitelist()
def get_operations_roles(doctype, txt, searchfield, start, page_len, filters):
	shift = filters.get('shift')
	operations_roles = frappe.db.sql("""
		SELECT DISTINCT post_template
		FROM `tabOperations Post`
		WHERE site_shift="{shift}"
	""".format(shift=shift))
	print(operations_roles)
	return operations_roles
