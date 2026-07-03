# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe import ValidationError
from frappe.tests.utils import FrappeTestCase


class TestMaintenanceKPIMaster(FrappeTestCase):
	def make_master(self, **overrides):
		"""Build an in-memory Maintenance KPI Master for unit-testing logic.

		Client/Project are set directly (instead of fetched from a Contract) so
		the tests stay focused on the business rules without heavy fixtures.
		"""
		doc = frappe.get_doc(
			{
				"doctype": "Maintenance KPI Master",
				"client": "_Test Client",
				"project": "_Test Project",
				"effective_from": "2026-01-01",
				"effective_to": "2026-12-31",
				"kpi_information": [],
				"penalty_information": [],
			}
		)

		for key, value in overrides.items():
			doc.set(key, value)

		return doc

	# --- Date range -----------------------------------------------------------

	def test_rejects_effective_to_before_effective_from(self):
		doc = self.make_master(effective_from="2026-12-31", effective_to="2026-01-01")

		with self.assertRaises(ValidationError):
			doc.validate_date_range()

	# --- KPI condition validation (AC1 / Example 1) ---------------------------

	def test_valid_kpi_condition_passes(self):
		doc = self.make_master(
			kpi_information=[
				{"kpi_name": "Response Time", "conditions": "actual_response_minutes <= 45"},
			]
		)

		# Should not raise.
		doc.validate_kpi_conditions()

	def test_plain_text_condition_blocked(self):
		doc = self.make_master(
			kpi_information=[
				{"kpi_name": "Bad Rule", "conditions": "respond fast please"},
			]
		)

		with self.assertRaises(Exception):
			doc.validate_kpi_conditions()

	def test_unapproved_variable_condition_blocked(self):
		doc = self.make_master(
			kpi_information=[
				{"kpi_name": "Unknown Var", "conditions": "made_up_variable <= 10"},
			]
		)

		with self.assertRaises(Exception):
			doc.validate_kpi_conditions()

	def test_non_comparison_condition_blocked(self):
		# A bare value is valid syntax but is not a true/false rule.
		doc = self.make_master(
			kpi_information=[
				{"kpi_name": "Bare Value", "conditions": "45"},
			]
		)

		with self.assertRaises(Exception):
			doc.validate_kpi_conditions()

	# --- Penalty tier auto-sort (Example 4, Case A) ---------------------------

	def test_penalty_tiers_sorted_highest_to_lowest(self):
		doc = self.make_master(
			penalty_information=[
				{"score_floor_threshold": 85, "deduction_percentage": 5},
				{"score_floor_threshold": 95, "deduction_percentage": 0},
				{"score_floor_threshold": 90, "deduction_percentage": 2},
			]
		)

		doc.sort_penalty_tiers()

		floors = [row.score_floor_threshold for row in doc.penalty_information]
		self.assertEqual(floors, [95, 90, 85])
		# idx must be re-sequenced so the reordering persists.
		self.assertEqual([row.idx for row in doc.penalty_information], [1, 2, 3])

	# --- Penalty tier logic (Example 4, Case B) -------------------------------

	def test_valid_descending_penalty_tiers_pass(self):
		doc = self.make_master(
			penalty_information=[
				{"score_floor_threshold": 95, "deduction_percentage": 0},
				{"score_floor_threshold": 90, "deduction_percentage": 2},
				{"score_floor_threshold": 85, "deduction_percentage": 5},
			]
		)

		# Should not raise.
		doc.validate_penalty_tiers()

	def test_duplicate_score_floor_blocked(self):
		doc = self.make_master(
			penalty_information=[
				{"score_floor_threshold": 90, "deduction_percentage": 2},
				{"score_floor_threshold": 90, "deduction_percentage": 5},
			]
		)

		with self.assertRaises(ValidationError):
			doc.validate_penalty_tiers()

	def test_cheaper_penalty_for_lower_score_blocked(self):
		# Sorted descending: 90 -> 2%, then 80 -> 1% (penalty got cheaper).
		doc = self.make_master(
			penalty_information=[
				{"score_floor_threshold": 90, "deduction_percentage": 2},
				{"score_floor_threshold": 80, "deduction_percentage": 1},
			]
		)
		doc.sort_penalty_tiers()

		with self.assertRaises(ValidationError):
			doc.validate_penalty_tiers()

	# --- KPI Code Key auto-generation (Example 2) -----------------------------

	def test_kpi_code_keys_generated_for_empty_rows(self):
		doc = self.make_master(
			kpi_information=[
				{"kpi_name": "Monthly AC Filter Punctuality", "conditions": "Actual Response Minutes <= 30"},
				{"kpi_name": "Response Time", "conditions": "Actual Response Minutes <= 45"},
			]
		)

		with patch("frappe.get_all", return_value=[]):
			doc.set_kpi_code_keys()

		keys = [row.kpi_code_key for row in doc.kpi_information]
		self.assertTrue(all(key.startswith("KPI-REQ-") for key in keys))
		# Keys must be unique across the rows.
		self.assertEqual(len(set(keys)), len(keys))

	def test_existing_kpi_code_key_preserved(self):
		doc = self.make_master(
			kpi_information=[
				{"kpi_name": "Locked Rule", "kpi_code_key": "KPI-REQ-0042"},
				{"kpi_name": "New Rule"},
			]
		)

		with patch("frappe.get_all", return_value=["KPI-REQ-0042"]):
			doc.set_kpi_code_keys()

		self.assertEqual(doc.kpi_information[0].kpi_code_key, "KPI-REQ-0042")
		# The new row must not collide with the existing key.
		self.assertNotEqual(doc.kpi_information[1].kpi_code_key, "KPI-REQ-0042")
		self.assertTrue(doc.kpi_information[1].kpi_code_key.startswith("KPI-REQ-"))

	# --- Double-booking protection (Example 3) --------------------------------

	def test_overlapping_active_master_blocked(self):
		doc = self.make_master()

		with patch("frappe.get_all", return_value=[{"name": "KPI-EXISTING-0001"}]):
			with self.assertRaises(ValidationError) as cm:
				doc.validate_no_overlapping_master()

		self.assertIn(
			"Configuration Error: A Maintenance KPI Master is already active "
			"for this Client and Project during this date range.",
			str(cm.exception),
		)

	def test_no_conflict_when_no_overlap(self):
		doc = self.make_master()

		with patch("frappe.get_all", return_value=[]):
			# Should not raise.
			doc.validate_no_overlapping_master()
