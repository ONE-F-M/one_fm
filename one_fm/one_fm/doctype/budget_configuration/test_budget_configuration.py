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

	def _clear_existing_config(self, effective_from=None):
		"""Remove site Budget Configurations that would collide with this test.

		The controller's unique-effective-from and single-enabled rules only started
		running when custom was set to 0 (WI-001707), at which point rows left in the
		site by earlier runs began failing these tests. Deletions happen inside the
		test transaction, which FrappeTestCase rolls back.
		"""
		filters = {"effective_from": effective_from} if effective_from else {"enabled": 1}
		for name in frappe.get_all("Budget Configuration", filters=filters, pluck="name"):
			frappe.delete_doc("Budget Configuration", name, force=True, ignore_permissions=True)

	def test_only_one_enabled_allowed(self):
		self._clear_existing_config()
		self._clear_existing_config("2026-01-01")
		self._clear_existing_config("2026-02-01")

		self._make("2026-01-01", enabled=1)
		with self.assertRaises(frappe.ValidationError):
			self._make("2026-02-01", enabled=1)

	def test_effective_from_must_be_unique(self):
		self._clear_existing_config("2026-03-01")

		self._make("2026-03-01")
		with self.assertRaises(frappe.ValidationError):
			self._make("2026-03-01")
