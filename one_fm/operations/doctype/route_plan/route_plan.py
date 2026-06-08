# Copyright (c) 2026, oneaborance and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document


class RoutePlan(Document):
	def validate(self):
		self._validate_dates()
		self._validate_single_active()
		self._validate_single_default()

	def _validate_dates(self):
		"""Ensure effective_until >= effective_from when set."""
		if self.effective_until and self.effective_from:
			if self.effective_until < self.effective_from:
				frappe.throw(_("Effective Until must be on or after Effective From"))

	def _validate_single_active(self):
		"""Only one Route Plan can be Active at a time."""
		if self.status == "Active":
			existing = frappe.db.get_value(
				"Route Plan",
				{"status": "Active", "name": ["!=", self.name]},
				"name"
			)
			if existing:
				frappe.throw(
					_("Route Plan {0} is already Active. Deactivate it first or set it to Expired.").format(existing)
				)

	def _validate_single_default(self):
		"""Only one Route Plan can be marked as Default."""
		if cint(self.is_default):
			existing = frappe.db.get_value(
				"Route Plan",
				{"is_default": 1, "name": ["!=", self.name]},
				"name"
			)
			if existing:
				frappe.throw(
					_("A default Route Plan already exists ({0}). Only one plan can be set as default at a time.").format(existing)
				)

	def before_save(self):
		self.last_modified_by_user = frappe.session.user
		self.last_modified_at = frappe.utils.now()
