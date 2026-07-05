# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from one_fm.one_fm.doctype.maintenance_kpi_assessment.maintenance_kpi_assessment import (
	METRIC_CALCULATORS,
	STATUS_COMPLIED,
	STATUS_FAILED,
	_pass_percentage,
	identify_metric,
)


class TestMaintenanceKPIAssessment(FrappeTestCase):
	def test_identify_metric_maps_friendly_labels(self):
		"""A human-friendly rule resolves to the correct engine identifier."""
		self.assertEqual(
			identify_metric("Response Timeframe Percentage >= 98%"),
			"response_timeframe_percentage",
		)
		self.assertEqual(
			identify_metric("Planned Maintenance Percentage = 100%"),
			"planned_maintenance_percentage",
		)
		self.assertEqual(
			identify_metric("Mean Time Between Failures >= 5000"),
			"mean_time_between_failures",
		)

	def test_identify_metric_unknown_returns_none(self):
		self.assertIsNone(identify_metric("Something Unmeasured >= 5"))

	def test_supported_metrics_are_registered(self):
		"""The three data-backed metrics must have calculators; the rest must not."""
		self.assertIn("response_timeframe_percentage", METRIC_CALCULATORS)
		self.assertIn("resolution_timeframe_percentage", METRIC_CALCULATORS)
		self.assertIn("planned_maintenance_percentage", METRIC_CALCULATORS)
		# Metrics without source data yet are intentionally absent.
		self.assertNotIn("mean_time_between_failures", METRIC_CALCULATORS)
		self.assertNotIn("first_time_fix_rate", METRIC_CALCULATORS)

	def test_pass_percentage(self):
		work_orders = [
			{"sla_response_status": "Pass"},
			{"sla_response_status": "Pass"},
			{"sla_response_status": "Fail"},
			{"sla_response_status": "Pre-Start"},  # excluded: not yet final
		]
		# 2 of 3 final rows passed -> 66.67%.
		self.assertAlmostEqual(
			_pass_percentage(work_orders, "sla_response_status"), 66.6667, places=3
		)

	def test_pass_percentage_no_final_work_orders(self):
		self.assertEqual(_pass_percentage([], "sla_response_status"), 0.0)

	def test_get_period_range(self):
		"""Month/Year resolve to an inclusive month with an exclusive upper bound."""
		doc = frappe.new_doc("Maintenance KPI Assessment")
		doc.month = "June"
		doc.year = "2026"
		start, end = doc.get_period_range()
		self.assertEqual(getdate(start), getdate("2026-06-01"))
		self.assertEqual(getdate(end), getdate("2026-07-01"))

	def test_calculate_scores_grades_rows(self):
		"""Actual Value drives Status and Points Achieved via the Master rule.

		Metric calculators are stubbed so the test exercises the grading logic
		(safe_eval + points mapping) without needing the full Work Order graph.
		"""
		doc = frappe.new_doc("Maintenance KPI Assessment")
		doc.month = "June"
		doc.year = "2026"
		doc.project = "__nonexistent_project__"
		doc.maintenance_kpi_master = "__stub_master__"

		doc.append(
			"monthly_kpi_assessment",
			{"kpi_code_key": "KPI-REQ-0001", "points_weight": 25.0},
		)
		doc.append(
			"monthly_kpi_assessment",
			{"kpi_code_key": "KPI-REQ-0002", "points_weight": 20.0},
		)

		conditions = {
			"KPI-REQ-0001": "Response Timeframe Percentage >= 98%",
			"KPI-REQ-0002": "Resolution Timeframe Percentage >= 95%",
		}
		metric_values = {
			"response_timeframe_percentage": 99.0,  # meets >= 98  -> Complied
			"resolution_timeframe_percentage": 90.0,  # fails  >= 95  -> Failed
		}

		original = dict(METRIC_CALCULATORS)
		conditions_getter = frappe.get_all
		try:
			METRIC_CALCULATORS["response_timeframe_percentage"] = (
				lambda project, start, end: metric_values["response_timeframe_percentage"]
			)
			METRIC_CALCULATORS["resolution_timeframe_percentage"] = (
				lambda project, start, end: metric_values["resolution_timeframe_percentage"]
			)

			def fake_get_all(doctype, *args, **kwargs):
				if doctype == "KPI Target Item":
					# Mirror frappe.get_all's _dict return type (attribute access).
					return [
						frappe._dict(kpi_code_key=key, conditions=rule)
						for key, rule in conditions.items()
					]
				return conditions_getter(doctype, *args, **kwargs)

			frappe.get_all = fake_get_all
			doc.calculate_scores()
		finally:
			frappe.get_all = conditions_getter
			METRIC_CALCULATORS.clear()
			METRIC_CALCULATORS.update(original)

		row1, row2 = doc.monthly_kpi_assessment
		self.assertEqual(row1.actual_value, 99.0)
		self.assertEqual(row1.status, STATUS_COMPLIED)
		self.assertEqual(row1.points_achieved, 25.0)

		self.assertEqual(row2.actual_value, 90.0)
		self.assertEqual(row2.status, STATUS_FAILED)
		self.assertEqual(row2.points_achieved, 0.0)

	def _stub_tier_matrix(self, tiers):
		"""Patch frappe.get_all so Penalty Tier Matrix returns the given tiers.

		Returns a callable that restores the original frappe.get_all.
		"""
		original = frappe.get_all

		def fake_get_all(doctype, *args, **kwargs):
			if doctype == "Penalty Tier Matrix":
				return [
					frappe._dict(
						score_floor_threshold=floor, deduction_percentage=deduction
					)
					for floor, deduction in tiers
				]
			return original(doctype, *args, **kwargs)

		frappe.get_all = fake_get_all
		return lambda: setattr(frappe, "get_all", original)

	def test_deduction_lookup_picks_highest_floor_met(self):
		"""88.5 points lands on the highest floor it still meets: 2% (AC1 example)."""
		doc = frappe.new_doc("Maintenance KPI Assessment")
		doc.maintenance_kpi_master = "__stub_master__"
		# Given deliberately out of order to prove the defensive sort.
		restore = self._stub_tier_matrix([(75, 5), (95, 0), (85, 2)])
		try:
			self.assertEqual(doc.get_applicable_deduction(88.5), 2.0)
			self.assertEqual(doc.get_applicable_deduction(95.0), 0.0)
			self.assertEqual(doc.get_applicable_deduction(80.0), 5.0)
		finally:
			restore()

	def test_deduction_below_all_floors_uses_worst_tier(self):
		"""A score under every floor takes the lowest tier's highest deduction."""
		doc = frappe.new_doc("Maintenance KPI Assessment")
		doc.maintenance_kpi_master = "__stub_master__"
		restore = self._stub_tier_matrix([(95, 0), (85, 2), (75, 5)])
		try:
			self.assertEqual(doc.get_applicable_deduction(50.0), 5.0)
		finally:
			restore()

	def test_deduction_empty_matrix_is_zero(self):
		"""No tiers configured -> no penalty."""
		doc = frappe.new_doc("Maintenance KPI Assessment")
		doc.maintenance_kpi_master = "__stub_master__"
		restore = self._stub_tier_matrix([])
		try:
			self.assertEqual(doc.get_applicable_deduction(88.5), 0.0)
		finally:
			restore()

	def test_deduction_without_master_is_zero(self):
		"""No linked Master -> no matrix to consult -> 0%."""
		doc = frappe.new_doc("Maintenance KPI Assessment")
		self.assertEqual(doc.get_applicable_deduction(88.5), 0.0)

	def test_calculate_penalty_creates_single_summary_row(self):
		"""Points Achieved aggregate into exactly one locked penalty row (AC1)."""
		doc = frappe.new_doc("Maintenance KPI Assessment")
		doc.maintenance_kpi_master = "__stub_master__"
		doc.append("monthly_kpi_assessment", {"points_achieved": 25.0})
		doc.append("monthly_kpi_assessment", {"points_achieved": 43.5})
		doc.append("monthly_kpi_assessment", {"points_achieved": 20.0})

		restore = self._stub_tier_matrix([(95, 0), (85, 2), (75, 5)])
		try:
			doc.calculate_penalty()
			# Re-running must not add a second row.
			doc.calculate_penalty()
		finally:
			restore()

		self.assertEqual(len(doc.monthly_penalty_assessment), 1)
		penalty = doc.monthly_penalty_assessment[0]
		self.assertEqual(penalty.total_achieved_points, 88.5)
		self.assertEqual(penalty.applied_penalty_percentage, 2.0)
