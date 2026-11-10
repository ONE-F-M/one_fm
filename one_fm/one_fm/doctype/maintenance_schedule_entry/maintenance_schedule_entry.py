# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""A planned maintenance slot of an Object.

The Maintenance Schedule Entry Lifecycle map builds the slots and raises their Work Orders
every day, through the Build Maintenance Schedule and Raise Due Work Orders scripts.
"""

from frappe.model.document import Document

from one_fm.one_fm.processa_rules import run_rule


class MaintenanceScheduleEntry(Document):
	def validate(self):
		# The category, location chain and planned execution datetime, by the same rule the map builds slots with.
		run_rule("Build Maintenance Schedule", "prepare_entry", self)
