# Copyright (c) 2026, ONEFM and contributors
# See license.txt

import re

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_first_day, get_last_day, getdate

from one_fm.one_fm.doctype.proof_of_work.proof_of_work import (
	WORKED_ABBRS,
	_hour_cells,
	ATTENDANCE_ABBR,
	DAY_OFF_ABBRS,
	DEFAULT_GENERATION_BASIS,
	_actual_hours,
	_attendance_abbr,
	_basis_for_rate_type,
	_non_manpower_amount_by_category,
	_populate_pow_items,
	_safe_filename,
	_uses_nominal_shift_hours,
	_fmt_actual,
	_fmt_contractual,
	_fmt_staff_breakdown,
	_shift_hours_from_item,
	generate_proof_of_work,
	get_eligible_contracts,
	get_pow_attendance_report,
	pdf_file_name,
	resolve_attendance_source,
)

TEST_YEAR = 2025
TEST_MONTH = 6


def _get_company():
	return frappe.db.get_value("Company", {}, "name")


def _get_or_create_customer():
	name = frappe.db.get_value("Customer", {}, "name")
	if name:
		return name
	customer = frappe.get_doc(
		{"doctype": "Customer", "customer_name": "_Test POW Customer"}
	).insert(ignore_permissions=True)
	return customer.name


def _get_or_create_project(company):
	# Reused as a stable fixture: Project is named after project_name, so a
	# committed leftover from an earlier run would otherwise clash on insert.
	name = "_Test POW Project"
	if frappe.db.exists("Project", name):
		return frappe.get_doc("Project", name)
	return frappe.get_doc(
		{"doctype": "Project", "project_name": name, "company": company}
	).insert(ignore_permissions=True)


class TestProofofWork(FrappeTestCase):
	def setUp(self):
		self.company = _get_company()
		self.customer = _get_or_create_customer()

		# Project the contract and attendance both point to.
		self.project = _get_or_create_project(self.company)

		# The Contracts controller commits internally (breaking test rollback),
		# so build the fixture with a raw db_insert to keep the test isolated.
		self.contract = self._make_contract("_TEST-POW-CONTRACT-A")

		self.first_day = get_first_day(getdate(f"{TEST_YEAR}-{TEST_MONTH:02d}-01"))
		self.last_day = get_last_day(self.first_day)

		self._make_attendance()

	def _make_contract(self, name):
		"""Create an Active Contracts row via a raw insert.

		Bypasses the Contracts controller on purpose: it calls frappe.db.commit()
		in many code paths, which would commit test data and defeat the
		auto-rollback that keeps tests isolated.
		"""
		# Clear any leftover POWs for this contract so generation is not skipped.
		for pow_name in frappe.get_all(
			"Proof of Work", filters={"contract": name}, pluck="name"
		):
			frappe.db.delete("Proof of Work Item", {"parent": pow_name})
			frappe.db.delete("Proof of Work Items Non-Manpower", {"parent": pow_name})
			frappe.db.delete("Proof of Work", {"name": pow_name})

		# Child rows outlive the parent delete, and a stale line item would feed the
		# contracted counts and the non-manpower rollup of every later test.
		frappe.db.delete("Contract Item", {"parent": name})
		frappe.db.delete("Contracts", {"name": name})

		contract = frappe.new_doc("Contracts")
		contract.name = name
		contract.client = self.customer
		contract.project = self.project.name
		contract.price_list = frappe.db.get_value("Price List", {}, "name")
		contract.start_date = getdate(f"{TEST_YEAR}-01-01")
		contract.end_date = getdate(f"{TEST_YEAR}-12-31")
		contract.workflow_state = "Active"
		contract.db_insert()
		return contract

	def _make_attendance(self):
		"""Insert a bare attendance row (bypassing the heavy controller) for the project."""
		att_name = f"POW-TEST-ATT-{self.project.name}"
		# Idempotent: the Project fixture is persistent, so clear any leftover row
		# with this deterministic name before re-inserting.
		frappe.db.delete("Attendance", {"name": att_name})

		att = frappe.new_doc("Attendance")
		att.naming_series = "HR-ATT-.YYYY.-"
		att.employee = "_TEST-POW-EMP"
		att.status = "Present"
		att.working_hours = 8
		att.attendance_date = self.first_day
		att.company = self.company
		att.project = self.project.name
		att.docstatus = 1
		att.name = att_name
		att.db_insert()

	# --- get_eligible_contracts -------------------------------------------------

	def test_eligible_contract_listed_and_not_ticked_when_pow_exists(self):
		rows = get_eligible_contracts(TEST_MONTH, TEST_YEAR)
		names = {r["name"]: r for r in rows}
		self.assertIn(self.contract.name, names)
		# No POW yet -> should be pre-ticked (has_pow == 0)
		self.assertEqual(names[self.contract.name]["has_pow"], 0)

		# After generating, the same contract should report has_pow == 1
		generate_proof_of_work(TEST_MONTH, TEST_YEAR, [self.contract.name], "Shift Hours")
		rows = get_eligible_contracts(TEST_MONTH, TEST_YEAR)
		names = {r["name"]: r for r in rows}
		self.assertEqual(names[self.contract.name]["has_pow"], 1)

	def test_contract_without_attendance_not_listed(self):
		# A month with no attendance should not surface the contract.
		rows = get_eligible_contracts(TEST_MONTH + 1, TEST_YEAR)
		self.assertNotIn(self.contract.name, {r["name"] for r in rows})

	# --- generate_proof_of_work -------------------------------------------------

	def test_generate_creates_header_record(self):
		res = generate_proof_of_work(
			TEST_MONTH, TEST_YEAR, [self.contract.name], "Both"
		)
		self.assertEqual(len(res["created"]), 1)

		pow_doc = frappe.get_doc("Proof of Work", res["created"][0])
		self.assertEqual(pow_doc.contract, self.contract.name)
		self.assertEqual(pow_doc.project, self.project.name)
		self.assertEqual(pow_doc.customer, self.customer)
		self.assertEqual(pow_doc.generation_basis, "Both")
		self.assertEqual(getdate(pow_doc.start_date), self.first_day)
		self.assertEqual(getdate(pow_doc.end_date), self.last_day)
		# The base fixture has no contract line items and the attendance row has
		# no Sale Item (no Operations Role), so the summary table is empty:
		# a Proof of Work Item row is only created per resolvable Sale Item.
		self.assertEqual(len(pow_doc.proof_of_work_item), 0)

	# --- source hierarchy (AC1) -------------------------------------------------

	def _make_approved_amendment(self, workflow_state="Approved"):
		amendment = frappe.get_doc(
			{
				"doctype": "Attendance Amendment",
				"project": self.project.name,
				"year": str(TEST_YEAR),
				"month": "June",
				"attendance_based_on": "Attendance Status",
			}
		).insert(ignore_permissions=True)
		amendment.db_set("workflow_state", workflow_state)
		return amendment

	def test_source_falls_back_to_attendance_when_no_amendment(self):
		source_type, reference = resolve_attendance_source(
			self.contract.name, self.project.name, TEST_MONTH, TEST_YEAR
		)
		self.assertEqual(source_type, "attendance")
		self.assertIsNone(reference)

	def test_source_prefers_approved_amendment(self):
		amendment = self._make_approved_amendment()
		source_type, reference = resolve_attendance_source(
			self.contract.name, self.project.name, TEST_MONTH, TEST_YEAR
		)
		self.assertEqual(source_type, "amendment")
		self.assertEqual(reference, amendment.name)

	def test_source_ignores_unapproved_amendment(self):
		# A Pending Approval amendment must not be used as the source.
		self._make_approved_amendment(workflow_state="Pending Approval")
		source_type, reference = resolve_attendance_source(
			self.contract.name, self.project.name, TEST_MONTH, TEST_YEAR
		)
		self.assertEqual(source_type, "attendance")
		self.assertIsNone(reference)

	# --- contractual hours (shift hours from item code) ------------------------

	def test_shift_hours_parsed_from_item_code(self):
		# actual_hours falls back to present-days x these hours-per-shift.
		self.assertEqual(_shift_hours_from_item("SER-SEC-000136-NKW-M-30DY-12HR"), 12)
		self.assertEqual(_shift_hours_from_item("SER-SEC-000200-8HR"), 8)
		# Service items with no encoded hours -> 0 (contractual falls back to 0).
		self.assertEqual(_shift_hours_from_item("SER-FMG-001706"), 0)
		self.assertEqual(_shift_hours_from_item(""), 0)

	# --- summary calculations & grouping (this story) --------------------------

	@staticmethod
	def _staff_source():
		# 3 relievers/staff worked 15 days / 200 hrs, 2 worked 10 days / 100 hrs.
		# Distinct head-count (5) is intentionally decoupled from any contracted
		# count so grouping is exercised regardless of the contracted total.
		staff = {}
		for i in range(3):
			staff[f"A{i}"] = {"name": f"A{i}", "id": f"A{i}", "days": 15, "hours": 200}
		for i in range(2):
			staff[f"B{i}"] = {"name": f"B{i}", "id": f"B{i}", "days": 10, "hours": 100}
		return {"staff": staff}

	def test_breakdown_grouped_by_days(self):
		out = _fmt_staff_breakdown(self._staff_source(), shift_hours=0, basis="Attendance Day")
		self.assertEqual(
			out,
			"- 3 Staff worked 15 days: 45 Days\n- 2 Staff worked 10 days: 20 Days",
		)

	def test_breakdown_grouped_by_hours(self):
		out = _fmt_staff_breakdown(self._staff_source(), shift_hours=0, basis="Shift Hours")
		self.assertEqual(
			out,
			"- 3 Staff worked 200 Hours: 600 Hrs\n- 2 Staff worked 100 Hours: 200 Hrs",
		)

	def test_breakdown_both_joined_with_or(self):
		out = _fmt_staff_breakdown(self._staff_source(), shift_hours=0, basis="Both")
		self.assertEqual(
			out,
			"- 3 Staff worked 15 days: 45 Days\n- 2 Staff worked 10 days: 20 Days"
			"\nOR\n"
			"- 3 Staff worked 200 Hours: 600 Hrs\n- 2 Staff worked 100 Hours: 200 Hrs",
		)

	def test_breakdown_hours_falls_back_to_days_times_shift(self):
		# No numeric hours recorded -> hours group uses days x shift length.
		source = {"staff": {"X": {"name": "X", "id": "X", "days": 15, "hours": 0}}}
		out = _fmt_staff_breakdown(source, shift_hours=12, basis="Shift Hours")
		self.assertEqual(out, "- 1 Staff worked 180 Hours: 180 Hrs")

	def test_breakdown_counts_relievers_beyond_contracted(self):
		# 21 distinct individuals all appear in the breakdown even if the contract
		# only covers 20 -> group totals sum to the true worked total.
		staff = {f"E{i}": {"name": f"E{i}", "id": f"E{i}", "days": 30, "hours": 0} for i in range(21)}
		out = _fmt_staff_breakdown({"staff": staff}, shift_hours=0, basis="Attendance Day")
		self.assertEqual(out, "- 21 Staff worked 30 days: 630 Days")

	def test_contractual_days_basis(self):
		self.assertEqual(_fmt_contractual(20, "Attendance Day"), "={20 staff * 30 days} = 600 DAYS")

	def test_contractual_hours_basis(self):
		self.assertEqual(_fmt_contractual(20, "Shift Hours"), "={20 staff * 208 hours} = 4160 HOURS")

	def test_contractual_both_joined_with_or(self):
		self.assertEqual(
			_fmt_contractual(20, "Both"),
			"={20 staff * 30 days} = 600 DAYS\nOR\n={20 staff * 208 hours} = 4160 HOURS",
		)

	# --- read-only integrity (AC2) ---------------------------------------------

	def test_summary_fields_are_read_only(self):
		meta = frappe.get_meta("Proof of Work Item")
		for field in meta.fields:
			self.assertTrue(
				field.read_only,
				msg=f"Proof of Work Item field '{field.fieldname}' must be read-only",
			)

	def test_generate_skips_duplicate(self):
		generate_proof_of_work(TEST_MONTH, TEST_YEAR, [self.contract.name], "Shift Hours")
		res = generate_proof_of_work(
			TEST_MONTH, TEST_YEAR, [self.contract.name], "Shift Hours"
		)
		self.assertEqual(len(res["created"]), 0)
		self.assertEqual(len(res["skipped"]), 1)
		self.assertEqual(res["skipped"][0]["contract"], self.contract.name)

	def test_generate_rejects_invalid_basis(self):
		with self.assertRaises(frappe.ValidationError):
			generate_proof_of_work(TEST_MONTH, TEST_YEAR, [self.contract.name], "Nonsense")

	def test_generate_rejects_empty_selection(self):
		with self.assertRaises(frappe.ValidationError):
			generate_proof_of_work(TEST_MONTH, TEST_YEAR, [], "Shift Hours")

	def test_generate_rejects_invalid_month(self):
		with self.assertRaises(frappe.ValidationError):
			generate_proof_of_work(13, TEST_YEAR, [self.contract.name], "Shift Hours")


class TestOnlyContractItemsBecomeRows(FrappeTestCase):
	"""The summary reports against the contract, so its rows come from the Contract Items.

	It used to be the union of Contract Items and items with attendance, which produced two
	rows on a contract whose Service line was a uniform: one for the service actually
	worked, carrying every hour but contracted 0, and one for the contract's own item with
	nothing against it.
	"""

	def _populate(self, contracted, source):
		from unittest.mock import patch

		module = "one_fm.one_fm.doctype.proof_of_work.proof_of_work"
		doc = frappe.new_doc("Proof of Work")
		doc.contract = "_TEST-POW-ROWS"
		doc.project = "_TEST-POW-PROJECT"
		doc.generation_basis = "Attendance Day"

		with patch(f"{module}._contracted_count_by_sale_item", return_value=contracted), patch(
			f"{module}.resolve_attendance_source", return_value=("attendance", None)
		), patch(f"{module}._source_from_attendance", return_value=source), patch(
			f"{module}._rate_type_by_sale_item", return_value={}
		), patch(f"{module}._item_types_by_sale_item", return_value={}), patch(
			f"{module}._shift_hours_from_item", return_value=12.0
		):
			_populate_pow_items(doc, "2026-01-01", "2026-01-31")

		return [r.sale_item_code for r in doc.proof_of_work_item]

	def test_an_item_with_attendance_but_no_contract_line_is_not_a_row(self):
		rows = self._populate(
			contracted={"UNF-TRS-000208": 3},
			source={"SER-SEC-000136": {"days": 1318.0, "hours": 15658.97, "staff": {}}},
		)
		self.assertEqual(rows, ["UNF-TRS-000208"])

	def test_a_contract_item_with_no_attendance_is_still_a_row(self):
		# The contract committed to it, so it is reported - at zero.
		rows = self._populate(contracted={"SER-A": 2}, source={})
		self.assertEqual(rows, ["SER-A"])

	def test_every_contract_item_gets_exactly_one_row(self):
		rows = self._populate(
			contracted={"SER-A": 2, "SER-B": 1},
			source={"SER-A": {"days": 10.0, "hours": 80.0, "staff": {}}},
		)
		self.assertEqual(rows, ["SER-A", "SER-B"])

	def test_a_contract_with_no_service_items_produces_no_rows(self):
		self.assertEqual(
			self._populate(
				contracted={}, source={"SER-A": {"days": 5.0, "hours": 40.0, "staff": {}}}
			),
			[],
		)


class TestTheAttendanceSheetFollowsTheContract(FrappeTestCase):
	"""The sheet on the later pages reports the same items as the summary on page 1.

	It is built from attendance rather than from the contract, so it used to carry a
	section for a Sale Item the summary did not list - the sheet and the summary of the
	same document disagreeing about what was worked.
	"""

	def _sections(self, contracted, grid):
		from unittest.mock import patch

		module = "one_fm.one_fm.doctype.proof_of_work.proof_of_work"
		pow_doc = frappe.new_doc("Proof of Work")
		pow_doc.contract = "_TEST-POW-SHEET"
		pow_doc.project = "_TEST-POW-PROJECT"
		pow_doc.start_date = "2026-01-01"
		pow_doc.end_date = "2026-01-31"
		pow_doc.generation_basis = "Attendance Day"

		with patch(f"{module}.frappe.get_doc", return_value=pow_doc), patch(
			f"{module}.resolve_attendance_source", return_value=("attendance", None)
		), patch(f"{module}._grid_from_attendance", return_value=grid), patch(
			f"{module}._contracted_count_by_sale_item", return_value=contracted
		), patch(f"{module}._item_types_by_sale_item", return_value={}), patch(
			f"{module}._shift_hours_from_item", return_value=12.0
		), patch(f"{module}._rate_type_by_sale_item", return_value={}):
			report = get_pow_attendance_report("_TEST-POW-SHEET-DOC")

		return [g["sale_item"] for g in report["groups"]]

	def _grid_entry(self, employee):
		return {
			employee: {
				"employee_id": employee,
				"employee_name": employee,
				"days": {1: "P"},
				"total_present": 1.0,
			}
		}

	def test_an_item_with_no_contract_line_gets_no_section(self):
		sections = self._sections(
			contracted={"UNF-TRS-000208": 3},
			grid={"SER-SEC-000136": self._grid_entry("HR-EMP-03926")},
		)
		self.assertEqual(sections, [])

	def test_a_contracted_item_keeps_its_section(self):
		sections = self._sections(
			contracted={"SER-SEC-000136": 50},
			grid={"SER-SEC-000136": self._grid_entry("HR-EMP-03926")},
		)
		self.assertEqual(sections, ["SER-SEC-000136"])

	def test_only_the_contracted_items_survive_a_mixed_grid(self):
		sections = self._sections(
			contracted={"SER-A": 1, "SER-B": 2},
			grid={
				"SER-A": self._grid_entry("EMP-1"),
				"SER-B": self._grid_entry("EMP-2"),
				"SER-NOT-ON-CONTRACT": self._grid_entry("EMP-3"),
			},
		)
		self.assertEqual(sorted(sections), ["SER-A", "SER-B"])

	def test_the_print_format_has_something_to_say_when_nothing_survives(self):
		# An empty sheet must not render as a bare page.
		import json

		path = frappe.get_app_path(
			"one_fm", "one_fm", "print_format", "proof_of_work_attendance_report",
			"proof_of_work_attendance_report.json",
		)
		html = json.loads(frappe.read_file(path))["html"]
		self.assertIn("if not report.groups", html)


class TestTheWorkedColumnUsesTheRightUnit(FrappeTestCase):
	"""The "Total number Days worked OR Total No of Hours worked" column.

	It used to render hours whatever the Rate Type, and for Daily/Monthly the hours were
	days x the shift length - so a 344-day month printed "4128.00 hrs" next to a
	contractual figure quoted in DAYS. It now follows the same basis as the columns either
	side of it.
	"""

	SOURCE = {"days": 344.0, "hours": 4000.0, "staff": {}}

	def test_a_day_basis_reports_days(self):
		self.assertEqual(_fmt_actual(self.SOURCE, 12.0, "Attendance Day"), "344 Days")

	def test_a_day_basis_never_reports_hours(self):
		# The regression: days x shift length rendered as "hrs".
		self.assertNotIn("hrs", _fmt_actual(self.SOURCE, 12.0, "Attendance Day"))

	def test_an_hours_basis_reports_recorded_hours(self):
		self.assertEqual(_fmt_actual(self.SOURCE, 12.0, "Shift Hours"), "4000.00 hrs")

	def test_an_hourly_rate_type_reports_nominal_shift_hours(self):
		# Hourly items take days x the shift length, not the clock (WI-001700).
		self.assertEqual(
			_fmt_actual(self.SOURCE, 12.0, "Shift Hours", True), "4128.00 hrs"
		)

	def test_both_reports_each_unit_on_its_own_line(self):
		self.assertEqual(
			_fmt_actual(self.SOURCE, 12.0, "Both"), "344 Days\nOR\n4000.00 hrs"
		)

	def test_a_half_day_survives_the_day_count(self):
		self.assertEqual(
			_fmt_actual({"days": 20.5, "hours": 0.0}, 12.0, "Attendance Day"), "20.5 Days"
		)

	def test_no_attendance_reports_zero_in_the_right_unit(self):
		blank = {"days": 0.0, "hours": 0.0, "staff": {}}
		self.assertEqual(_fmt_actual(blank, 12.0, "Attendance Day"), "0 Days")
		self.assertEqual(_fmt_actual(blank, 12.0, "Shift Hours"), "0.00 hrs")

	def test_hours_fall_back_to_days_when_only_statuses_were_recorded(self):
		# Same fallback _actual_hours has: a source with no numeric hours.
		self.assertEqual(
			_fmt_actual({"days": 10.0, "hours": 0.0}, 8.0, "Shift Hours"), "80.00 hrs"
		)

	def test_it_agrees_with_the_column_beside_it(self):
		# Both figures in a row must be in the same unit, or the row cannot be read.
		for basis, unit in (("Attendance Day", "DAYS"), ("Shift Hours", "HOURS")):
			contractual = _fmt_contractual(20, basis)
			worked = _fmt_actual(self.SOURCE, 12.0, basis)
			self.assertIn(unit, contractual, msg=basis)
			self.assertEqual(
				unit == "DAYS", "Days" in worked, msg=f"{basis}: {contractual} vs {worked}"
			)


class TestRateTypeBasis(FrappeTestCase):
	"""
	WI-001700 update: the Contract Item's Rate Type decides which metric a Sale Item is
	reported in, unless the contract has an Attendance Amendment.
	"""

	def test_daily_and_monthly_are_counted_in_present_days(self):
		for rate_type in ("Daily", "Monthly"):
			self.assertEqual(
				_basis_for_rate_type(rate_type, "attendance", "Both"),
				"Attendance Day",
				msg=rate_type,
			)

	def test_hourly_is_counted_in_shift_hours(self):
		self.assertEqual(_basis_for_rate_type("Hourly", "attendance", "Both"), "Shift Hours")

	def test_an_amendment_keeps_the_generated_method(self):
		# "If the linked Contract has Attendance Amendment, then the data will be shown as
		# per the generated method" - the Rate Type must not override it.
		for rate_type in ("Daily", "Monthly", "Hourly", ""):
			self.assertEqual(
				_basis_for_rate_type(rate_type, "amendment", "Both"), "Both", msg=rate_type
			)
			self.assertEqual(
				_basis_for_rate_type(rate_type, "amendment", "Shift Hours"),
				"Shift Hours",
				msg=rate_type,
			)

	def test_missing_rate_type_leaves_behaviour_unchanged(self):
		# A Contract Item with no Rate Type keeps the document's basis, so nothing that
		# worked before this change starts reporting differently.
		for basis in ("Attendance Day", "Shift Hours", "Both"):
			self.assertEqual(_basis_for_rate_type("", "attendance", basis), basis, msg=basis)
			self.assertEqual(_basis_for_rate_type(None, "attendance", basis), basis, msg=basis)


class TestAttendanceReportStructure(FrappeTestCase):
	"""
	WI-001700 update: the Attendance Report print format shows the item type(s) beside the
	Sale Item Code and drops the Item Type column.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Read the shipped definition rather than the database copy: the file is what
		# migrate installs, and asserting on the DB would only pass after a migration.
		import json

		path = frappe.get_app_path(
			"one_fm", "one_fm", "print_format", "proof_of_work_attendance_report",
			"proof_of_work_attendance_report.json",
		)
		cls.print_format = frappe._dict(json.loads(frappe.read_file(path)))

	def test_item_type_column_is_gone(self):
		self.assertNotIn("Item Type</th>", self.print_format.html)

	def test_item_types_are_shown_beside_the_sale_item_code(self):
		self.assertIn("group.sale_item", self.print_format.html)
		self.assertIn("group.item_type", self.print_format.html)

	def test_grid_carries_the_columns_from_the_agreed_structure(self):
		for column in ("Employee ID", "Employee Name", "Working Days", "Days Off", "Total Hours"):
			self.assertIn(f"{column}</th>", self.print_format.html, msg=column)

	def test_header_repeats_without_overlapping_tall_rows(self):
		# wkhtmltopdf overlaps a repeated thead with tall rows unless it is a row group.
		self.assertIn("display: table-row-group", self.print_format.css)


class TestAttendanceAbbreviations(FrappeTestCase):
	"""
	The day cells must carry the legend's abbreviations. Day Off previously fell through to
	its initial ("D"), so the Days Off column added to the report could never count it.
	"""

	def test_day_off_statuses_use_the_legend_codes(self):
		self.assertEqual(_attendance_abbr("Day Off"), "DO")
		self.assertEqual(_attendance_abbr("Client Day Off"), "CDO")

	def test_day_off_codes_are_the_ones_the_report_counts(self):
		self.assertEqual(
			{_attendance_abbr("Day Off"), _attendance_abbr("Client Day Off")}, DAY_OFF_ABBRS
		)

	def test_half_day_no_longer_collides_with_holiday(self):
		self.assertEqual(_attendance_abbr("Half Day"), "HD")
		self.assertEqual(_attendance_abbr("Holiday"), "H")
		self.assertNotEqual(_attendance_abbr("Half Day"), _attendance_abbr("Holiday"))

	def test_every_status_in_use_has_an_abbreviation(self):
		# Statuses present in the live data; none should fall back to a bare initial.
		for status in (
			"Present", "Day Off", "On Leave", "Absent", "On Hold", "Client Day Off",
			"Holiday", "Work From Home", "Medical Appointment", "Client Interview",
			"Fingerprint Appointment", "Half Day",
		):
			self.assertIn(status, ATTENDANCE_ABBR, msg=status)

	def test_unknown_status_falls_back_to_its_initial(self):
		self.assertEqual(_attendance_abbr("Suspended"), "S")
		self.assertEqual(_attendance_abbr(""), "")
		self.assertEqual(_attendance_abbr(None), "")


class TestHourlyReportsNominalShiftHours(FrappeTestCase):
	"""
	WI-001700 update: an Hourly Sale Item "Fetch Shift Hours", so hours are the shift
	length x days present and come out whole. Recorded working_hours are what produced the
	decimal figures (540.96, 537.93) that prompted this.
	"""

	def _staff(self):
		# 45 days present, but the clock recorded a fractional total
		return {"staff": {"E1": {"name": "E1", "id": "E1", "days": 45, "hours": 540.96}}}

	def test_hourly_uses_shift_length_not_the_clock(self):
		out = _fmt_staff_breakdown(
			self._staff(), shift_hours=12, basis="Shift Hours", nominal_shift_hours=True
		)
		self.assertEqual(out, "- 1 Staff worked 540 Hours: 540 Hrs")
		self.assertNotIn("540.96", out)

	def test_recorded_hours_still_used_when_not_rate_driven(self):
		# The amendment path shows data as generated, so the clock still wins there.
		out = _fmt_staff_breakdown(self._staff(), shift_hours=12, basis="Shift Hours")
		self.assertIn("540.96", out)

	def test_actual_hours_total_follows_the_same_rule(self):
		source = {"days": 45, "hours": 540.96, "staff": {}}
		self.assertEqual(
			_actual_hours(source, 12, "Shift Hours", nominal_shift_hours=True), 540
		)
		self.assertEqual(_actual_hours(source, 12, "Shift Hours"), 540.96)

	def test_only_hourly_without_an_amendment_uses_the_shift_length(self):
		self.assertTrue(_uses_nominal_shift_hours("Hourly", "attendance"))
		self.assertFalse(_uses_nominal_shift_hours("Hourly", "amendment"))
		for rate_type in ("Daily", "Monthly", ""):
			self.assertFalse(_uses_nominal_shift_hours(rate_type, "attendance"), msg=rate_type)


class TestReportDayHeader(FrappeTestCase):
	"""WI-001700 update: the day columns carry weekday over d/m, as the sample shows."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		import json

		path = frappe.get_app_path(
			"one_fm", "one_fm", "print_format", "proof_of_work_attendance_report",
			"proof_of_work_attendance_report.json",
		)
		cls.print_format = frappe._dict(json.loads(frappe.read_file(path)))

	def test_day_columns_have_two_header_rows(self):
		self.assertIn("label.weekday", self.print_format.html)
		self.assertIn("label.date", self.print_format.html)

	def test_fixed_columns_span_both_header_rows(self):
		# Employee ID/Name and the three totals must not repeat on the second row.
		self.assertIn('class="c-id" rowspan="2"', self.print_format.html)
		self.assertIn('class="c-name" rowspan="2"', self.print_format.html)
		# Each totals column carries its own class as well as c-num since WI-001983.
		for column in ("c-worked-days", "c-days-off", "c-total-hours"):
			self.assertIn(f'class="c-num {column}" rowspan="2"', self.print_format.html)

	def test_the_totals_columns_have_separate_widths(self):
		"""WI-001983: "Working Days" and "Days Off" ran together inside one 32px width."""
		for column in ("c-worked-days", "c-days-off", "c-total-hours"):
			self.assertIn(f".pow-grid .{column} {{ width:", self.print_format.css)

	def test_the_header_line_carries_the_report_period_on_the_right(self):
		"""WI-001983: logo and title left, Report Period right, on one line."""
		self.assertIn('<td class="pow-hd-right"><strong>Report Period:</strong>', self.print_format.html)
		# And it is not also left in the metadata line below.
		metadata = self.print_format.html.split('<div class="pow-meta">')[1].split("</div>")[0]
		self.assertNotIn("Report Period", metadata)

	def test_the_metadata_reads_client_then_project_then_contract(self):
		metadata = self.print_format.html.split('<div class="pow-meta">')[1].split("</div>")[0]
		labels = re.findall(r"<strong>(.*?):</strong>", metadata)

		self.assertEqual(labels, ["Client", "Project", "Contract"])


class TestSafeFilename(FrappeTestCase):
	"""WI-001808: ``<client> - <contract> - <MMM-YYYY>.pdf``, safe for a ZIP entry."""

	def test_separators_are_scrubbed(self):
		self.assertEqual(_safe_filename("A/B:C*D?"), "A B C D")
		self.assertEqual(_safe_filename('a"b<c>d|e'), "a b c d e")

	def test_whitespace_runs_collapse(self):
		self.assertEqual(_safe_filename("  spaced   out  "), "spaced out")
		self.assertEqual(_safe_filename("line\nbreak\ttab"), "line break tab")

	def test_name_follows_the_agreed_pattern(self):
		self.assertEqual(
			pdf_file_name("Aesop", "Mizzen-Aesop-2025-11-02", "2025-11-01"),
			"Aesop - Mizzen-Aesop-2025-11-02 - Nov-2025.pdf",
		)

	def test_a_slash_in_the_contract_name_cannot_escape_the_archive(self):
		# A ZIP entry called "../x.pdf" would write outside the extraction root.
		self.assertNotIn("/", pdf_file_name("ACME", "../../etc/passwd", "2025-11-01"))

	def test_blank_components_do_not_leave_dangling_separators(self):
		self.assertEqual(pdf_file_name("", "CON-1", "2025-11-01"), "CON-1 - Nov-2025.pdf")


class TestNonManpowerRollup(FrappeTestCase):
	"""
	WI-001808: Contract Items with Item Type "Items" carry no attendance, so they are
	reported as a contracted amount per Contract Item Category. ``rate`` is the figure
	consistently filled in production, with ``amount`` as the fallback.
	"""

	def setUp(self):
		self.company = _get_company()
		self.customer = _get_or_create_customer()
		self.project = _get_or_create_project(self.company)
		self.first_day = get_first_day(getdate(f"{TEST_YEAR}-{TEST_MONTH:02d}-01"))
		self.last_day = get_last_day(self.first_day)
		self.contract = TestProofofWork._make_contract(self, "_Test POW NM Contract")

	def _add_item(self, category, item_type="Items", rate=0.0, amount=0.0):
		"""Insert a Contract Item child row, bypassing the committing controller."""
		row = frappe.new_doc("Contract Item")
		row.parent = self.contract.name
		row.parenttype = "Contracts"
		row.parentfield = "items"
		row.contract_item_category = category
		row.item_type = item_type
		row.rate = rate
		row.amount = amount
		row.db_insert()

	def _category(self, label):
		if not frappe.db.exists("Contract Item Category", label):
			frappe.get_doc(
				{"doctype": "Contract Item Category", "contract_item_category": label}
			).insert(ignore_permissions=True)
		return label

	def test_rate_is_used_when_present(self):
		self._add_item(self._category("_Test Handyman"), rate=100.0, amount=0.0)
		rows = _non_manpower_amount_by_category(self.contract.name)
		self.assertEqual(rows, [{"contract_item_category": "_Test Handyman", "amount": 100.0}])

	def test_amount_is_the_fallback_when_rate_is_zero(self):
		self._add_item(self._category("_Test Plumbing"), rate=0.0, amount=150.0)
		rows = _non_manpower_amount_by_category(self.contract.name)
		self.assertEqual(rows[0]["amount"], 150.0)

	def test_rate_wins_where_the_two_disagree(self):
		# Production has exactly this shape: rate 50.00 against amount 150.00.
		self._add_item(self._category("_Test Plumbing"), rate=50.0, amount=150.0)
		rows = _non_manpower_amount_by_category(self.contract.name)
		self.assertEqual(rows[0]["amount"], 50.0)

	def test_rows_sharing_a_category_are_summed(self):
		category = self._category("_Test Pest Control")
		self._add_item(category, rate=80.0)
		self._add_item(category, rate=20.0)
		rows = _non_manpower_amount_by_category(self.contract.name)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["amount"], 100.0)

	def test_service_rows_are_excluded(self):
		# "Service" lines are the manpower ones and belong to the other table.
		self._add_item(self._category("_Test Janitorial"), item_type="Service", rate=999.0)
		self.assertEqual(_non_manpower_amount_by_category(self.contract.name), [])

	def test_rows_without_a_category_are_skipped(self):
		self._add_item(None, rate=42.0)
		self.assertEqual(_non_manpower_amount_by_category(self.contract.name), [])

	def test_categories_come_back_ordered(self):
		self._add_item(self._category("_Test Zeta"), rate=1.0)
		self._add_item(self._category("_Test Alpha"), rate=2.0)
		rows = _non_manpower_amount_by_category(self.contract.name)
		self.assertEqual(
			[r["contract_item_category"] for r in rows], ["_Test Alpha", "_Test Zeta"]
		)

	def test_a_contract_with_no_items_returns_nothing(self):
		self.assertEqual(_non_manpower_amount_by_category(self.contract.name), [])

	def test_generation_fills_the_table_and_submits(self):
		self._add_item(self._category("_Test Handyman"), rate=100.0)
		res = generate_proof_of_work(TEST_MONTH, TEST_YEAR, [self.contract.name])

		self.assertEqual(len(res["created"]), 1, msg=res["skipped"])
		pow_doc = frappe.get_doc("Proof of Work", res["created"][0])

		# Bulk generation submits (AC: "all the POW record shall be submitted").
		self.assertEqual(pow_doc.docstatus, 1)
		# The dialog no longer asks for a basis, so the default is stamped on.
		self.assertEqual(pow_doc.generation_basis, DEFAULT_GENERATION_BASIS)

		self.assertEqual(len(pow_doc.proof_of_work_items_nonmanpower), 1)
		self.assertEqual(
			pow_doc.proof_of_work_items_nonmanpower[0].contract_item_category,
			"_Test Handyman",
		)
		self.assertEqual(pow_doc.proof_of_work_items_nonmanpower[0].amount, 100.0)


class TestLetterCarriesTheNonManpowerTable(FrappeTestCase):
	"""WI-001808: the rollup is reflected in the Letter, right-to-left, with a total."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		import json

		path = frappe.get_app_path(
			"one_fm", "one_fm", "print_format", "proof_of_work_letter",
			"proof_of_work_letter.json",
		)
		cls.print_format = frappe._dict(json.loads(frappe.read_file(path)))

	def test_the_table_is_rendered_from_the_new_child_table(self):
		self.assertIn("doc.proof_of_work_items_nonmanpower", self.print_format.html)
		self.assertIn("row.contract_item_category", self.print_format.html)

	def test_it_reuses_the_right_to_left_table_styling(self):
		# .pow-tbl is the RTL table class; the new table opts into it.
		self.assertIn('class="pow-tbl nm-tbl"', self.print_format.html)
		self.assertIn("direction: rtl", self.print_format.css)

	def test_it_carries_a_total_row(self):
		self.assertIn("nm-total", self.print_format.html)
		self.assertIn('sum(attribute="amount")', self.print_format.html)


class TestHourlyDayCells(FrappeTestCase):
	"""A Sale Item reported in hours shows the rostered shift length in its day cells,
	not the hours clocked (WI-001808) - the same figure the summary counts it in.
	"""

	def test_a_worked_day_shows_the_rostered_shift_length(self):
		self.assertEqual(_hour_cells(["P", "P", "P"], shift_hours=12), ["12", "12", "12"])

	def test_the_length_follows_the_sale_item(self):
		self.assertEqual(_hour_cells(["P"], shift_hours=9), ["9"])
		self.assertEqual(_hour_cells(["P"], shift_hours=8), ["8"])

	def test_it_is_the_rostered_length_not_the_hours_clocked(self):
		# Every worked day reads the same figure, whatever the employee actually
		# clocked - which is what the summary counts an Hourly item in.
		self.assertEqual(set(_hour_cells(["P"] * 5, shift_hours=12)), {"12"})

	def test_a_day_not_worked_keeps_its_abbreviation(self):
		# "0" against an absence reads as a figure rather than an explanation.
		self.assertEqual(_hour_cells(["P", "DO", "A"], shift_hours=8), ["8", "DO", "A"])

	def test_a_half_day_carries_half_a_shift(self):
		# Which is how it is already counted towards the day total.
		self.assertEqual(_hour_cells(["HD"], shift_hours=12), ["6"])

	def test_an_empty_day_stays_empty(self):
		self.assertEqual(_hour_cells(["", ""], shift_hours=12), ["", ""])

	def test_the_totals_are_left_alone(self):
		# Working Days counts attendance records and an employee can hold more than one
		# a day, so the cells - one per calendar day - are not summed into the total.
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "one_fm", "doctype", "proof_of_work", "proof_of_work.py"
			)
		)
		self.assertIn('"total_hours": _num(working_days * shift_hours)', source)

	def test_the_worked_set_tracks_the_present_statuses(self):
		# Derived rather than restated, so a new present status cannot start reporting
		# as an unworked day.
		self.assertIn("P", WORKED_ABBRS)
		self.assertIn("HD", WORKED_ABBRS)
		self.assertNotIn("DO", WORKED_ABBRS)
		self.assertNotIn("A", WORKED_ABBRS)

	def test_the_sheet_follows_the_same_basis_as_the_summary(self):
		# The gate calls _basis_for_rate_type - page 1's own function - so the two
		# pages cannot end up reporting one Sale Item in two different metrics.
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "one_fm", "doctype", "proof_of_work", "proof_of_work.py"
			)
		)
		grid = source.split("def get_pow_attendance_report")[1]
		self.assertIn("_basis_for_rate_type(", grid)
		self.assertIn('by_hours = basis == "Shift Hours"', grid)



class TestTheLetterHeadingsFollowTheRateType(FrappeTestCase):
	"""WI-001983: each figure column is headed after the units the contract bills in.

	Daily and Monthly are counted in days, Hourly in hours. A contract that mixes them
	keeps the OR - the column really does hold both across its rows - and one that does
	not stops asking the reader to pick a line.
	"""

	def _headers(self, *rate_types):
		from unittest.mock import patch

		from one_fm.jinja.print_format.methods import pow_letter_headers

		doc = frappe.new_doc("Proof of Work")
		doc.contract = "_TEST-CONTRACT"
		doc.project = "_TEST-PROJECT"
		doc.start_date = "2026-07-01"
		doc.generation_basis = "Both"
		by_item = {}
		for index, rate_type in enumerate(rate_types):
			item = f"ITEM-{index}"
			doc.append("proof_of_work_item", {"sale_item_code": item})
			if rate_type:
				by_item[item] = rate_type

		module = "one_fm.one_fm.doctype.proof_of_work.proof_of_work"
		with patch(f"{module}._rate_type_by_sale_item", return_value=by_item), patch(
			f"{module}.resolve_attendance_source", return_value=("attendance", None)
		):
			return pow_letter_headers(doc)

	def _english(self, column):
		return [line.get("en") for line in column if not line.get("separator")]

	def _has_or(self, column):
		return any(line.get("separator") for line in column)

	def test_a_daily_and_monthly_contract_is_headed_in_days(self):
		headers = self._headers("Daily", "Monthly")

		self.assertEqual(self._english(headers["contractual"]), ["Contractual Number of days per month"])
		self.assertEqual(self._english(headers["worked"]), ["Total number Days worked"])
		self.assertEqual(self._english(headers["breakdown"]), ["Total Number of Days"])
		for column in headers.values():
			self.assertFalse(self._has_or(column))

	def test_an_hourly_contract_is_headed_in_hours(self):
		headers = self._headers("Hourly", "Hourly")

		self.assertEqual(self._english(headers["contractual"]), ["Contractual number of hours per month"])
		self.assertEqual(self._english(headers["worked"]), ["Total No of Hours worked"])
		self.assertEqual(self._english(headers["breakdown"]), ["Total Number of Hours"])
		for column in headers.values():
			self.assertFalse(self._has_or(column))

	def test_a_contract_that_mixes_them_keeps_the_or(self):
		"""Al Babtain is Hourly and Monthly together, so its column holds both."""
		headers = self._headers("Hourly", "Monthly")

		for column in headers.values():
			self.assertTrue(self._has_or(column))
		self.assertEqual(
			self._english(headers["worked"]),
			["Total number Days worked", "Total No of Hours worked"],
		)

	def test_an_item_with_no_rate_type_names_both(self):
		"""Nothing decides its unit, so the row reports both and the heading says so."""
		headers = self._headers("Monthly", None)

		self.assertTrue(self._has_or(headers["worked"]))

	def test_the_breakdown_column_keeps_its_arabic_in_both_units(self):
		days = self._headers("Monthly")["breakdown"]
		hours = self._headers("Hourly")["breakdown"]

		self.assertEqual(days[0]["ar"], "اجمالي عدد ايام عمل")
		self.assertEqual(hours[0]["ar"], "اجمالي عدد ساعات عمل")

	def test_the_other_two_columns_carry_no_arabic(self):
		"""They never did - only the breakdown column is bilingual."""
		headers = self._headers("Monthly")

		for column in ("contractual", "worked"):
			for line in headers[column]:
				self.assertFalse(line.get("ar"))

	def test_a_document_with_no_rows_names_both(self):
		headers = self._headers()

		self.assertTrue(self._has_or(headers["contractual"]))


class TestTheLetterSurvivesADeployGap(FrappeTestCase):
	"""The method arrives with the app code, the print format with the database. A
	migrate not yet followed by a restart has one without the other, and an undefined
	Jinja method fails the whole PDF rather than one heading."""

	def _heading_line(self):
		import json

		path = frappe.get_app_path(
			"one_fm", "one_fm", "print_format", "proof_of_work_letter",
			"proof_of_work_letter.json",
		)
		html = json.loads(frappe.read_file(path))["html"]
		start = html.index("{%- set headers")
		return html[start:html.index("-%}", start) + 3]

	def test_the_heading_still_renders_without_the_method(self):
		import jinja2

		rendered = jinja2.Environment().from_string(
			self._heading_line() + "{{ headers.worked | map(attribute='en') | select | join('|') }}"
		).render()

		self.assertEqual(rendered, "Total number Days worked|Total No of Hours worked")

	def test_the_method_is_registered_in_hooks(self):
		"""The fallback is insurance, not the plan."""
		from one_fm import hooks

		self.assertIn(
			"pow_letter_headers:one_fm.jinja.print_format.methods.pow_letter_headers",
			hooks.jenv["methods"],
		)
