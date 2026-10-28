# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Nationality Percentage by PAM."""

import json
from unittest import mock

import frappe
from frappe import _
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.report.nationality_percentage_by_pam import nationality_percentage_by_pam as module
from one_fm.grd.report.nationality_percentage_by_pam.nationality_percentage_by_pam import (
	build_rows,
	execute,
	get_chart,
)


def _group(pam_file, nationality, count):
	return {"pam_file": pam_file, "one_fm_nationality": nationality, "employee_count": count}


TWO_PAMS = [
	_group("ONE FM Private", "Indian", 152),
	_group("T4", "Nepali", 294),
	_group("ONE FM Private", "Nepali", 419),
	_group("T4", "Indian", 100),
	_group("ONE FM Private", "Kenyan", 176),
]


class TestBuildRows(FrappeTestCase):
	def test_each_pam_adds_up_to_one_hundred_on_its_own_total(self):
		rows = build_rows(TWO_PAMS)
		for pam_file, total in (("ONE FM Private", 747), ("T4", 394)):
			own = [row for row in rows if row["pam_file"] == pam_file]
			self.assertAlmostEqual(sum(row["percentage"] for row in own), 100, delta=0.01)
			self.assertEqual(sum(row["employee_count"] for row in own), total)
			for row in own:
				self.assertEqual(row["percentage"], round(row["employee_count"] * 100 / total, 2))

	def test_sorted_by_pam_then_count_descending(self):
		rows = build_rows(TWO_PAMS)
		self.assertEqual(
			[(row["pam_file"], row["nationality"]) for row in rows],
			[
				("ONE FM Private", "Nepali"),
				("ONE FM Private", "Kenyan"),
				("ONE FM Private", "Indian"),
				("T4", "Nepali"),
				("T4", "Indian"),
			],
		)

	def test_an_empty_nationality_is_labelled_not_set(self):
		rows = build_rows([_group("T4", None, 1), _group("T4", "Indian", 3)])
		self.assertIn(_("Not Set"), [row["nationality"] for row in rows])
		self.assertEqual(next(r for r in rows if r["nationality"] == _("Not Set"))["percentage"], 25)

	def test_a_pam_with_no_employees_does_not_appear(self):
		rows = build_rows([_group("T4", "Indian", 2), _group("Opera File", "Indian", 0)])
		self.assertEqual({row["pam_file"] for row in rows}, {"T4"})
		self.assertEqual(build_rows([]), [])


class TestGetChart(FrappeTestCase):
	def test_one_pam_is_a_pie_of_counts(self):
		chart = get_chart(build_rows([_group("T4", "Nepali", 294), _group("T4", "Indian", 100)]))
		self.assertEqual(chart["type"], "pie")
		self.assertEqual(chart["data"]["labels"], ["Nepali", "Indian"])
		self.assertEqual(chart["data"]["datasets"][0]["values"], [294, 100])

	def test_two_pams_are_a_bar_chart_with_a_dataset_each(self):
		rows = build_rows(TWO_PAMS + [_group("ONE FM Private", "Sri Lankan", 5)])
		chart = get_chart(rows)
		self.assertEqual(chart["type"], "bar")
		self.assertEqual(len(chart["data"]["datasets"]), 2)
		labels = chart["data"]["labels"]
		self.assertEqual(labels[0], "Nepali")
		datasets = {d["name"]: d["values"] for d in chart["data"]["datasets"]}
		# T4 has no Sri Lankan employees: 0, not a gap.
		self.assertEqual(datasets["T4"][labels.index("Sri Lankan")], 0)
		self.assertEqual(datasets["T4"][labels.index("Indian")], round(100 * 100 / 394, 2))

	def test_no_rows_no_chart(self):
		self.assertIsNone(get_chart([]))


class TestExecute(FrappeTestCase):
	def _run(self, filters):
		with mock.patch.object(module.frappe, "get_list", return_value=TWO_PAMS) as get_list:
			result = execute(filters)
		return result, get_list

	def test_it_returns_columns_data_chart_and_summary(self):
		(columns, data, message, chart, summary), _get_list = self._run(None)
		self.assertEqual(
			[c["fieldname"] for c in columns],
			["pam_file", "nationality", "employee_count", "percentage"],
		)
		self.assertEqual(len(data), 5)
		self.assertIsNone(message)
		self.assertEqual(chart["type"], "bar")
		self.assertEqual(
			{card["label"]: card["value"] for card in summary}, {"ONE FM Private": 747, "T4": 394}
		)

	def test_only_employees_under_company_residency_on_the_pam_file_link(self):
		_result, get_list = self._run({})
		kwargs = get_list.call_args.kwargs
		self.assertEqual(get_list.call_args.args[0], "Employee")
		self.assertEqual(kwargs["filters"]["under_company_residency"], 1)
		self.assertIn("pam_file", kwargs["filters"])
		self.assertNotIn("pam_file_number", kwargs["filters"])
		self.assertEqual(kwargs["filters"]["pam_file"], ["is", "set"])
		self.assertEqual(kwargs["group_by"], "pam_file, one_fm_nationality")
		self.assertNotIn("pam_file_number", " ".join(kwargs["fields"]))

	def test_the_pam_file_filter_passes_through(self):
		_result, get_list = self._run({"pam_file": "T4"})
		self.assertEqual(get_list.call_args.kwargs["filters"]["pam_file"], "T4")


class TestTheReportDefinition(FrappeTestCase):
	def test_it_is_a_standard_live_report_on_employee(self):
		definition = json.loads(
			frappe.read_file(
				frappe.get_app_path(
					"one_fm",
					"grd",
					"report",
					"nationality_percentage_by_pam",
					"nationality_percentage_by_pam.json",
				)
			)
		)
		self.assertEqual(definition["ref_doctype"], "Employee")
		self.assertEqual(definition["report_type"], "Script Report")
		self.assertEqual(definition["is_standard"], "Yes")
		self.assertEqual(definition["module"], "GRD")
		self.assertEqual(definition["prepared_report"], 0)
		self.assertEqual(definition["add_total_row"], 0)
