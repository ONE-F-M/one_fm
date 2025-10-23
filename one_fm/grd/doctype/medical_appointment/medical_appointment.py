# Copyright (c) 2024, one_fm and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class MedicalAppointment(Document):
	def validate(self):
		if self.workflow_state == "Pending Confirmation" and self.date_and_time_confirmation:
			if self.date_and_time_confirmation > today():
				frappe.throw(
					_("You are not allowed to action medical appointment before the appointment date."),
					title=_("Appointment Date is in the future"),
				)
