# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Medical Appointment processes run as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime, today


SCRIPTS = {
	"Set Medical Appointment Supervisor": """# Runs when the appointment is created. Fills the Employee Supervisor, who takes the
# supervisor step, from the employee's site supervisor or else their leave approver.
from one_fm.utils import get_approver_user, get_employee_site_supervisor_user

if doc.employee and not doc.employee_supervisor:
	supervisor = get_employee_site_supervisor_user(doc.employee) or get_approver_user(doc.employee)
	if supervisor:
		doc.employee_supervisor = supervisor
		frappe.db.set_value("Medical Appointment", doc.name, "employee_supervisor", supervisor)
""",
	"Validate Medical Appointment Step": """# Checks the action taken on the Medical Appointment task before the process moves it on.
# Sets result["step_valid"]; on False the process reopens the same task.
action = task_data.get("action")
state = doc.workflow_state
errors = []

missing = [doc.meta.get_label(f) for f in ("required_transportation", "pro_user") if not doc.get(f)]
if missing:
	errors.append(frappe._("Set {0} first.").format(", ".join(frappe._(m) for m in missing)))

if action == "Reject" and state in ("Pending Supervisor", "Set Pick-up as Accommodation (Supervisor)") and not doc.reason_for_rejection:
	errors.append(frappe._("Select the Reason for Rejection first."))

if state == "Pending PRO":
	if not doc.date_and_time_confirmation:
		errors.append(frappe._("Date and Time Confirmation is required."))
	elif frappe.utils.getdate(doc.date_and_time_confirmation) > frappe.utils.getdate():
		errors.append(frappe._("You are not allowed to action medical appointment before the appointment date."))
	if action == "Employee Attended" and not doc.payment_invoice:
		errors.append(frappe._("Payment invoice attachment is required to proceed."))

result["step_valid"] = not errors
for e in errors:
	frappe.msgprint(e, title=frappe._("Cannot Continue"), indicator="red")
""",
	"Notify Supervisor of Medical Appointment Site Pickup Rejection": """# Runs when the GR Operator rejects the operations site pickup. Tells the Employee
# Supervisor they can change the pickup location to the accommodation.
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

if doc.employee_supervisor:
	message = frappe._(
		"This is to inform you that your request for site pickup for a medical appointment has been rejected. "
		"You can change the pickup location to Accommodation.<br/><br/>{0} {1}"
	).format(doc.full_name, doc.date_and_time_confirmation or "")
	enqueue_create_notification(doc.employee_supervisor, {
		"subject": message, "email_content": message, "document_type": doc.doctype,
		"document_name": doc.name, "from_user": doc.modified_by, "type": "Alert",
	})
""",
	"Book Medical Appointment Day": """# Runs when the appointment reaches the PRO. When the roster is blocked, the employee's
# schedule for the appointment day becomes Medical Appointment and their attendance for
# that day is held On Hold.
# Written directly: the user who raised the appointment has no access to Employee
# Schedule or Attendance.
if doc.block_roster == "Yes" and doc.employee and doc.date_and_time_confirmation:
	day = frappe.utils.getdate(doc.date_and_time_confirmation)
	now = frappe.utils.now_datetime()
	audit = {"owner": frappe.session.user, "modified_by": frappe.session.user, "creation": now, "modified": now}
	schedule_values = {
		"employee_availability": "Medical Appointment", "operations_role": "", "shift": "", "site": "",
		"shift_type": "", "project": "", "reference_doctype": doc.doctype, "reference_docname": doc.name,
	}
	schedule = frappe.db.get_value("Employee Schedule", {"employee": doc.employee, "date": day, "roster_type": "Basic"}, "name")
	if schedule:
		frappe.db.set_value("Employee Schedule", schedule, schedule_values)
	else:
		new_schedule = frappe.get_doc({"doctype": "Employee Schedule", "employee": doc.employee, "date": day, "roster_type": "Basic", **schedule_values, **audit})
		new_schedule.set_new_name()
		new_schedule.db_insert()
		schedule = new_schedule.name
	result["employee_schedule"] = schedule

	comment = frappe._("Created via Medical Appointment: {0}").format(doc.name)
	attendance = frappe.db.get_value("Attendance", {"employee": doc.employee, "attendance_date": day, "docstatus": ["<", 2]}, "name")
	if attendance:
		frappe.db.set_value("Attendance", attendance, {"status": "On Hold", "comment": comment})
	else:
		employee = frappe.db.get_value("Employee", doc.employee, ["employee_name", "company", "department"], as_dict=True)
		new_attendance = frappe.get_doc({
			"doctype": "Attendance", "employee": doc.employee, "employee_name": employee.employee_name,
			"company": employee.company, "department": employee.department, "attendance_date": day, "status": "On Hold",
			"comment": comment, "reference_doctype": doc.doctype, "reference_docname": doc.name, "docstatus": 1, **audit,
		})
		new_attendance.set_new_name()
		new_attendance.db_insert()
		attendance = new_attendance.name
	result["attendance"] = attendance
""",
	"Record Medical Appointment Outcome": """# Runs once the appointment is Completed, Reschedule Requested or Rejected. Settles the
# attendance held for the appointment day and tells the GR Operator of a rejection.
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

if doc.workflow_state in ("Completed", "Reschedule Requested") and doc.block_roster == "Yes" and doc.date_and_time_confirmation:
	values = {"status": "Medical Appointment", "working_hours": 8} if doc.workflow_state == "Completed" else {"status": "Absent"}
	values["comment"] = frappe._("Updated via Medical Appointment: {0}").format(doc.name)
	for name in frappe.get_all("Attendance", filters={
		"employee": doc.employee, "attendance_date": frappe.utils.getdate(doc.date_and_time_confirmation),
		"status": ["in", ["On Hold", "Absent"]], "docstatus": ["<", 2],
	}, pluck="name"):
		frappe.db.set_value("Attendance", name, values)

if doc.workflow_state == "Rejected" and doc.government_relations_operator and doc.reason_for_rejection:
	message = frappe._("This is to inform you that a medical appointment has been rejected<br/>")
	message += frappe._("Employee Name: {0}<br/>").format(doc.full_name)
	message += frappe._("Date and Time Confirmation: {0}<br/>").format(doc.date_and_time_confirmation or "")
	message += frappe._("Reason for Rejection: {0}").format(doc.reason_for_rejection)
	enqueue_create_notification(doc.government_relations_operator, {
		"subject": message, "email_content": message, "document_type": doc.doctype,
		"document_name": doc.name, "from_user": doc.modified_by, "type": "Alert",
	})
""",
	"Remind Supervisors of Pending Medical Appointments": """# Daily at 8 AM. Reminds each Employee Supervisor of the appointments still waiting on them.
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

for appointment in frappe.get_all(
	"Medical Appointment",
	filters={"workflow_state": "Pending Supervisor", "employee_supervisor": ["is", "set"]},
	fields=["name", "full_name", "employee", "employee_supervisor"],
):
	enqueue_create_notification(appointment.employee_supervisor, {
		"subject": frappe._("You need to take action on Medical Appointment for {0}").format(appointment.full_name or appointment.employee),
		"document_type": "Medical Appointment", "document_name": appointment.name, "type": "Alert",
	})
""",
	"Remind Transportation Supervisors of Medical Appointment Pickups": """# Daily at 9 AM. Tells each Transportation Supervisor who to pick up for tomorrow's appointments.
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

tomorrow = frappe.utils.add_days(frappe.utils.nowdate(), 1)
by_supervisor = {}
for appointment in frappe.get_all(
	"Medical Appointment",
	filters={
		"workflow_state": "Pending Transportation Supervisor",
		"date_and_time_confirmation": ["between", (f"{tomorrow} 00:00:00", f"{tomorrow} 23:59:59")],
		"transportation_supervisor_user": ["is", "set"],
	},
	fields=["full_name", "date_and_time_confirmation", "transportation_supervisor_user", "pickup_location", "operations_site", "accommodation_name"],
):
	by_supervisor.setdefault(appointment.transportation_supervisor_user, []).append(appointment)

for supervisor, appointments in by_supervisor.items():
	lines = []
	for a in appointments:
		place = a.operations_site if a.pickup_location == "Operations Site" else a.accommodation_name if a.pickup_location == "Accommodation" else ""
		if place:
			lines.append(f"<li>{a.full_name}: {frappe.utils.format_datetime(a.date_and_time_confirmation, 'hh:mm a')} from {place}</li>")
	if not lines:
		continue
	enqueue_create_notification(supervisor, {
		"subject": f"Reminder: {len(appointments)} medical appointments for tomorrow.",
		"email_content": f"<p>You have {len(appointments)} employees scheduled to attend medical appointments on "
			f"{frappe.utils.format_datetime(tomorrow, 'd MMMM YYYY')}.</p><p>Pick-up locations:</p><ol>{''.join(lines)}</ol>",
		"document_type": "Medical Appointment", "type": "Alert",
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
		"context_doctype": "Medical Appointment",
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


def appointment(**kw):
	doc = frappe.new_doc("Medical Appointment")
	doc.name = kw.pop("name", "MAP-PROCESSA-TEST-1")
	doc.update({"required_transportation": "No", "pro_user": "Administrator", **kw})
	return doc


def an_employee():
	return frappe.get_all("Employee", filters={"status": "Active"}, pluck="name", limit=1, order_by="creation desc")[0]


class TestValidateMedicalAppointmentStep(FrappeTestCase):
	def valid(self, doc, action):
		return run("Validate Medical Appointment Step", doc, action=action)["step_valid"]

	def test_leaving_draft_needs_transportation_and_the_pro(self):
		self.assertFalse(self.valid(appointment(workflow_state="Draft", pro_user=None), "Submit to Supervisor"))
		self.assertFalse(self.valid(appointment(workflow_state="Draft", required_transportation=None), "Submit to Supervisor"))
		self.assertTrue(self.valid(appointment(workflow_state="Draft"), "Submit to Supervisor"))

	def test_a_supervisor_rejection_needs_its_reason(self):
		for state in ("Pending Supervisor", "Set Pick-up as Accommodation (Supervisor)"):
			doc = appointment(workflow_state=state)
			self.assertFalse(self.valid(doc, "Reject"))
			doc.reason_for_rejection = "Staff Shortage"
			self.assertTrue(self.valid(doc, "Reject"))

	def test_the_pro_cannot_close_before_the_appointment(self):
		doc = appointment(workflow_state="Pending PRO")
		self.assertFalse(self.valid(doc, "Employee Did Not Attend"))
		doc.date_and_time_confirmation = add_days(now_datetime(), 2)
		self.assertFalse(self.valid(doc, "Employee Did Not Attend"))
		doc.date_and_time_confirmation = now_datetime()
		self.assertTrue(self.valid(doc, "Employee Did Not Attend"))

	def test_attended_needs_the_payment_invoice(self):
		doc = appointment(workflow_state="Pending PRO", date_and_time_confirmation=now_datetime())
		self.assertFalse(self.valid(doc, "Employee Attended"))
		doc.payment_invoice = "/files/invoice.pdf"
		self.assertTrue(self.valid(doc, "Employee Attended"))


class TestMedicalAppointmentDay(FrappeTestCase):
	def setUp(self):
		self.employee = an_employee()
		self.day = add_days(today(), 30)
		frappe.db.delete("Employee Schedule", {"employee": self.employee, "date": self.day})
		frappe.db.delete("Attendance", {"employee": self.employee, "attendance_date": self.day})

	def attendance(self):
		return frappe.db.get_value("Attendance", {"employee": self.employee, "attendance_date": self.day}, ["status", "working_hours"], as_dict=True)

	def test_a_blocked_roster_books_the_day_and_completes_it(self):
		doc = appointment(employee=self.employee, block_roster="Yes", date_and_time_confirmation=f"{self.day} 09:00:00")
		run("Book Medical Appointment Day", doc)
		self.assertEqual(frappe.db.get_value("Employee Schedule", {"employee": self.employee, "date": self.day}, "employee_availability"), "Medical Appointment")
		self.assertEqual(self.attendance().status, "On Hold")

		doc.workflow_state = "Completed"
		run("Record Medical Appointment Outcome", doc)
		self.assertEqual(self.attendance().status, "Medical Appointment")
		self.assertEqual(self.attendance().working_hours, 8)

	def test_a_missed_appointment_marks_the_day_absent(self):
		doc = appointment(employee=self.employee, block_roster="Yes", date_and_time_confirmation=f"{self.day} 09:00:00")
		run("Book Medical Appointment Day", doc)
		doc.workflow_state = "Reschedule Requested"
		run("Record Medical Appointment Outcome", doc)
		self.assertEqual(self.attendance().status, "Absent")

	def test_an_open_roster_books_nothing(self):
		run("Book Medical Appointment Day", appointment(employee=self.employee, block_roster="No", date_and_time_confirmation=f"{self.day} 09:00:00"))
		self.assertFalse(frappe.db.exists("Employee Schedule", {"employee": self.employee, "date": self.day}))
		self.assertIsNone(self.attendance())


class TestMedicalAppointmentNotices(FrappeTestCase):
	NOTIFY = "frappe.desk.doctype.notification_log.notification_log.enqueue_create_notification"

	def test_the_gr_operator_hears_of_a_rejection(self):
		doc = appointment(workflow_state="Rejected", government_relations_operator="Administrator", reason_for_rejection="Staff Shortage", full_name="X")
		with patch(self.NOTIFY) as notify:
			run("Record Medical Appointment Outcome", doc)
		self.assertEqual(notify.call_args[0][0], "Administrator")

	def test_the_supervisor_hears_of_a_site_pickup_rejection(self):
		with patch(self.NOTIFY) as notify:
			run("Notify Supervisor of Medical Appointment Site Pickup Rejection", appointment(employee_supervisor="Administrator", full_name="X"))
		self.assertEqual(notify.call_args[0][0], "Administrator")
