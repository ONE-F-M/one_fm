# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002107: what the Preparation Connections section offers."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.preparation.preparation_dashboard import get_data


class TestPreparationDashboard(FrappeTestCase):
	def test_every_sub_document_has_a_badge(self):
		data = get_data()
		linked = [doctype for group in data["transactions"] for doctype in group["items"]]

		for doctype in (
			"Work Permit",
			"Medical Insurance",
			"Residency",
			"PACI",
			"Medical Appointment",
			"PCC Attestation",
		):
			self.assertIn(doctype, linked)

	def test_each_badge_can_filter_on_the_link_the_dashboard_names(self):
		"""A badge on a doctype with no `preparation` field renders but finds nothing."""
		data = get_data()

		for group in data["transactions"]:
			for doctype in group["items"]:
				with self.subTest(doctype=doctype):
					self.assertTrue(
						frappe.get_meta(doctype).get_field(data["fieldname"]),
						f"{doctype} has no {data['fieldname']} field to filter on",
					)
