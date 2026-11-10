# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""A maintained asset.

The Object Lifecycle map submits it, then builds its maintenance schedule and raises the Work
Orders already due, through the Build Maintenance Schedule and Raise Due Work Orders scripts.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

from one_fm.one_fm.processa_rules import run_rule


class Object(Document):
	def validate(self):
		self.validate_commissioning_date()

	def before_save(self):
		# The template parts and the default Last Service Date, by the map's Prepare Object rule.
		run_rule("Prepare Object", "prepare_object", self)

	def validate_commissioning_date(self):
		"""Ensure the commissioning date is not in the future."""
		if self.commissioning_date and getdate(self.commissioning_date) > getdate(today()):
			frappe.throw(
				_("Commissioning Date cannot be in the future. Got: {0}").format(
					frappe.format(self.commissioning_date, {"fieldtype": "Date"})
				)
			)
