# Copyright (c) 2024, one_fm and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


class MedicalAppointment(Document):
	def validate(self):
		if self.workflow_state == "Done" and self.date_and_time_confirmation:
			if get_datetime(self.date_and_time_confirmation) > now_datetime():
				frappe.throw(
					_("You are not allowed to action medical appointment before the appointment date."),
					title=_("Appointment Date is in the future"),
				)
