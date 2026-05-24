# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import ValidationError
from frappe.tests.utils import FrappeTestCase


class TestMaintenanceServiceLevelAgreement(FrappeTestCase):
	def make_sla(self, **overrides):
		doc = frappe.get_doc(
			{
				"doctype": "Maintenance Service Level Agreement",
				"start_date": "2026-01-01",
				"end_date": "2026-12-31",
				"priorities": [
					{
						"priority": "Low",
						"default_priority": 1,
					}
				],
			}
		)

		for key, value in overrides.items():
			doc.set(key, value)

		return doc

	def test_validate_rejects_end_date_before_start_date(self):
		doc = self.make_sla(start_date="2026-12-31", end_date="2026-01-01")

		with self.assertRaises(ValidationError):
			doc.validate()

	def test_validate_rejects_multiple_default_priorities(self):
		doc = self.make_sla(
			priorities=[
				{
					"priority": "Low",
					"default_priority": 1,
				},
				{
					"priority": "High",
					"default_priority": 1,
				},
			]
		)

		with self.assertRaises(ValidationError):
			doc.validate()
