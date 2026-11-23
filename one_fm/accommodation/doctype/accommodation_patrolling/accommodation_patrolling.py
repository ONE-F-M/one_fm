# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import getseries
from frappe.utils import cint, getdate, now_datetime


class AccommodationPatrolling(Document):
	def before_insert(self):
		self.set_officer_details()
		self.set_number_of_patrolling()

	def set_officer_details(self):
		"""Stamp the creating user, time and Employee shift. Insert only, so later edits keep them."""
		user = frappe.session.user
		self.patrolling_date_and_time = now_datetime()
		self.name_of_security_officer = user
		self.patrol_shift = frappe.db.get_value("Employee", {"user_id": user}, "shift")
		# Links are validated (and fetch_from filled) before before_insert runs, so fill them here.
		self.email_address = frappe.db.get_value("User", user, "email")
		times = self.patrol_shift and frappe.db.get_value(
			"Operations Shift", self.patrol_shift, ["start_time", "end_time"]
		)
		self.shift_time, self.shift_end_time = times or (None, None)

	def set_number_of_patrolling(self):
		"""Daily sequence from a per-date counter in tabSeries; locked row, rolled back with a failed insert."""
		self.number_of_patrolling = cint(
			getseries(f"ACC-PATROL-{getdate(self.patrolling_date_and_time)}", 1)
		)
