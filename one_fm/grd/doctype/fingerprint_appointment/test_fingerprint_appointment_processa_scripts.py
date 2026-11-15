# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Fingerprint Appointment Lifecycle process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime, today

SCRIPTS = {
	"Validate Fingerprint Appointment Step": """# Checks the action taken on the Fingerprint Appointment task before the process moves it on.
# The two pickup actions also record where the employee is picked up from.
# Sets result["step_valid"]; on False the process reopens the same task.
action = task_data.get("action")
state = doc.workflow_state
errors = []

PICKUP_BY_ACTION = {
	"Request Pickup from Accommodation": "Accommodation",
	"Request Pickup from Operations Site": "Operations Site",
}

if action in PICKUP_BY_ACTION:
	doc.pickup_location = PICKUP_BY_ACTION[action]
	frappe.db.set_value("Fingerprint Appointment", doc.name, "pickup_location", doc.pickup_location)

if state == "Pending Supervisor" and action in PICKUP_BY_ACTION and doc.required_transportation == "Yes":
	if not doc.roster_action:
		errors.append(frappe._("Roster Action is required before proceeding"))
	if doc.pickup_location == "Accommodation" and not doc.accommodation:
		errors.append(frappe._("Accommodation is required when Pickup Location is Accommodation"))
	if doc.pickup_location == "Operations Site" and not doc.operations_site:
		errors.append(frappe._("Operations Site is required when Pickup Location is Operations Site"))

elif state == "Pending Supervisor" and action == "Reject":
	if not doc.reason_for_rejection:
		errors.append(frappe._("Select the Reason for Rejection first."))

elif state == "Set Pick-up as Accommodation (Supervisor)" and action == "Request Pickup from Accommodation":
	if doc.required_transportation == "Yes" and not doc.accommodation:
		errors.append(frappe._("Accommodation details must be provided to proceed"))

elif state == "Pending PRO" and doc.roster_action == "Yes":
	if not doc.date_and_time_confirmation:
		errors.append(frappe._("Date and Time Confirmation is required"))
	elif frappe.utils.getdate(doc.date_and_time_confirmation) > frappe.utils.getdate():
		errors.append(frappe._("You cannot confirm fingerprint capturing before the appointment date."))

result["step_valid"] = not errors
for e in errors:
	frappe.msgprint(e, title=frappe._("Cannot Continue"), indicator="red")
""",
	"Book Fingerprint Appointment Day": """# Runs when the appointment reaches the Transportation Supervisor or the PRO. When the roster
# is affected, the employee's schedule for the appointment day becomes Fingerprint
# Appointment and their attendance for that day is held On Hold.
# Written directly: the GR Operator who raised the appointment has no access to Employee
# Schedule or Attendance.
if doc.employee and doc.date_and_time_confirmation and doc.roster_action != "No":
	day = frappe.utils.getdate(doc.date_and_time_confirmation)
	now = frappe.utils.now_datetime()
	audit = {"owner": frappe.session.user, "modified_by": frappe.session.user, "creation": now, "modified": now}
	schedule_values = {
		"employee_availability": "Fingerprint Appointment", "operations_role": "", "shift": "", "site": "",
		"shift_type": "", "project": "", "reference_doctype": doc.doctype, "reference_docname": doc.name,
	}
	schedule = frappe.db.get_value("Employee Schedule", {"employee": doc.employee, "date": day}, "name")
	if schedule:
		frappe.db.set_value("Employee Schedule", schedule, schedule_values)
	else:
		new_schedule = frappe.get_doc({"doctype": "Employee Schedule", "employee": doc.employee, "date": day, "roster_type": "Basic", **schedule_values, **audit})
		new_schedule.set_new_name()
		new_schedule.db_insert()
		schedule = new_schedule.name
	result["employee_schedule"] = schedule

	attendance = frappe.db.get_value("Attendance", {"employee": doc.employee, "attendance_date": day}, "name")
	if attendance:
		frappe.db.set_value("Attendance", attendance, "status", "On Hold")
	else:
		employee = frappe.db.get_value("Employee", doc.employee, ["employee_name", "company", "department"], as_dict=True)
		new_attendance = frappe.get_doc({
			"doctype": "Attendance", "employee": doc.employee, "employee_name": employee.employee_name,
			"company": employee.company, "department": employee.department, "attendance_date": day, "status": "On Hold",
			"reference_doctype": doc.doctype, "reference_docname": doc.name, "docstatus": 1, **audit,
		})
		new_attendance.set_new_name()
		new_attendance.db_insert()
		attendance = new_attendance.name
	result["attendance"] = attendance
""",
	"Notify Employee of Fingerprint Appointment": """# Runs when the appointment reaches the PRO. Tells the employee when and where they are
# picked up, in the desk and on the mobile app.
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from one_fm.utils import send_push_notification

employee = frappe.db.get_value("Employee", doc.employee, ["user_id", "employee_id"], as_dict=True)
if doc.pickup_location and doc.date_and_time_confirmation and employee and employee.user_id:
	if doc.pickup_location == "Accommodation":
		place = doc.accommodation_name or doc.accommodation
	else:
		place = frappe.db.get_value("Operations Site", doc.operations_site, "site_name") or doc.operations_site
	when = frappe.utils.format_datetime(doc.date_and_time_confirmation, "dd-MM-yyyy hh:mm a")
	subject = frappe._("Fingerprint Appointment Scheduled")
	message = frappe._(
		"<p>Good day,</p><p>Please be informed that you have been scheduled for a fingerprint appointment on "
		"<strong>{0}</strong> and will be picked up at the <strong>{1}: {2}</strong>.</p>"
		"<p>Please ensure to take your original passport with you.</p>"
	).format(when, doc.pickup_location, place)
	enqueue_create_notification(employee.user_id, {
		"subject": subject, "email_content": message, "document_type": doc.doctype,
		"document_name": doc.name, "from_user": doc.modified_by, "type": "Alert",
	})
	send_push_notification(employee.employee_id, subject, message)
""",
	"Notify Supervisor of Site Pickup Rejection": """# Runs when the GR Operator rejects the operations site pickup. Tells the Employee
# Supervisor they can change the pickup to the accommodation.
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

if doc.employee_supervisor:
	when = frappe.utils.format_datetime(doc.date_and_time_confirmation, "dd-MM-yyyy hh:mm a") if doc.date_and_time_confirmation else frappe._("Not specified")
	enqueue_create_notification(doc.employee_supervisor, {
		"subject": frappe._("Site Pickup Request Rejected - Fingerprint Appointment"),
		"email_content": frappe._(
			"<p>This is to inform you that your request for site pickup for a fingerprint appointment has been rejected. "
			"You can change the pickup location to Accommodation.</p><br><p><strong>Employee Name:</strong> {0}</p>"
			"<p><strong>Date and Time Confirmation:</strong> {1}</p>"
		).format(doc.full_name, when),
		"document_type": doc.doctype, "document_name": doc.name, "from_user": doc.modified_by, "type": "Alert",
	})
""",
	"Record Fingerprint Appointment Outcome": """# Runs once the appointment is Completed, Reschedule Requested or Rejected. Stamps when it
# closed, settles the attendance held On Hold for the appointment day, and tells the GR
# Operator who raised it when it is rejected.
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

frappe.db.set_value("Fingerprint Appointment", doc.name, "completed_on", frappe.utils.now_datetime())

if doc.workflow_state in ("Completed", "Reschedule Requested") and doc.roster_action == "Yes" and doc.date_and_time_confirmation:
	status = "Fingerprint Appointment" if doc.workflow_state == "Completed" else "Absent"
	for name in frappe.get_all("Attendance", filters={
		"employee": doc.employee, "attendance_date": frappe.utils.getdate(doc.date_and_time_confirmation), "status": "On Hold",
	}, pluck="name"):
		frappe.db.set_value("Attendance", name, "status", status)

if doc.workflow_state == "Rejected" and doc.owner and doc.owner != "Guest":
	enqueue_create_notification(doc.owner, {
		"subject": frappe._("Fingerprint Appointment Rejected - {0}").format(doc.full_name),
		"email_content": frappe._(
			"<p>This is to inform you that a fingerprint appointment has been rejected.</p><br>"
			"<p><strong>Employee Name:</strong> {0}</p><p><strong>Date and Time Confirmation:</strong> {1}</p>"
			"<p><strong>Reason for Rejection:</strong> {2}</p>"
		).format(doc.full_name, doc.date_and_time_confirmation or frappe._("Not specified"), doc.reason_for_rejection or frappe._("Not provided")),
		"document_type": doc.doctype, "document_name": doc.name, "from_user": doc.modified_by, "type": "Alert",
	})
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
		"context_doctype": "Fingerprint Appointment",
		"context_docname": doc.name,
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


def appointment(**kw):
	doc = frappe.new_doc("Fingerprint Appointment")
	doc.name = kw.pop("name", "FP-PROCESSA-TEST-1")
	doc.update(kw)
	return doc


def an_employee():
	return frappe.get_all("Employee", filters={"status": "Active", "user_id": ["is", "set"]}, pluck="name", limit=1, order_by="creation desc")[0]


class TestValidateFingerprintAppointmentStep(FrappeTestCase):
	def valid(self, doc, action):
		return run("Validate Fingerprint Appointment Step", doc, action=action)["step_valid"]

	def test_the_action_names_the_pickup_location(self):
		doc = appointment(workflow_state="Pending Supervisor", required_transportation="No")
		self.assertTrue(self.valid(doc, "Request Pickup from Operations Site"))
		self.assertEqual(doc.pickup_location, "Operations Site")

	def test_transport_needs_the_roster_action_and_the_place(self):
		doc = appointment(workflow_state="Pending Supervisor", required_transportation="Yes")
		self.assertFalse(self.valid(doc, "Request Pickup from Accommodation"))
		doc.roster_action = "No"
		self.assertFalse(self.valid(doc, "Request Pickup from Accommodation"))
		doc.accommodation = frappe.db.get_value("Accommodation", {}, "name")
		self.assertTrue(self.valid(doc, "Request Pickup from Accommodation"))
		self.assertFalse(self.valid(doc, "Request Pickup from Operations Site"))

	def test_a_supervisor_rejection_needs_its_reason(self):
		doc = appointment(workflow_state="Pending Supervisor")
		self.assertFalse(self.valid(doc, "Reject"))
		doc.reason_for_rejection = "Staff Shortage"
		self.assertTrue(self.valid(doc, "Reject"))

	def test_the_pro_cannot_confirm_before_the_appointment(self):
		doc = appointment(workflow_state="Pending PRO", roster_action="Yes")
		self.assertFalse(self.valid(doc, "Employee Attended"))
		doc.date_and_time_confirmation = add_days(now_datetime(), 2)
		self.assertFalse(self.valid(doc, "Employee Attended"))
		doc.date_and_time_confirmation = now_datetime()
		self.assertTrue(self.valid(doc, "Employee Attended"))
		doc.roster_action = "No"
		doc.date_and_time_confirmation = None
		self.assertTrue(self.valid(doc, "Employee Did Not Attend"))


class TestFingerprintAppointmentDay(FrappeTestCase):
	def setUp(self):
		self.employee = an_employee()
		self.day = add_days(today(), 30)
		frappe.db.delete("Employee Schedule", {"employee": self.employee, "date": self.day})
		frappe.db.delete("Attendance", {"employee": self.employee, "attendance_date": self.day})

	def test_books_the_schedule_and_holds_the_attendance(self):
		doc = appointment(employee=self.employee, roster_action="Yes", date_and_time_confirmation=f"{self.day} 09:00:00")
		run("Book Fingerprint Appointment Day", doc)
		self.assertEqual(frappe.db.get_value("Employee Schedule", {"employee": self.employee, "date": self.day}, "employee_availability"), "Fingerprint Appointment")
		self.assertEqual(frappe.db.get_value("Attendance", {"employee": self.employee, "attendance_date": self.day}, "status"), "On Hold")

		doc.workflow_state = "Completed"
		run("Record Fingerprint Appointment Outcome", doc)
		self.assertEqual(frappe.db.get_value("Attendance", {"employee": self.employee, "attendance_date": self.day}, "status"), "Fingerprint Appointment")

	def test_no_roster_action_books_nothing(self):
		run("Book Fingerprint Appointment Day", appointment(employee=self.employee, roster_action="No", date_and_time_confirmation=f"{self.day} 09:00:00"))
		self.assertFalse(frappe.db.exists("Employee Schedule", {"employee": self.employee, "date": self.day}))


class TestFingerprintAppointmentNotices(FrappeTestCase):
	def test_the_employee_hears_when_and_where(self):
		doc = appointment(employee=an_employee(), pickup_location="Accommodation", accommodation="ACC", date_and_time_confirmation=now_datetime())
		with patch("frappe.desk.doctype.notification_log.notification_log.enqueue_create_notification") as notify, patch("one_fm.utils.send_push_notification") as push:
			run("Notify Employee of Fingerprint Appointment", doc)
		self.assertTrue(notify.called)
		self.assertTrue(push.called)

	def test_the_creator_hears_of_a_rejection(self):
		doc = appointment(workflow_state="Rejected", owner="Administrator", full_name="X")
		with patch("frappe.desk.doctype.notification_log.notification_log.enqueue_create_notification") as notify:
			run("Record Fingerprint Appointment Outcome", doc)
		self.assertEqual(notify.call_args[0][0], "Administrator")

	def test_the_supervisor_hears_of_a_site_pickup_rejection(self):
		doc = appointment(employee_supervisor="Administrator", full_name="X")
		with patch("frappe.desk.doctype.notification_log.notification_log.enqueue_create_notification") as notify:
			run("Notify Supervisor of Site Pickup Rejection", doc)
		self.assertEqual(notify.call_args[0][0], "Administrator")
