# Copyright (c) 2025, ONE FM and Contributors
# See license.txt
"""The checks the Event Staff Lifecycle process runs as a script task.

The Server Script lives on the site and moves between sites with the process export, so
its body is mirrored here. test_site_script_matches_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

SCRIPTS = {
	"Validate Event Staff": """# Checks made when the Event Staff is submitted: its dates, the event's head count for the
# designation, the employee's other event assignments, a day off in every month it spans, and
# no clash with the employee's existing Employee Schedules.
getdate = frappe.utils.getdate
get_datetime = frappe.utils.get_datetime
add_days = frappe.utils.add_days
errors = []

if getdate(doc.end_date) < getdate(doc.start_date):
	errors.append(frappe._("End Date cannot be before Start Date."))
if not doc.start_datetime or not doc.end_datetime:
	errors.append(frappe._("Start DateTime and End DateTime are mandatory."))
elif get_datetime(doc.end_datetime) <= get_datetime(doc.start_datetime):
	errors.append(frappe._("End DateTime must be after Start DateTime."))

event_start, event_state = frappe.db.get_value("Client Event", doc.client_event, ["start_date", "workflow_state"]) or (None, None)
if event_start and getdate(doc.start_date) < getdate(event_start):
	errors.append(frappe._("Start Date cannot be before the linked Client Event's Start Date."))

if doc.designation:
	required = frappe.db.get_value(
		"Client Event Staff Requirement",
		{"parent": doc.client_event, "parenttype": "Client Event", "designation": doc.designation},
		"count",
	)
	assigned = frappe.db.count("Event Staff", {"client_event": doc.client_event, "designation": doc.designation, "docstatus": ["<", 2]})
	if required and assigned > required:
		errors.append(
			frappe._("The number of assigned staff for Designation {0} exceeds the required count {1}.").format(doc.designation, required)
		)

if doc.employee and doc.start_date and doc.end_date and doc.designation:
	overlapping = frappe.get_all(
		"Event Staff",
		filters={
			"employee": doc.employee,
			"docstatus": ["<", 2],
			"name": ["!=", doc.name],
			"start_date": ["<=", doc.end_date],
			"end_date": [">=", doc.start_date],
		},
		fields=["start_date", "end_date"],
		limit=1,
	)
	if overlapping:
		errors.append(
			frappe._("{0} already assigned to {1} from {2} to {3}.").format(
				doc.employee, doc.designation, overlapping[0].start_date, overlapping[0].end_date
			)
		)

if doc.employee and doc.start_date and doc.end_date:
	month_start = frappe.utils.get_first_day(doc.start_date)
	while month_start <= getdate(doc.end_date):
		month_end = frappe.utils.get_last_day(month_start)
		days_off = frappe.db.count(
			"Employee Schedule",
			{"employee": doc.employee, "employee_availability": "Day Off", "date": ["between", [str(month_start), str(month_end)]]},
		)
		if not days_off:
			shift, employee_id = frappe.db.get_value("Employee", doc.employee, ["shift", "employee_id"])
			roster_url = "/app/roster?shift={0}&employee_id={1}".format(frappe.utils.quote(shift or ""), frappe.utils.quote(employee_id or ""))
			errors.append(
				frappe._("Employee <b>{0}</b> has 0 scheduled days off in <b>{1}</b>. Please assign a day off before creating this Client Event assignment.").format(
					doc.employee_name or doc.employee, month_start.strftime("%B %Y")
				)
				+ "<br><br><a href='{0}' target='_blank' class='btn btn-primary btn-sm'>{1}</a>".format(roster_url, frappe._("Take Action"))
			)
		month_start = frappe.utils.get_first_day(frappe.utils.add_months(month_start, 1))

# On submit the controller writes an Employee Schedule for every day of an Approved event, and
# refuses a day whose existing schedule of another roster type overlaps the event's hours.
# Checked here so the record is refused before it is submitted.
if not errors and event_state == "Approved" and doc.employee:
	start_time = get_datetime(doc.start_datetime).time()
	end_time = get_datetime(doc.end_datetime).time()
	existing = frappe.get_all(
		"Employee Schedule",
		filters={"docstatus": 0, "employee": doc.employee, "date": ["between", [doc.start_date, doc.end_date]]},
		fields=["name", "date", "start_datetime", "end_datetime", "roster_type"],
	)
	for day in range(frappe.utils.date_diff(doc.end_date, doc.start_date) + 1):
		date = getdate(add_days(doc.start_date, day))
		new_start = get_datetime("{0} {1}".format(date, start_time))
		new_end = get_datetime("{0} {1}".format(add_days(date, 1) if end_time < start_time else date, end_time))
		for row in [r for r in existing if getdate(r.date) == date]:
			if row.roster_type == doc.roster_type:
				break
			if not (row.start_datetime and row.end_datetime) or (
				get_datetime(row.start_datetime) < new_end and get_datetime(row.end_datetime) > new_start
			):
				errors.append(
					frappe._("The Event Staff schedule overlaps with an existing Employee Schedule ({0}) for {1}.").format(row.name, doc.employee)
				)
				break

for message in errors:
	frappe.msgprint(message, title=frappe._("Event Staff Not Submitted"), indicator="red")
result["event_staff_valid"] = not errors
""",
}


def run(script_name, doc):
	"""Run a script the way the BPMN engine does; return its result and the messages shown."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc,
		"task_data": {"action": "Submit"},
		"result": result,
		"context_doctype": "Event Staff",
		"context_docname": doc.name,
	}
	with patch("frappe.msgprint") as msgprint:
		exec(SCRIPTS[script_name], namespace)
	shown = " ".join(str(c.args[0]) for c in msgprint.call_args_list)
	return result, shown


CLIENT_EVENT = "CE-ES-PROCESSA-TEST"
START = getdate("2031-03-10")


def make_client_event(state="Approved", **kwargs):
	if not frappe.db.exists("Client Event", CLIENT_EVENT):
		doc = frappe.new_doc("Client Event")
		doc.update({
			"event_name": "Event Staff Processa Test",
			"start_date": START,
			"end_date": add_days(START, 5),
			"event_start_datetime": f"{START} 08:00:00",
			"event_end_datetime": f"{add_days(START, 5)} 16:00:00",
		})
		doc.name = CLIENT_EVENT
		doc.db_insert()
	frappe.db.set_value("Client Event", CLIENT_EVENT, {"workflow_state": state, **kwargs})


def make_event_staff(employee, **kwargs):
	doc = frappe.new_doc("Event Staff")
	doc.update({
		"client_event": CLIENT_EVENT,
		"employee": employee,
		"roster_type": "Basic",
		"start_date": START,
		"end_date": add_days(START, 1),
		"start_datetime": f"{START} 08:00:00",
		"end_datetime": f"{START} 16:00:00",
	})
	doc.update(kwargs)
	return doc


def schedule(employee, date, availability="Working", roster_type="Basic", start="08:00:00", end="16:00:00", **kwargs):
	doc = frappe.get_doc({
		"doctype": "Employee Schedule",
		"employee": employee,
		"date": date,
		"employee_availability": availability,
		"roster_type": roster_type,
		"start_datetime": f"{date} {start}" if availability != "Day Off" else None,
		"end_datetime": f"{date} {end}" if availability != "Day Off" else None,
		**kwargs,
	})
	doc.db_insert()
	return doc


class TestValidateEventStaff(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Event Staff", {"client_event": CLIENT_EVENT})
		make_client_event()
		self.employee = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name", limit=1)[0]
		frappe.db.delete("Employee Schedule", {"employee": self.employee, "date": ["between", [START, add_days(START, 40)]]})
		schedule(self.employee, add_days(START, 10), availability="Day Off")

	def assert_refused(self, doc, message):
		result, shown = run("Validate Event Staff", doc)
		self.assertFalse(result["event_staff_valid"])
		self.assertIn(message, shown)

	def test_site_script_matches_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is None:
				continue
			self.assertEqual(saved.strip(), body.strip(), name)

	def test_a_valid_record_passes(self):
		result, shown = run("Validate Event Staff", make_event_staff(self.employee))
		self.assertTrue(result["event_staff_valid"], shown)

	def test_end_date_before_start_date(self):
		self.assert_refused(make_event_staff(self.employee, end_date=add_days(START, -1)), "End Date cannot be before Start Date.")

	def test_datetimes_are_mandatory(self):
		self.assert_refused(make_event_staff(self.employee, end_datetime=None), "Start DateTime and End DateTime are mandatory.")

	def test_end_datetime_after_start_datetime(self):
		self.assert_refused(
			make_event_staff(self.employee, end_datetime=f"{START} 07:00:00"), "End DateTime must be after Start DateTime."
		)

	def test_start_before_the_client_event(self):
		self.assert_refused(
			make_event_staff(self.employee, start_date=add_days(START, -1)),
			"Start Date cannot be before the linked Client Event's Start Date.",
		)

	def test_head_count_for_the_designation(self):
		designation = frappe.get_all("Designation", pluck="name", limit=1)[0]
		frappe.get_doc({
			"doctype": "Client Event Staff Requirement",
			"parent": CLIENT_EVENT,
			"parenttype": "Client Event",
			"parentfield": "staffing_requirements",
			"designation": designation,
			"count": 1,
		}).db_insert()
		other_employee = frappe.get_all("Employee", filters={"status": "Active", "name": ["!=", self.employee]}, pluck="name", limit=1)[0]
		make_event_staff(other_employee, designation=designation).db_insert()
		doc = make_event_staff(self.employee, designation=designation)
		doc.db_insert()
		self.assert_refused(doc, f"The number of assigned staff for Designation {designation} exceeds the required count 1.")

	def test_another_assignment_for_the_employee_overlaps(self):
		designation = frappe.get_all("Designation", pluck="name", limit=1)[0]
		other = make_event_staff(self.employee, designation=designation)
		other.db_insert()
		self.assert_refused(make_event_staff(self.employee, designation=designation), "already assigned to")

	def test_no_day_off_in_a_month_the_assignment_spans(self):
		frappe.db.delete("Employee Schedule", {"employee": self.employee, "employee_availability": "Day Off"})
		self.assert_refused(make_event_staff(self.employee), "has 0 scheduled days off in <b>March 2031</b>")

	def test_a_clashing_schedule_of_another_roster_type(self):
		schedule(self.employee, START, roster_type="Over-Time", start="12:00:00", end="20:00:00")
		self.assert_refused(make_event_staff(self.employee), "overlaps with an existing Employee Schedule")

	def test_a_schedule_of_the_same_roster_type_is_reused_not_refused(self):
		schedule(self.employee, START, roster_type="Basic", start="12:00:00", end="20:00:00")
		result, shown = run("Validate Event Staff", make_event_staff(self.employee))
		self.assertTrue(result["event_staff_valid"], shown)

	def test_no_clash_check_before_the_event_is_approved(self):
		make_client_event(state="Pending Operations Manager")
		schedule(self.employee, START, roster_type="Over-Time", start="12:00:00", end="20:00:00")
		result, shown = run("Validate Event Staff", make_event_staff(self.employee))
		self.assertTrue(result["event_staff_valid"], shown)
