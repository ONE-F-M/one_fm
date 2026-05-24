# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class MaintenanceFrequency(Document):
	def validate(self):
		self.validate_frequency_days()

	def validate_frequency_days(self):
		"""Ensure frequency_days is a positive integer to avoid infinite loops in the scheduler."""
		if cint(self.frequency_days) <= 0:
			frappe.throw(
				_("Frequency (Days) must be a positive integer. Got: {0}").format(self.frequency_days)
			)
