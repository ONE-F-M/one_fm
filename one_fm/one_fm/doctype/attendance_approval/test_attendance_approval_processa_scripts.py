# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Attendance Approval process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm import processa_rules

SCRIPTS = {
	"Calculate Attendance Approval Working Days": """# Working and off days of every attendance and overtime row. Every save runs recount() through
# the controller; in the map it runs before the record goes for review.
WORKING = ("Present", "Working", "Work From Home")
OFF = ("Day Off", "Client Day Off")


def recount(doc):
	use_hours = doc.attendance_based_on in ("Shift Hours", "Working Hours")
	for row in list(doc.get("attendance_details") or []) + list(doc.get("overtime_details") or []):
		working_days = off_days = 0
		for i in range(1, 32):
			val = row.get(f"day_{i}")
			if val in OFF:
				off_days += 1
			elif use_hours:
				if frappe.utils.flt(row.get(f"day_{i}_hour")) > 0:
					working_days += 1
			elif val in WORKING:
				working_days += 1
			elif val == "Half Day":
				working_days += 0.5
		row.working_days = working_days
		row.off_days = off_days


if bpmn_id:
	recount(doc)
	for row in list(doc.attendance_details) + list(doc.overtime_details):
		frappe.db.set_value(row.doctype, row.name, {"working_days": row.working_days, "off_days": row.off_days}, update_modified=False)
""",
	"Validate Attendance Approval Submission": """# Checks the record can go for review. Sets result["step_valid"]; on False the process reopens Draft.
result["step_valid"] = bool(doc.attendance_details)
if not result["step_valid"]:
	frappe.msgprint(
		frappe._("Attendance Details are empty. Select Attendance Record Based On and click Fetch Attendance Record before submitting for review."),
		title=frappe._("Cannot Submit for Review"),
		indicator="red",
	)
""",
}


def run(script_name, doc, **task_data):
	"""Run a script the way the Processa engine does and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc,
		"task_data": task_data,
		"result": result,
		"context_doctype": "Attendance Approval",
		"context_docname": doc.name,
		"bpmn_id": "test",
	}
	with patch("frappe.msgprint"):
		exec(SCRIPTS[script_name], namespace)
	return result


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is None:
				continue
			self.assertEqual(saved.strip(), body.strip(), name)


RULES = "Calculate Attendance Approval Working Days"


def recount(doc):
	namespace = {"frappe": frappe, "doc": frappe._dict(), "task_data": {}, "result": {}, "bpmn_id": ""}
	exec(SCRIPTS[RULES], namespace)
	namespace["recount"](doc)


def approval(based_on="Attendance Status", **days):
	doc = frappe.new_doc("Attendance Approval")
	doc.attendance_based_on = based_on
	doc.append("attendance_details", days)
	return doc


class TestCalculateWorkingDays(FrappeTestCase):
	def test_status_mode_counts_half_days_and_offs(self):
		doc = approval(day_1="Present", day_2="Half Day", day_3="Day Off", day_4="Absent", day_5="Work From Home")
		recount(doc)
		self.assertEqual(doc.attendance_details[0].working_days, 2.5)
		self.assertEqual(doc.attendance_details[0].off_days, 1)

	def test_hours_mode_counts_days_with_hours(self):
		doc = approval("Shift Hours", day_1="Present", day_1_hour="8", day_2="Day Off", day_3="Absent", day_3_hour="N/A", day_4="Present", day_4_hour="0")
		recount(doc)
		self.assertEqual(doc.attendance_details[0].working_days, 1)
		self.assertEqual(doc.attendance_details[0].off_days, 1)

	def test_controller_runs_the_site_rule(self):
		doc = approval(day_1="Present")
		with patch.object(processa_rules, "run_rule") as rule:
			from one_fm.one_fm.doctype.attendance_approval.attendance_approval import AttendanceApproval
			AttendanceApproval.recalculate_working_days(doc)
		rule.assert_called_once_with(RULES, "recount", doc)


class TestValidateAttendanceApprovalSubmission(FrappeTestCase):
	def test_empty_details_stop_the_submission(self):
		self.assertFalse(run("Validate Attendance Approval Submission", frappe.new_doc("Attendance Approval"))["step_valid"])

	def test_details_let_it_through(self):
		self.assertTrue(run("Validate Attendance Approval Submission", approval(day_1="Present"))["step_valid"])

	def test_controller_no_longer_blocks_pending_approval(self):
		from one_fm.one_fm.doctype.attendance_approval.attendance_approval import AttendanceApproval
		self.assertFalse(hasattr(AttendanceApproval, "validate_attendance_details_present"))
