# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TripRequest(Document):
	def validate(self):
		self.validate_passengers()
		self.calculate_total_headcount()

	def validate_passengers(self):
		"""Ensure at least one passenger has been added to the trip request.

		A Trip Request with no passengers has nothing to transport, so we
		block the save with a clear, translatable message.
		"""
		if not self.transport_request_passenger:
			frappe.throw(
				_("Please add at least one employee to the passenger list."),
				title=_("No Passengers Added"),
			)

	def calculate_total_headcount(self):
		"""Populate the read-only Total Headcount from the passenger table."""
		self.total_headcount = len(self.transport_request_passenger)
