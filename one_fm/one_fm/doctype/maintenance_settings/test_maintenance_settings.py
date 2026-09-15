# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.maintenance_settings.maintenance_settings import (
	get_maintenance_settings,
)


class TestMaintenanceSettings(FrappeTestCase):
	def test_is_single_doctype(self):
		"""Maintenance Settings must be a Single doctype."""
		self.assertTrue(frappe.get_meta("Maintenance Settings").issingle)

	def test_get_maintenance_settings_returns_single_doc(self):
		"""The helper returns the single settings document with the expected fields."""
		settings = get_maintenance_settings()
		self.assertEqual(settings.doctype, "Maintenance Settings")
		self.assertTrue(hasattr(settings, "schedule_generation_months"))
		self.assertTrue(hasattr(settings, "work_order_generation_lead_time_days"))
