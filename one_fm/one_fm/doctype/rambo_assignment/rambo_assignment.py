# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class RamboAssignment(Document):
	"""Submitting, cancelling and notifying run in the Rambo Assignment Processa maps.

	Only the checks that must refuse the submit or the cancel stay here.
	"""

	def before_submit(self):
		self.validate_schedule_details()

	def before_cancel(self):
		self.validate_not_checked_in()

	def validate_schedule_details(self):
		"""The reliever's Employee Schedule is written from these on submit."""
		if not self.employee:
			frappe.throw(_("Reliever Employee is required to create an Employee Schedule."))
		if not self.date:
			frappe.throw(_("Date is required to create an Employee Schedule."))
		if not self.operations_shift:
			frappe.throw(_("Operations Shift is required to create an Employee Schedule."))
		if not frappe.db.get_value("Operations Shift", self.operations_shift, "shift_type"):
			frappe.throw(_("Shift Type is not configured for Operations Shift {0}.").format(self.operations_shift))

	def validate_not_checked_in(self):
		"""A Rambo shift the reliever has started cannot be taken back."""
		schedule = frappe.db.get_value(
			"Employee Schedule", {"employee": self.employee, "date": self.date, "rambo_assignment": self.name}, "name"
		)
		if not schedule:
			return
		shift_assignment = frappe.db.get_value(
			"Shift Assignment", {"employee_schedule": schedule, "docstatus": 1}, "name"
		)
		if shift_assignment and frappe.db.exists("Employee Checkin", {"shift_assignment": shift_assignment}):
			frappe.throw(
				_("{0} has already checked in on Shift Assignment {1}, so the Rambo Assignment cannot be cancelled.").format(
					self.employee_name or self.employee, shift_assignment
				)
			)
