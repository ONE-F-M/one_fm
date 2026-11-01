# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Overtime Request Lifecycle process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

SCRIPTS = {
	"Validate Overtime Request": """# Checks made when the request is submitted: no other request for the same employee,
# date, start and end time; no approved leave on the overtime date when the employee
# raised the request; no more than 180 overtime hours in the year.
errors = []

duplicate = frappe.db.exists(
	"Overtime Request",
	{
		"employee": doc.employee,
		"date": doc.date,
		"name": ["!=", doc.name],
		"start_time": doc.start_time,
		"end_time": doc.end_time,
	},
)
if duplicate:
	errors.append(
		frappe._("Already exists an Overtime Request {0} for employee {1} on {2}!").format(
			duplicate, doc.employee, doc.date
		)
	)

employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
if doc.requested_by and doc.requested_by == employee_user:
	leave = frappe.get_all(
		"Leave Application",
		filters={
			"employee": doc.employee,
			"status": "Approved",
			"docstatus": 1,
			"from_date": ["<=", doc.date],
			"to_date": [">=", doc.date],
		},
		fields=["leave_type"],
		limit=1,
	)
	if leave:
		errors.append(
			frappe._("You cannot create an Overtime Request on {0} as you have an approved {1} on this day.").format(
				frappe.format(doc.date, {"fieldtype": "Date"}), leave[0].leave_type
			)
		)

if frappe.utils.flt(doc.yearly_overtime_hours) > 180:
	errors.append(
		frappe._(
			"This request cannot be submitted. Adding these overtime hours will exceed the maximum allowable limit of 180 overtime hours per year."
		)
	)

if errors:
	frappe.msgprint("<br>".join(errors), title=frappe._("Overtime Request"), indicator="red")

result["overtime_request_valid"] = not errors
""",
	"Validate Compensatory Day Off": """# Public holiday overtime that brings the unredeemed balance to 9 hours or more earns a
# compensatory day off. The date must be chosen before the request reaches the Line Manager.
valid = not doc.eligible_for_compensatory_day_off or bool(doc.compensatory_day_off)

if not valid:
	frappe.msgprint(
		frappe._(
			"Compensatory Day Off date is required when Overtime Type is 'Overtime on Public Holiday' and hours are 9 or more."
		),
		title=frappe._("Overtime Request"),
		indicator="red",
	)

result["compensatory_day_off_valid"] = valid
""",
	"Validate Attendance Verification": """# Attendance can be verified only after the overtime has ended (an overnight span ends
# the next day), and only once the employee is marked Present or Absent.
errors = []

if doc.date and doc.end_time:
	overtime_end = frappe.utils.get_datetime(f"{doc.date} {doc.end_time}")
	if doc.start_time:
		overtime_start = frappe.utils.get_datetime(f"{doc.date} {doc.start_time}")
		if overtime_end <= overtime_start:
			overtime_end = frappe.utils.add_days(overtime_end, 1)
	if frappe.utils.now_datetime() < overtime_end:
		errors.append(frappe._("You cannot verify attendance until the scheduled overtime end time has passed."))

if not doc.present and not doc.absent:
	errors.append(frappe._("Please mark the employee as Present or Absent before verifying attendance."))

if errors:
	frappe.msgprint("<br>".join(errors), title=frappe._("Overtime Request"), indicator="red")

result["attendance_verification_valid"] = not errors
""",
}


def run(script_name, doc):
	"""Run a script the way the BPMN engine does and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc,
		"task_data": {},
		"result": result,
		"context_doctype": "Overtime Request",
		"context_docname": doc.name,
	}
	with patch("frappe.msgprint"):
		exec(SCRIPTS[script_name], namespace)
	return result


def make_request(**kwargs):
	doc = frappe.new_doc("Overtime Request")
	doc.name = kwargs.pop("name", "OT-PROCESSA-TEST-1")
	doc.update(kwargs)
	return doc


class TestOvertimeRequestProcessaScripts(FrappeTestCase):
	def setUp(self):
		# FrappeTestCase rolls back per class, so fixtures from an earlier test are still here.
		frappe.db.delete("Overtime Request", {"name": ["like", "OT-PROCESSA-TEST-%"]})
		frappe.db.delete("Leave Application", {"name": ["like", "LA-PROCESSA-TEST-%"]})
		self.employee = frappe.get_all("Employee", filters={"user_id": ["is", "set"]}, fields=["name", "user_id"], limit=1)[0]

	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is None:
				continue
			self.assertEqual(saved.strip(), body.strip(), name)

	def test_a_clean_request_is_valid(self):
		doc = make_request(employee=self.employee.name, date=nowdate(), start_time="18:00:00", end_time="20:00:00", yearly_overtime_hours=10)
		self.assertTrue(run("Validate Overtime Request", doc)["overtime_request_valid"])

	def test_a_duplicate_request_is_refused(self):
		existing = make_request(name="OT-PROCESSA-TEST-0", employee=self.employee.name, date=nowdate(), start_time="18:00:00", end_time="20:00:00", naming_series="OT-.MM.-.YYYY.-.####", overtime_type="Overtime after Working Hours")
		existing.db_insert()
		doc = make_request(employee=self.employee.name, date=nowdate(), start_time="18:00:00", end_time="20:00:00")
		self.assertFalse(run("Validate Overtime Request", doc)["overtime_request_valid"])

	def test_more_than_180_hours_in_the_year_is_refused(self):
		doc = make_request(employee=self.employee.name, date=nowdate(), start_time="18:00:00", end_time="20:00:00", yearly_overtime_hours=180.5)
		self.assertFalse(run("Validate Overtime Request", doc)["overtime_request_valid"])
		doc.yearly_overtime_hours = 180
		self.assertTrue(run("Validate Overtime Request", doc)["overtime_request_valid"])

	def test_approved_leave_blocks_a_self_request_only(self):
		leave = frappe.new_doc("Leave Application")
		leave.name = "LA-PROCESSA-TEST-1"
		leave.update({"employee": self.employee.name, "leave_type": "Annual Leave", "from_date": nowdate(), "to_date": nowdate(), "status": "Approved", "docstatus": 1, "posting_date": nowdate(), "company": frappe.defaults.get_global_default("company")})
		leave.db_insert()
		doc = make_request(employee=self.employee.name, date=nowdate(), start_time="18:00:00", end_time="20:00:00", requested_by=self.employee.user_id)
		self.assertFalse(run("Validate Overtime Request", doc)["overtime_request_valid"])
		doc.requested_by = "Administrator"
		self.assertTrue(run("Validate Overtime Request", doc)["overtime_request_valid"])

	def test_an_eligible_request_needs_its_compensatory_day_off(self):
		doc = make_request(eligible_for_compensatory_day_off=1)
		self.assertFalse(run("Validate Compensatory Day Off", doc)["compensatory_day_off_valid"])
		doc.compensatory_day_off = nowdate()
		self.assertTrue(run("Validate Compensatory Day Off", doc)["compensatory_day_off_valid"])

	def test_a_request_that_is_not_eligible_needs_no_day_off(self):
		doc = make_request(eligible_for_compensatory_day_off=0)
		self.assertTrue(run("Validate Compensatory Day Off", doc)["compensatory_day_off_valid"])

	def test_attendance_needs_present_or_absent(self):
		doc = make_request(date=add_days(nowdate(), -1), start_time="08:00:00", end_time="10:00:00")
		self.assertFalse(run("Validate Attendance Verification", doc)["attendance_verification_valid"])
		doc.present = 1
		self.assertTrue(run("Validate Attendance Verification", doc)["attendance_verification_valid"])

	def test_attendance_waits_for_the_overtime_to_end(self):
		doc = make_request(date=add_days(nowdate(), 1), start_time="08:00:00", end_time="10:00:00", present=1)
		self.assertFalse(run("Validate Attendance Verification", doc)["attendance_verification_valid"])

	def test_an_overnight_span_ends_the_next_day(self):
		doc = make_request(date=nowdate(), start_time="23:59:00", end_time="00:01:00", present=1)
		self.assertFalse(run("Validate Attendance Verification", doc)["attendance_verification_valid"])
