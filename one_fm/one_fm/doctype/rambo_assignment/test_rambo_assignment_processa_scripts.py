# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Rambo Assignment process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

SCRIPTS = {
	"Create Rambo Employee Schedule": """# Runs when a Rambo Assignment is submitted (the Transportation Manifest submits it). Puts the
# reliever on the Rambo shift for the day. A schedule the reliever already has for that date and
# roster type is overwritten, and what it held is kept on the Rambo Assignment so a cancel can put
# it back; otherwise a new schedule is created. A Shift Assignment made for the old shift type is
# cancelled unless the reliever has checked in on it. The Rambo Shift Assignment timer creates the
# new Shift Assignment on the day.
# A failure is logged and shown to the user, and the reliever is not notified.
import json

FIELDS = ("employee_availability", "shift", "shift_type", "operations_role", "site", "project",
	"start_datetime", "end_datetime", "is_rambo_schedule", "rambo_assignment")


def cancel_stale_shift_assignment(schedule_name, shift_type):
	stale = frappe.db.get_value("Shift Assignment", {"employee_schedule": schedule_name, "docstatus": 1}, ["name", "shift_type"], as_dict=True)
	if not stale or stale.shift_type == shift_type:
		return
	if frappe.db.exists("Employee Checkin", {"shift_assignment": stale.name}):
		frappe.msgprint(frappe._("Shift Assignment {0} has checkin logs and cannot be cancelled.").format(stale.name), indicator="orange", alert=True)
		return
	# Set directly: the person who saved the manifest may not hold Shift Assignment cancel.
	frappe.db.set_value("Shift Assignment", stale.name, "docstatus", 2)


try:
	shift_type = frappe.db.get_value("Operations Shift", doc.operations_shift, "shift_type")
	start_time, end_time = frappe.db.get_value("Shift Type", shift_type, ["start_time", "end_time"])
	end_date = frappe.utils.add_days(doc.date, 1) if start_time > end_time else doc.date
	values = {
		"employee_availability": "Working",
		"shift": doc.operations_shift,
		"shift_type": shift_type,
		"operations_role": doc.operations_role,
		"site": doc.operations_site,
		"project": doc.project,
		"start_datetime": "{0} {1}".format(doc.date, start_time),
		"end_datetime": "{0} {1}".format(end_date, end_time),
		"is_rambo_schedule": 1,
		"rambo_assignment": doc.name,
	}
	existing = frappe.db.get_value("Employee Schedule", {"employee": doc.employee, "date": doc.date, "roster_type": doc.roster_type}, "name")
	if existing:
		cancel_stale_shift_assignment(existing, shift_type)
		previous = frappe.db.get_value("Employee Schedule", existing, FIELDS, as_dict=True)
		frappe.db.set_value("Rambo Assignment", doc.name, "previous_schedule", json.dumps(previous, default=str), update_modified=False)
		frappe.db.set_value("Employee Schedule", existing, values)
		result["employee_schedule"] = existing
		frappe.msgprint(frappe._("Employee Schedule {0} has been updated for {1}.").format(existing, doc.employee_name), indicator="blue", alert=True)
	else:
		schedule = frappe.new_doc("Employee Schedule")
		schedule.update(values)
		schedule.update({"employee": doc.employee, "date": doc.date, "roster_type": doc.roster_type})
		schedule.insert()
		result["employee_schedule"] = schedule.name
		frappe.msgprint(frappe._("Employee Schedule {0} has been created for {1}.").format(schedule.name, doc.employee_name), indicator="green", alert=True)
	result["rambo_schedule_written"] = True
except Exception:
	frappe.log_error(title="Rambo Assignment schedule failed for " + doc.name, message=frappe.get_traceback())
	result["rambo_schedule_written"] = False
	frappe.msgprint(frappe._("The Employee Schedule for Rambo Assignment {0} could not be written. The error is in the Error Log.").format(doc.name), indicator="orange")
""",
	"Notify Rambo Assignment": """# Runs once the reliever's schedule is written. Emails the shift supervisor of the Rambo shift,
# then the Operation Admin in Operation Settings and the site supervisor of the reliever's own
# site, and pushes a deployment alert to the reliever's mobile app. A missing recipient is
# skipped; a failed email is logged and never stops the process.
from one_fm.processor import sendemail
from one_fm.utils import get_employee_site_supervisor_user, send_push_notification


def send(recipients):
	recipients = list({r for r in recipients if r})
	if not recipients:
		return
	message = frappe.render_template("one_fm/templates/emails/rambo_assignment_notification.html", {
		"date": doc.date,
		"original_employee": doc.original_employee or "",
		"original_employee_name": doc.original_employee_name or "",
		"employee": doc.employee or "",
		"employee_name": doc.employee_name or "",
		"operations_site": doc.operations_site or "",
		"operations_shift": doc.operations_shift or "",
		"operations_role": doc.operations_role or "",
		"project": doc.project or "",
		"start_time": doc.start_time or "",
		"end_time": doc.end_time or "",
		"transportation_manifest": doc.transportation_manifest or "",
		"manifest_url": frappe.utils.get_url_to_form("Transportation Manifest", doc.transportation_manifest),
	})
	try:
		sendemail(
			recipients=recipients,
			subject=frappe._("Rambo Reliever Assigned for Manifest {0}").format(doc.transportation_manifest),
			header=[frappe._("Rambo Assignment Alert: {0}").format(doc.name)],
			message=message,
		)
	except Exception:
		frappe.log_error(title="Rambo Assignment Email Error for " + doc.name, message=frappe.get_traceback())


send([doc.shift_supervisor_user])
send([
	frappe.db.get_single_value("Operation Settings", "operation_admin"),
	get_employee_site_supervisor_user(doc.employee) if doc.employee else None,
])
if doc.employee:
	send_push_notification(
		doc.employee,
		frappe._("Rambo Reliever Deployment"),
		frappe._("Site: You have been deployed at {0} | Shift: {1} ({2}). Report immediately.").format(
			doc.operations_site or "", doc.operations_shift or "", doc.date or ""
		),
	)
""",
	"Release Rambo Employee Schedule": """# Runs when a Rambo Assignment is cancelled (the Transportation Manifest cancels it when the row
# no longer needs a reliever or its details change). Cancels the Shift Assignment made for the
# Rambo shift, then puts back the schedule the reliever had before, or deletes the schedule the
# assignment created. The cancel itself is refused earlier, by the Rambo Assignment, once the
# reliever has checked in. Writes are direct: the person who saved the manifest may not hold
# Employee Schedule or Shift Assignment permissions. A failure is logged.
import json

try:
	schedule = frappe.db.get_value("Employee Schedule", {"employee": doc.employee, "date": doc.date, "rambo_assignment": doc.name}, "name")
	if schedule:
		shift_assignment = frappe.db.get_value("Shift Assignment", {"employee_schedule": schedule, "docstatus": 1}, "name")
		if shift_assignment:
			frappe.db.set_value("Shift Assignment", shift_assignment, "docstatus", 2)
		if doc.previous_schedule:
			frappe.db.set_value("Employee Schedule", schedule, json.loads(doc.previous_schedule))
			frappe.msgprint(frappe._("Employee Schedule {0} has been restored.").format(schedule), indicator="blue", alert=True)
		else:
			frappe.db.delete("Employee Schedule", {"name": schedule})
			frappe.msgprint(frappe._("Employee Schedule {0} has been deleted.").format(schedule), indicator="orange", alert=True)
	result["employee_schedule"] = schedule
	result["rambo_schedule_released"] = True
except Exception:
	frappe.log_error(title="Rambo Assignment release failed for " + doc.name, message=frappe.get_traceback())
	result["rambo_schedule_released"] = False
""",
	"Create Rambo Shift Assignments": """# Every 5 minutes. Gives today's Rambo schedules of active Full-time, Part-time, Intern and
# Subcontractor employees their Shift Assignment. The shared helper skips a reliever on vacation
# or leave, cancels a Shift Assignment left from the old shift or turns the day into Over-Time,
# and creates and submits the Shift Assignment.
from one_fm.api.tasks import process_rambo_shift_assignment

date = frappe.utils.today()
schedules = frappe.get_all("Employee Schedule", filters={
	"date": date,
	"is_rambo_schedule": 1,
	"is_replaced": 0,
	"roster_type": ["in", ["Basic", "Over-Time"]],
	"employee_availability": ["in", ["Working", "On-the-job Training", "Client Event"]],
}, fields=["*"])
if schedules:
	eligible = set(frappe.get_all("Employee", filters={
		"name": ["in", list({s.employee for s in schedules})],
		"status": "Active",
		"employment_type": ["in", ["Full-time", "Part-time", "Intern", "Subcontractor"]],
	}, pluck="name"))
	schedules = [s for s in schedules if s.employee in eligible]
if schedules:
	process_rambo_shift_assignment(schedules=schedules, date=date)
result["rambo_schedules"] = len(schedules)
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
		"context_doctype": "Rambo Assignment",
		"context_docname": doc.name if doc else None,
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


from frappe.query_builder import DocType
from frappe.utils import add_days, getdate, today

DATE = add_days(today(), 900)
SCHEDULE, NOTIFY, RELEASE, SHIFTS = "Create Rambo Employee Schedule", "Notify Rambo Assignment", "Release Rambo Employee Schedule", "Create Rambo Shift Assignments"


def _shift(overnight):
	"""An active Operations Shift whose Shift Type does (or does not) cross midnight."""
	OperationsShift = DocType("Operations Shift")
	ShiftType = DocType("Shift Type")
	rows = (
		frappe.qb.from_(OperationsShift)
		.join(ShiftType)
		.on(OperationsShift.shift_type == ShiftType.name)
		.select(OperationsShift.name, ShiftType.start_time, ShiftType.end_time)
		.where(OperationsShift.status == "Active")
	).run(as_dict=True)
	for row in rows:
		if (row.start_time > row.end_time) == overnight:
			return row.name
	raise frappe.DoesNotExistError("No suitable Operations Shift on this site")


def _reliever():
	return frappe.db.get_value("Employee", {"status": "Active", "relieving_date": ["is", "not set"],
		"employment_type": ["in", ["Full-time", "Part-time", "Intern", "Subcontractor"]]}, "name", order_by="creation asc")


@patch("one_fm.processor.sendemail")
@patch("one_fm.utils.send_push_notification")
class TestRamboScripts(FrappeTestCase):
	def setUp(self):
		self.employee = _reliever()
		frappe.db.delete("Employee Schedule", {"employee": self.employee, "date": DATE})

	def _rambo(self, overnight=False, **kw):
		shift = _shift(overnight)
		site, project = frappe.db.get_value("Operations Shift", shift, ["site", "project"])
		values = {"doctype": "Rambo Assignment", "date": DATE, "employee": self.employee, "operations_shift": shift,
			"operations_site": site, "project": project, "roster_type": "Basic"}
		values.update(kw)
		doc = frappe.get_doc(values)
		doc.insert(ignore_permissions=True)
		return doc

	def _schedule(self, rambo_name):
		return frappe.db.get_value("Employee Schedule", {"employee": self.employee, "date": DATE, "rambo_assignment": rambo_name},
			["name", "shift", "site", "is_rambo_schedule", "end_datetime", "rambo_assignment"], as_dict=True)

	def test_schedule_is_created_for_the_reliever(self, *_):
		rambo = self._rambo()
		result = run(SCHEDULE, rambo)
		self.assertTrue(result["rambo_schedule_written"])
		schedule = self._schedule(rambo.name)
		self.assertEqual(schedule.shift, rambo.operations_shift)
		self.assertEqual(schedule.is_rambo_schedule, 1)

	def test_an_overnight_shift_ends_the_next_day(self, *_):
		rambo = self._rambo(overnight=True)
		run(SCHEDULE, rambo)
		self.assertEqual(getdate(self._schedule(rambo.name).end_datetime), getdate(add_days(DATE, 1)))

	def test_a_bad_shift_is_logged_not_raised(self, *_):
		rambo = self._rambo()
		rambo.operations_shift = "No Such Shift"
		with patch("frappe.log_error") as log_error:
			result = run(SCHEDULE, rambo)
		self.assertFalse(result["rambo_schedule_written"])
		log_error.assert_called_once()

	def test_release_deletes_a_schedule_it_created(self, *_):
		rambo = self._rambo()
		run(SCHEDULE, rambo)
		rambo.reload()
		result = run(RELEASE, rambo)
		self.assertTrue(result["rambo_schedule_released"])
		self.assertIsNone(self._schedule(rambo.name))

	def test_release_restores_a_schedule_the_reliever_already_had(self, *_):
		own_shift = _shift(overnight=True)
		site, project, shift_type = frappe.db.get_value("Operations Shift", own_shift, ["site", "project", "shift_type"])
		own = frappe.get_doc({"doctype": "Employee Schedule", "employee": self.employee, "date": DATE, "employee_availability": "Working",
			"shift": own_shift, "shift_type": shift_type, "site": site, "project": project, "roster_type": "Basic"})
		own.flags.ignore_permissions = True
		own.insert()
		rambo = self._rambo()
		run(SCHEDULE, rambo)
		self.assertEqual(self._schedule(rambo.name).name, own.name)
		rambo.reload()
		self.assertTrue(rambo.previous_schedule)
		run(RELEASE, rambo)
		restored = frappe.db.get_value("Employee Schedule", own.name, ["shift", "site", "is_rambo_schedule", "rambo_assignment"], as_dict=True)
		self.assertEqual(restored.shift, own_shift)
		self.assertEqual(restored.site, site)
		self.assertFalse(restored.is_rambo_schedule)
		self.assertIsNone(restored.rambo_assignment)

	def test_notify_emails_supervisors_and_pushes_the_reliever(self, push, sendemail):
		rambo = self._rambo(shift_supervisor_user="Administrator")
		with patch("one_fm.utils.get_employee_site_supervisor_user", return_value="site@example.com"):
			run(NOTIFY, rambo)
		recipients = [c.kwargs["recipients"] for c in sendemail.call_args_list]
		self.assertEqual(recipients[0], ["Administrator"])
		self.assertIn("site@example.com", recipients[1])
		push.assert_called_once()

	def test_notify_skips_a_missing_supervisor(self, push, sendemail):
		rambo = self._rambo(shift_supervisor_user=None)
		with patch("one_fm.utils.get_employee_site_supervisor_user", return_value=None), \
			patch.object(frappe.db, "get_single_value", return_value=None):
			run(NOTIFY, rambo)
		sendemail.assert_not_called()
		push.assert_called_once()

	def test_todays_rambo_schedules_get_shift_assignments(self, *_):
		shift = _shift(overnight=False)
		frappe.db.delete("Employee Schedule", {"employee": self.employee, "date": today()})
		frappe.get_doc({"doctype": "Employee Schedule", "name": frappe.generate_hash(), "employee": self.employee, "date": today(),
			"employee_availability": "Working", "shift": shift, "roster_type": "Basic", "is_rambo_schedule": 1, "is_replaced": 0}).db_insert()
		with patch("one_fm.api.tasks.process_rambo_shift_assignment") as process:
			result = run(SHIFTS, None)
		self.assertGreaterEqual(result["rambo_schedules"], 1)
		self.assertIn(self.employee, [s.employee for s in process.call_args.kwargs["schedules"]])

	def test_a_replaced_schedule_is_left_out(self, *_):
		frappe.db.delete("Employee Schedule", {"date": today(), "is_rambo_schedule": 1})
		frappe.get_doc({"doctype": "Employee Schedule", "name": frappe.generate_hash(), "employee": self.employee, "date": today(),
			"employee_availability": "Working", "roster_type": "Basic", "is_rambo_schedule": 1, "is_replaced": 1}).db_insert()
		with patch("one_fm.api.tasks.process_rambo_shift_assignment") as process:
			result = run(SHIFTS, None)
		self.assertEqual(result["rambo_schedules"], 0)
		process.assert_not_called()
