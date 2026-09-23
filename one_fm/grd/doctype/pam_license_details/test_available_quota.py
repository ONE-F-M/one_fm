# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002770: what is left of a quota once everything claimed against it is taken off."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.pam_license_details.pam_license_details import (
	QUOTA_DEDUCTIONS,
	available_quota,
)

SOURCE = frappe.get_app_path(
	"one_fm", "grd", "doctype", "pam_license_details", "pam_license_details.py"
)


def _row(allocated="", registered="", issued="", transfers=""):
	return {
		"allocated_quota": allocated,
		"registered_numbers_of_employees": registered,
		"number_of_visas_issued": issued,
		"number_of_transfer_requests": transfers,
	}


class TestTheSubtraction(FrappeTestCase):
	def test_it_takes_all_three_claims_off_the_allocation(self):
		self.assertEqual(
			available_quota(_row(allocated="100", registered="40", issued="10", transfers="5")),
			"45",
		)

	def test_the_three_deductions_are_the_ones_the_story_lists(self):
		self.assertEqual(
			QUOTA_DEDUCTIONS,
			(
				"registered_numbers_of_employees",
				"number_of_visas_issued",
				"number_of_transfer_requests",
			),
		)

	def test_an_untouched_allocation_is_wholly_available(self):
		self.assertEqual(available_quota(_row(allocated="30")), "30")

	def test_a_blank_counts_as_zero(self):
		"""These are Data fields, so an unfilled one is "" rather than 0 - and arithmetic
		on it would raise rather than read as nothing claimed."""
		self.assertEqual(available_quota(_row(allocated="30", registered="")), "30")
		self.assertEqual(available_quota(_row()), "0")
		self.assertEqual(
			available_quota(
				{
					"allocated_quota": None,
					"registered_numbers_of_employees": None,
					"number_of_visas_issued": None,
					"number_of_transfer_requests": None,
				}
			),
			"0",
		)

	def test_a_missing_key_counts_as_zero_too(self):
		self.assertEqual(available_quota({"allocated_quota": "12"}), "12")

	def test_an_over_allocated_quota_reads_as_none_left(self):
		"""A licence CAN be over its quota - that is what an over-allocation is - but
		"available" is how many are left to use, and a negative number of visas is not a
		number anybody can act on. The overage is still visible in the four figures beside
		it, which are not clamped."""
		self.assertEqual(
			available_quota(_row(allocated="10", registered="12", issued="3")), "0"
		)

	def test_it_returns_a_whole_number_as_text(self):
		"""The field is Data, and every figure on this row is a count of people."""
		result = available_quota(_row(allocated="10", registered="2"))
		self.assertIsInstance(result, str)
		self.assertEqual(result, "8")
		self.assertNotIn(".", result)


class TestWhenItIsDerived(FrappeTestCase):
	def setUp(self):
		self.source = frappe.read_file(SOURCE)

	def test_it_is_derived_after_the_figures_it_subtracts(self):
		"""Deriving it first would leave it one save behind its own inputs."""
		validate = self.source.split("def validate(self):", 1)[1].split("\n\n", 1)[0]
		self.assertLess(
			validate.index("set_quota_registrations"), validate.index("set_available_quota")
		)
		self.assertLess(
			validate.index("set_quota_visas_issued"), validate.index("set_available_quota")
		)

	def test_the_recount_writes_it_beside_its_inputs(self):
		"""db_set bypasses the controller that derives it, so a row would otherwise carry
		yesterday's remainder beside today's headcount."""
		block = self.source.split("def recount_quota_rows", 1)[1]
		self.assertIn('figures["available_quota"] = available_quota({**row, **figures})', block)

	def test_the_recount_reads_the_two_figures_it_does_not_write(self):
		"""The remainder is a subtraction over all four, and two of them are typed."""
		block = self.source.split("def recount_quota_rows", 1)[1]
		self.assertIn('"allocated_quota"', block)
		self.assertIn('"number_of_transfer_requests"', block)


class TestWhichFiguresArePeoplesToType(FrappeTestCase):
	def setUp(self):
		self.fields = {
			f["fieldname"]: f
			for f in json.loads(
				frappe.read_file(
					frappe.get_app_path(
						"one_fm",
						"grd",
						"doctype",
						"quota_classification",
						"quota_classification.json",
					)
				)
			)["fields"]
		}

	def test_the_remainder_is_derived(self):
		self.assertEqual(self.fields["available_quota"]["read_only"], 1)

	def test_the_two_figures_no_story_derives_are_still_typed(self):
		"""Allocated Quota is what PAM granted; Number of Transfer Requests has no source
		on this site yet. Locking either would leave a figure nobody can set."""
		self.assertNotEqual(self.fields["allocated_quota"].get("read_only"), 1)
		self.assertNotEqual(self.fields["number_of_transfer_requests"].get("read_only"), 1)

	def test_the_two_counted_figures_are_derived(self):
		self.assertEqual(self.fields["registered_numbers_of_employees"]["read_only"], 1)
		self.assertEqual(self.fields["number_of_visas_issued"]["read_only"], 1)
