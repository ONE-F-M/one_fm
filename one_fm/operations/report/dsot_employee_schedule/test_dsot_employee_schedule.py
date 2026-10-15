# Copyright (c) 2026, One FM and contributors
# For license information, please see license.txt
"""The DSOT Employee Schedule report and the backfill that feeds it.

Rows are written straight to the table: the report and the patch read columns, and going
through the controller would pull in shift, employee and roster rules that have nothing to
do with what is under test.
"""

import json
import re

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.operations.report.dsot_employee_schedule.dsot_employee_schedule import execute
from one_fm.patches.v15_0.backfill_dsot_request import execute as backfill

REPORT_DIR = ("one_fm", "operations", "report", "dsot_employee_schedule")
PATCH = "one_fm.patches.v15_0.backfill_dsot_request"

PENDING = "Pending DSOT Approval"
ACTIVE = "Active"
REJECTED = "Rejected"
OVERTIME = "Over-Time"
BASIC = "Basic"

MARCH = {"from_date": "2031-03-01", "to_date": "2031-03-31"}


def _insert_schedule(name, workflow_state, roster_type=OVERTIME, dsot_request=None,
		date="2031-03-10", **fields):
	doc = frappe.get_doc({
		"doctype": "Employee Schedule",
		"name": name,
		"date": date,
		"employee": fields.pop("employee", "TEST-DSOT-EMP-1"),
		"employee_name": fields.pop("employee_name", "Test DSOT Employee"),
		"roster_type": roster_type,
		"dsot_request": dsot_request,
		**fields,
	})
	doc.set_user_and_timestamp()
	doc.db_insert()
	frappe.db.set_value("Employee Schedule", name, "workflow_state", workflow_state,
		update_modified=False)
	return name


def _insert_version(docname, data):
	doc = frappe.get_doc({
		"doctype": "Version",
		"name": frappe.generate_hash(length=10),
		"ref_doctype": "Employee Schedule",
		"docname": docname,
		"data": data,
	})
	doc.set_user_and_timestamp()
	doc.db_insert()


def _read_report_file(name):
	return frappe.read_file(frappe.get_app_path(*REPORT_DIR, name))


class TestDsotEmployeeScheduleReport(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.pending = _insert_schedule("TDSOT-PENDING", PENDING, dsot_request="TDSOT-PENDING")
		self.approved = _insert_schedule("TDSOT-APPROVED", ACTIVE, dsot_request="TDSOT-APPROVED")
		self.rejected = _insert_schedule("TDSOT-REJECTED", REJECTED, dsot_request="TDSOT-REJECTED")
		# Ordinary overtime that was never held: Active, Over-Time, no marker.
		self.ordinary = _insert_schedule("TDSOT-ORDINARY", ACTIVE)
		# A basic roster row is never a DSOT, even if something left a marker on it.
		self.basic = _insert_schedule("TDSOT-BASIC", ACTIVE, roster_type=BASIC,
			dsot_request="TDSOT-BASIC")
		# A DSOT state the report does not show.
		self.suspended = _insert_schedule("TDSOT-SUSPENDED", "Suspended",
			dsot_request="TDSOT-SUSPENDED")

	def _names(self, **filters):
		_, data, *_ = execute({**MARCH, **filters})
		return {row.name for row in data}

	def test_it_lists_only_overtime_rows_that_carry_the_marker(self):
		names = self._names()

		self.assertEqual(names, {self.pending, self.approved, self.rejected})

	def test_ordinary_active_overtime_is_not_counted_as_approved(self):
		self.assertNotIn(self.ordinary, self._names())
		self.assertNotIn(self.ordinary, self._names(workflow_state="Approved"))

	def test_basic_rows_are_excluded(self):
		self.assertNotIn(self.basic, self._names())

	def test_other_workflow_states_are_excluded(self):
		self.assertNotIn(self.suspended, self._names())

	def test_the_approved_option_means_active(self):
		self.assertEqual(self._names(workflow_state="Approved"), {self.approved})

	def test_the_pending_and_rejected_options(self):
		self.assertEqual(self._names(workflow_state="Pending DSOT Approval"), {self.pending})
		self.assertEqual(self._names(workflow_state="Rejected"), {self.rejected})

	def test_active_is_shown_as_approved(self):
		_, data, *_ = execute({**MARCH})
		states = {row.name: row.workflow_state for row in data}

		self.assertEqual(states[self.pending], PENDING)
		self.assertEqual(states[self.approved], "Approved")
		self.assertEqual(states[self.rejected], REJECTED)

	def test_the_date_range_applies_inclusively(self):
		later = _insert_schedule("TDSOT-LATER", PENDING, dsot_request="TDSOT-LATER",
			date="2031-04-01")

		self.assertNotIn(later, self._names())
		names = self._names(from_date="2031-03-10", to_date="2031-04-01")
		self.assertIn(later, names)
		self.assertIn(self.pending, names)
		self.assertEqual(self._names(from_date="2031-03-11", to_date="2031-03-31"), set())

	def test_the_employee_filter(self):
		other = _insert_schedule("TDSOT-OTHER-EMP", PENDING, dsot_request="TDSOT-OTHER-EMP",
			employee="TEST-DSOT-EMP-2")

		self.assertEqual(self._names(employee="TEST-DSOT-EMP-2"), {other})
		self.assertNotIn(other, self._names(employee="TEST-DSOT-EMP-1"))

	def test_the_project_and_site_filters(self):
		meta = frappe.get_meta("Employee Schedule")
		self.assertTrue(meta.has_field("project"))
		self.assertTrue(meta.has_field("site"))

		frappe.db.set_value("Employee Schedule", self.pending,
			{"project": "TEST DSOT PROJECT", "site": "TEST DSOT SITE"}, update_modified=False)

		self.assertEqual(self._names(project="TEST DSOT PROJECT"), {self.pending})
		self.assertEqual(self._names(site="TEST DSOT SITE"), {self.pending})
		self.assertEqual(self._names(project="NO SUCH PROJECT"), set())

	def test_the_rows_come_newest_date_first_then_by_employee(self):
		_insert_schedule("TDSOT-NEWER", PENDING, dsot_request="TDSOT-NEWER", date="2031-03-20")
		_insert_schedule("TDSOT-SAME-DAY", PENDING, dsot_request="TDSOT-SAME-DAY",
			employee="TEST-DSOT-EMP-0")
		_, data, *_ = execute({**MARCH})

		self.assertEqual(data[0].name, "TDSOT-NEWER")
		same_day = [row for row in data if str(row.date) == "2031-03-10"]
		self.assertEqual(same_day[0].name, "TDSOT-SAME-DAY")

	def test_from_date_after_to_date_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			execute({"from_date": "2031-03-31", "to_date": "2031-03-01"})

	def test_the_summary_cards_count_the_fetched_rows(self):
		_insert_schedule("TDSOT-PENDING-2", PENDING, dsot_request="TDSOT-PENDING-2")
		_insert_schedule("TDSOT-REJECTED-2", REJECTED, dsot_request="TDSOT-REJECTED-2")
		_insert_schedule("TDSOT-REJECTED-3", REJECTED, dsot_request="TDSOT-REJECTED-3")

		columns, data, message, chart, summary = execute({**MARCH})

		self.assertEqual(
			[(card["label"], card["value"], card["indicator"], card["datatype"]) for card in summary],
			[
				("Pending DSOT Approval", 2, "Orange", "Int"),
				("Approved DSOT", 1, "Green", "Int"),
				("Rejected DSOT", 3, "Red", "Int"),
			],
		)
		self.assertEqual(sum(card["value"] for card in summary), len(data))
		self.assertIsNone(message)
		self.assertIsNone(chart)

	def test_the_summary_follows_the_filters(self):
		*_, summary = execute({**MARCH, "workflow_state": "Approved"})

		self.assertEqual([card["value"] for card in summary], [0, 1, 0])

	def test_the_columns(self):
		columns, *_ = execute({**MARCH})

		self.assertEqual(
			[c["label"] for c in columns],
			["Schedule ID", "Date", "Employee ID", "Employee Name", "Project", "Site",
				"Operations Shift", "Operations Role", "Start Datetime", "End Datetime",
				"Workflow State"],
		)


class TestTheReportScaffold(FrappeTestCase):
	def test_the_definition(self):
		report = json.loads(_read_report_file("dsot_employee_schedule.json"))

		self.assertEqual(report["report_type"], "Script Report")
		self.assertEqual(report["is_standard"], "Yes")
		self.assertEqual(report["ref_doctype"], "Employee Schedule")
		self.assertEqual(report["module"], "Operations")
		self.assertEqual(
			{r["role"] for r in report["roles"]},
			{"System Manager", "Operations Manager", "Projects Manager"},
		)

	def test_the_filters_are_in_order(self):
		fieldnames = re.findall(r'fieldname: "(\w+)"',
			_read_report_file("dsot_employee_schedule.js"))

		self.assertEqual(
			fieldnames,
			["from_date", "to_date", "project", "site", "employee", "workflow_state"],
		)

	def test_the_workflow_state_options(self):
		script = _read_report_file("dsot_employee_schedule.js")

		self.assertIn('options: "\\nPending DSOT Approval\\nApproved\\nRejected"', script)

	def test_the_dates_are_required(self):
		script = _read_report_file("dsot_employee_schedule.js")

		self.assertEqual(script.count("reqd: 1"), 2)

	def test_the_patch_is_registered_after_model_sync(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		section = None
		sections = {}
		for line in patches.splitlines():
			line = line.strip()
			if line.startswith("[") and line.endswith("]"):
				section = line
			elif line and section:
				sections.setdefault(section, []).append(line.split("#")[0].strip())

		self.assertIn(PATCH, sections.get("[post_model_sync]", []))
		self.assertNotIn(PATCH, sections.get("[pre_model_sync]", []))


class TestTheBackfill(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		pending_in_history = json.dumps(
			{"changed": [["workflow_state", PENDING, ACTIVE]]}, separators=(",", ":"))

		self.pending = _insert_schedule("TBF-PENDING", PENDING)
		self.rejected = _insert_schedule("TBF-REJECTED", REJECTED)
		self.once_held = _insert_schedule("TBF-ONCE-HELD", ACTIVE)
		_insert_version(self.once_held, pending_in_history)
		self.ordinary = _insert_schedule("TBF-ORDINARY", ACTIVE)
		self.basic_pending = _insert_schedule("TBF-BASIC-PENDING", PENDING, roster_type=BASIC)
		self.basic_once_held = _insert_schedule("TBF-BASIC-ONCE-HELD", ACTIVE, roster_type=BASIC)
		_insert_version(self.basic_once_held, pending_in_history)
		self.marked = _insert_schedule("TBF-MARKED", PENDING, dsot_request="TBF-GROUP")
		self.unrelated_history = _insert_schedule("TBF-UNRELATED-HISTORY", ACTIVE)
		_insert_version(self.unrelated_history,
			json.dumps({"changed": [["workflow_state", "Draft", ACTIVE]]}, separators=(",", ":")))

	def _marker(self, name):
		return frappe.db.get_value("Employee Schedule", name, "dsot_request") or None

	def test_held_rows_are_marked_with_their_own_name(self):
		backfill()

		self.assertEqual(self._marker(self.pending), self.pending)
		self.assertEqual(self._marker(self.rejected), self.rejected)

	def test_an_approved_row_is_found_through_its_version_history(self):
		backfill()

		self.assertEqual(self._marker(self.once_held), self.once_held)

	def test_active_overtime_with_no_hold_in_its_history_is_left_alone(self):
		backfill()

		self.assertIsNone(self._marker(self.ordinary))
		self.assertIsNone(self._marker(self.unrelated_history))

	def test_basic_rows_are_left_alone(self):
		backfill()

		self.assertIsNone(self._marker(self.basic_pending))
		self.assertIsNone(self._marker(self.basic_once_held))

	def test_an_existing_marker_is_kept(self):
		backfill()

		self.assertEqual(self._marker(self.marked), "TBF-GROUP")

	def test_running_it_twice_changes_nothing_more(self):
		backfill()
		first = {name: self._marker(name) for name in (
			self.pending, self.once_held, self.ordinary, self.marked)}
		backfill()
		second = {name: self._marker(name) for name in first}

		self.assertEqual(first, second)

	def test_the_report_then_lists_the_backfilled_rows(self):
		backfill()
		_, data, *_ = execute({**MARCH})
		names = {row.name for row in data}

		self.assertTrue({self.pending, self.rejected, self.once_held, self.marked} <= names)
		self.assertFalse({self.ordinary, self.basic_pending, self.basic_once_held} & names)
