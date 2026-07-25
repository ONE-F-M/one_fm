# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestBudgetConfiguration(FrappeTestCase):
	def _make(self, effective_from, enabled=0):
		return frappe.get_doc(
			{
				"doctype": "Budget Configuration",
				"effective_from": effective_from,
				"enabled": enabled,
				"reliever_factor_percentage": 10,
			}
		).insert(ignore_permissions=True)

	def test_only_one_enabled_allowed(self):
		self._make("2026-01-01", enabled=1)
		with self.assertRaises(frappe.ValidationError):
			self._make("2026-02-01", enabled=1)

	def test_effective_from_must_be_unique(self):
		self._make("2026-03-01")
		with self.assertRaises(frappe.ValidationError):
			self._make("2026-03-01")
