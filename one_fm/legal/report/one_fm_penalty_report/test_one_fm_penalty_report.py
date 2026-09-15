# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002015: the One FM Penalty Report's columns, mappings and filters."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.legal.report.one_fm_penalty_report.one_fm_penalty_report import (
	REPORTABLE_STATES,
	execute,
	format_penalty,
	get_columns,
)

# The spreadsheet's columns, in the spreadsheet's order. Asserted as a literal so that
# reordering or renaming one has to be a deliberate edit - the departments read this report
# by its shape.
EXPECTED_COLUMNS = [
	("Sl.No", "sl_no"),
	("Violation Date", "violation_date"),
	("ERP ID", "issuer"),
	("Issued by", "issuer_name"),
	("Receiving Date", "receiving_date"),
	("Serial No.", "penalty_serial_no"),
	("Employee ID (Penalty Receipient)", "employee_id_number"),
	("ERP ID (Penalty Receipient)", "employee"),
	("Employee Name", "employee_name"),
	("Location", "operations_site"),
	("Type of Violation", "applied_penalty_code"),
	("Violation Category", "penalty_name"),
	("Penalty", "penalty"),
	("Status (Employee Response)", "employee_response"),
	("deductions", "deductions"),
]


class TestOneFMPenaltyReport(FrappeTestCase):
	# ------------------------------------------------------------------ columns

	def test_the_columns_match_the_reporter_s_spreadsheet(self):
		columns = [(c["label"], c["fieldname"]) for c in get_columns()]

		self.assertEqual(columns, EXPECTED_COLUMNS)

	def test_the_two_employee_columns_link_to_employee(self):
		by_name = {c["fieldname"]: c for c in get_columns()}

		for fieldname in ("issuer", "employee"):
			with self.subTest(fieldname=fieldname):
				self.assertEqual(by_name[fieldname]["fieldtype"], "Link")
				self.assertEqual(by_name[fieldname]["options"], "Employee")

	def test_the_deduction_column_is_currency(self):
		by_name = {c["fieldname"]: c for c in get_columns()}

		self.assertEqual(by_name["deductions"]["fieldtype"], "Currency")

	def test_the_serial_no_column_reads_the_penalty_s_own_serial(self):
		# WI-002032's field. The spreadsheet's Serial No. holds hand-assigned numbers
		# (1890, 513, ...), not the record's PEN-MM-YYYY-#### name.
		self.assertTrue(
			frappe.get_meta("Penalty And Investigation").get_field("penalty_serial_no")
		)

	# ------------------------------------------------------- the Penalty column

	def test_a_deduction_reads_as_the_spreadsheet_writes_it(self):
		self.assertEqual(format_penalty("Salary Deduction", 1), "Deduct 1 day")

	def test_several_days_are_pluralised(self):
		self.assertEqual(format_penalty("Salary Deduction", 4), "Deduct 4 days")

	def test_a_whole_day_does_not_read_as_a_decimal(self):
		self.assertEqual(format_penalty("Salary Deduction", 1.0), "Deduct 1 day")

	def test_a_half_day_keeps_its_half(self):
		# "Deduct 0.5 day" appears 240 times in the spreadsheet; it is a real half day.
		self.assertEqual(format_penalty("Salary Deduction", 0.5), "Deduct 0.5 day")

	def test_a_fractional_deduction_over_a_day_is_pluralised(self):
		self.assertEqual(format_penalty("Salary Deduction", 2.5), "Deduct 2.5 days")

	def test_every_other_action_reads_as_itself(self):
		for action in ("Warning", "Suspension", "Termination"):
			with self.subTest(action=action):
				self.assertEqual(format_penalty(action, 0), action)

	def test_a_deduction_with_no_days_does_not_claim_to_deduct_none(self):
		self.assertEqual(format_penalty("Salary Deduction", 0), "Salary Deduction")

	def test_no_action_type_reads_as_nothing(self):
		self.assertEqual(format_penalty(None, 0), "")

	# ------------------------------------------------------------------- rows

	def test_the_report_runs_and_numbers_its_rows(self):
		columns, rows = execute({})

		self.assertEqual(len(columns), len(EXPECTED_COLUMNS))
		self.assertEqual([row.sl_no for row in rows], list(range(1, len(rows) + 1)))

	def test_only_reportable_states_are_included(self):
		# AC 1: a penalty is reportable once it has reached payroll, not before.
		_columns, rows = execute({})

		for row in rows:
			state = frappe.db.get_value("Penalty And Investigation", row.name, "workflow_state")
			self.assertIn(state, REPORTABLE_STATES)

	def test_every_row_carries_a_rendered_penalty_column(self):
		_columns, rows = execute({})

		for row in rows:
			self.assertEqual(row.penalty, format_penalty(row.action_type, row.salary_deduction_days))

	def test_the_date_filters_narrow_the_range(self):
		_columns, all_rows = execute({})
		if not all_rows:
			self.skipTest("No reportable penalties on this site")

		dates = sorted(row.violation_date for row in all_rows if row.violation_date)
		if not dates:
			self.skipTest("No reportable penalty carries a violation date")

		_columns, narrowed = execute({"from_date": dates[-1], "to_date": dates[-1]})

		self.assertTrue(all(row.violation_date == dates[-1] for row in narrowed))
		self.assertLessEqual(len(narrowed), len(all_rows))

	def test_an_employee_filter_returns_only_that_employee(self):
		_columns, all_rows = execute({})
		employees = [row.employee for row in all_rows if row.employee]
		if not employees:
			self.skipTest("No reportable penalty carries an employee")

		_columns, rows = execute({"employee": employees[0]})

		self.assertTrue(rows)
		self.assertTrue(all(row.employee == employees[0] for row in rows))

	def test_a_response_filter_returns_only_that_response(self):
		_columns, all_rows = execute({})
		responses = [row.employee_response for row in all_rows if row.employee_response]
		if not responses:
			self.skipTest("No reportable penalty carries an employee response")

		_columns, rows = execute({"employee_response": responses[0]})

		self.assertTrue(all(row.employee_response == responses[0] for row in rows))

	def test_an_unmatched_filter_returns_nothing_rather_than_everything(self):
		_columns, rows = execute({"employee": "HR-EMP-does-not-exist"})

		self.assertEqual(rows, [])
