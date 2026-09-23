# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002824: the Visa Request field is called Centralized Number now.

A label change and nothing else. The fieldname, the fetch chain and the data are what
every other story on this field depends on, so the rename stops at what the user reads.
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

FIELDNAME = "moi_reference_number"
NEW_LABEL = "Centralized Number"


def _visa_request():
	return json.loads(
		frappe.read_file(
			frappe.get_app_path(
				"one_fm", "visa_management", "doctype", "visa_request", "visa_request.json"
			)
		)
	)


class TestTheLabel(FrappeTestCase):
	def setUp(self):
		self.field = next(
			f for f in _visa_request()["fields"] if f["fieldname"] == FIELDNAME
		)

	def test_it_reads_centralized_number(self):
		self.assertEqual(self.field["label"], NEW_LABEL)

	def test_the_employee_already_calls_it_that(self):
		"""The other half of the story's "Visa Request and Employee": Employee has said
		Centralized Number since the field was created."""
		self.assertEqual(
			frappe.get_meta("Employee").get_field("one_fm_centralized_number").label, NEW_LABEL
		)


class TestNothingElseMoved(FrappeTestCase):
	def setUp(self):
		self.definition = _visa_request()
		self.field = next(
			f for f in self.definition["fields"] if f["fieldname"] == FIELDNAME
		)

	def test_the_fieldname_is_unchanged(self):
		"""Renaming it would break the fetch chain and every stored value with it."""
		self.assertIn(FIELDNAME, self.definition["field_order"])
		self.assertEqual(self.field["fieldtype"], "Data")

	def test_the_read_only_rule_is_untouched(self):
		"""It is what stops an operator editing the number after MOI has issued it."""
		self.assertIn("Pending Visa Issuance", self.field["read_only_depends_on"])
		self.assertIn("Completed", self.field["read_only_depends_on"])

	def test_the_fetch_chain_to_the_employee_still_names_the_field(self):
		"""Visa Request -> Onboard Employee -> Employee. A label change must not disturb
		the mapping the number actually travels along."""
		onboard = json.loads(
			frappe.read_file(
				frappe.get_app_path(
					"one_fm", "hiring", "doctype", "onboard_employee", "onboard_employee.json"
				)
			)
		)
		centralized = next(
			f for f in onboard["fields"] if f["fieldname"] == "visa_centralized_number"
		)
		self.assertEqual(centralized["fetch_from"], f"visa_request.{FIELDNAME}")

		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "hiring", "doctype", "onboard_employee", "onboard_employee.py"
			)
		)
		self.assertIn('"visa_centralized_number": "one_fm_centralized_number"', source)

	def test_the_visibility_patch_still_names_the_field(self):
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "patches", "v15_0", "migrate_visa_request_visibility.py"
			)
		)
		self.assertIn(FIELDNAME, source)
