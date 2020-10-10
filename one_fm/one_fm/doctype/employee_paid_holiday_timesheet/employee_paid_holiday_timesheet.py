# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class EmployeePaidHolidayTimesheet(Document):
	def on_update_after_submit(self):
		if self.status == "Approved":
			self.create_timesheet_for_items()

	def create_timesheet_for_items(self):
		for item in self.items:
			if not item.timesheet:
				ts = frappe.new_doc('Timesheet')
				ts.submit()
