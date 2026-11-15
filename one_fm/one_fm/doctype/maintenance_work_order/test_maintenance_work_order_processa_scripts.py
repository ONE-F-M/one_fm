# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Maintenance Work Order processes run as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one. The other Maintenance Work Order tests read the rules from here through
rules(), and install_scripts() puts these bodies on the site for the hooks to run.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

# The Processa engine commits when an instance starts or fails. A test module starts this in
# setUpModule, so its records still roll back.
NO_COMMIT = patch("frappe.db.commit")

SCRIPTS = {
	"Calculate Work Order": """# The derived fields of a Maintenance Work Order: the asset profile, parts, team and checklist,
# the SLA contract and its targets, the paused time, the live SLA countdown and the planned deadline.
# A Work Order's insert runs initialise and every save runs calculate. The Check In and Close
# steps of the Work Order map run evaluate_sla_response and evaluate_sla_resolution.
# The Maintenance Work Order SLA Countdown timer runs it every 5 minutes to advance the countdown
# of every open Preventive Work Order.
from datetime import datetime, time, timedelta

# The Work Order status that pauses the SLA clock while parts are awaited.
ON_HOLD_STATUS = "On Hold - Parts Required"
# Verdicts the live countdown never overrides.
FINAL_STATUSES = ("Pass", "Fail")


# A Time field value (timedelta, time or string) as a time.
def to_time(value):
	if value is None or value == "":
		return None
	if isinstance(value, time):
		return value
	if isinstance(value, timedelta):
		return (datetime.min + value).time()
	return frappe.utils.get_datetime(value).time()


# Asset profile: the Object's name, category and space, and the Space > Floor > Building > Site >
# Project > Client chain. Always overwritten, so the read-only fields cannot be tampered with.
def fetch_object_details(wo):
	if not wo.object:
		return
	obj = frappe.db.get_value("Object", wo.object, ["object_name", "object_category", "space"], as_dict=True)
	if not obj:
		return

	wo.object_name = obj.object_name
	wo.object_category = obj.object_category
	wo.space = obj.space
	if wo.space:
		space = frappe.db.get_value(
			"Space", wo.space, ["maintenance_floor", "building_name", "operations_site", "project"], as_dict=True
		)
		if space:
			wo.maintenance_floor = space.maintenance_floor
			wo.building = space.building_name
			wo.operations_site = space.operations_site
			wo.project = space.project
			if wo.project:
				wo.client = frappe.db.get_value("Project", wo.project, "customer")


# The Object's spare parts, only while the table is empty.
def fetch_object_parts(wo):
	if not wo.object or wo.object_parts:
		return
	for part in frappe.get_all(
		"Object Items", filters={"parent": wo.object, "parenttype": "Object"},
		fields=["item_name", "description"], order_by="idx asc",
	):
		wo.append("object_parts", {"item_name": part.item_name, "description": part.description})


# The assigned team's lead and crew, only while the crew table is empty.
def populate_maintenance_team(wo):
	if not wo.assigned_maintenance_team or wo.object_maintenance_team:
		return
	team_lead = frappe.db.get_value("Asset Maintenance Team", wo.assigned_maintenance_team, "maintenance_manager")
	if team_lead:
		wo.maintenance_team_lead = team_lead
	for member in frappe.get_all(
		"Maintenance Team Member",
		filters={"parent": wo.assigned_maintenance_team, "parenttype": "Asset Maintenance Team"},
		fields=["team_member", "full_name", "maintenance_role"], order_by="idx asc",
	):
		wo.append("object_maintenance_team", {
			"team_member": member.team_member, "full_name": member.full_name, "maintenance_role": member.maintenance_role,
		})


# The master checklist of the asset's category. A Work Order raised from a schedule slot carries
# only its due tasks, so it never gets the full template.
def route_maintenance_checklist(wo):
	if not wo.object_category:
		return
	checklist_name = frappe.db.get_value("Object Maintenance Checklist", {"object_category": wo.object_category}, "name")
	if not checklist_name:
		return

	# The checklist link is mandatory, so it is resolved even when the schedule generator filled the rows.
	if not wo.object_maintenance_checklist_items or not wo.object_maintenance_checklist:
		wo.object_maintenance_checklist = checklist_name
	if wo.object_maintenance_checklist_items or wo.maintenance_schedule:
		return

	for item in frappe.get_all(
		"Object Maintenance Checklist Items",
		filters={"parent": checklist_name, "parenttype": "Object Maintenance Checklist"},
		fields=["sequence_no", "task_description", "photo_required", "reference_image",
			"maintenance_frequency", "frequency_days"],
		order_by="idx asc",
	):
		wo.append("object_maintenance_checklist_items", {
			"sequence_no": item.sequence_no,
			"task_description": item.task_description,
			"is_required": item.get("photo_required", 0),
			"reference_image": item.reference_image,
			"maintenance_frequency": item.maintenance_frequency,
			"frequency_days": item.frequency_days,
		})


# The active, submitted contract for Work Orders: the client's own, else the default one.
def find_matching_sla(wo):
	today = frappe.utils.getdate()
	sla = frappe.qb.DocType("Maintenance Service Level Agreement")
	active = (
		(sla.enabled == 1) & (sla.docstatus == 1) & (sla.document_type == "Maintenance Work Order")
		& ((sla.start_date.isnull()) | (sla.start_date <= today))
		& ((sla.end_date.isnull()) | (sla.end_date >= today))
	)

	if wo.client:
		match = (
			frappe.qb.from_(sla).select(sla.name).where(active)
			.where(sla.entity_type == "Customer").where(sla.entity == wo.client)
			.where(sla.default_service_level_agreement == 0).limit(1)
		).run(as_dict=True)
		if match:
			return frappe.get_doc("Maintenance Service Level Agreement", match[0].name)

	match = (
		frappe.qb.from_(sla).select(sla.name).where(active).where(sla.default_service_level_agreement == 1).limit(1)
	).run(as_dict=True)
	if match:
		return frappe.get_doc("Maintenance Service Level Agreement", match[0].name)
	return None


# Public Holiday, then Weekly Off from the holiday list, then the working hours of the
# weekday, else After Working Hours. A weekday with no working hours is a Weekly Off.
def determine_sla_shift_type(wo, sla):
	trigger_dt = frappe.utils.get_datetime(wo.sla_trigger_time)
	if sla.holiday_list:
		holiday = frappe.db.get_value(
			"Maintenance Holiday Item", {"parent": sla.holiday_list, "holiday_date": trigger_dt.date()},
			["weekly_off", "public_holiday"], as_dict=True,
		)
		if holiday and holiday.public_holiday:
			wo.sla_shift_type = "Public Holiday"
			return
		if holiday and holiday.weekly_off:
			wo.sla_shift_type = "Weekly Off"
			return

	weekday_name = trigger_dt.strftime("%A")
	working_day = next((day for day in sla.support_and_resolution if day.workday == weekday_name), None)
	if not working_day:
		wo.sla_shift_type = "Weekly Off"
		return

	start_time = to_time(working_day.start_time) or time(0, 0)
	end_time = to_time(working_day.end_time) or time(23, 59, 59)
	wo.sla_shift_type = "Working Hours" if start_time <= trigger_dt.time() <= end_time else "After Working Hours"


# The response and resolution targets of the priority and shift type, else of the priority alone.
# Durations are stored in seconds.
def fetch_sla_targets(wo, sla):
	if not wo.priority or not wo.sla_shift_type:
		return
	rows = [row for row in sla.priorities if row.priority == wo.priority]
	row = next((r for r in rows if r.sla_shift_type == wo.sla_shift_type), rows[0] if rows else None)
	if row:
		wo.target_response_minutes = frappe.utils.flt(row.response_time) / 60.0 if row.response_time else 0
		wo.target_resolution_minutes = frappe.utils.flt(row.resolution_time) / 60.0 if row.resolution_time else 0


def apply_sla(wo, sla):
	for title, step in (("SLA Shift Type Determination Failed", determine_sla_shift_type), ("SLA Target Fetch Failed", fetch_sla_targets)):
		try:
			step(wo, sla)
		except Exception:
			frappe.log_error(title=title, message=frappe.get_traceback())


# On insert: the creation timestamp, and for a Reactive ticket the contract, a clock locked to
# now and its targets. Returns False when a Reactive ticket has no contract, which the controller refuses.
def initialise(wo):
	if not wo.creation_datetime:
		wo.creation_datetime = frappe.utils.now_datetime()
	if wo.maintenance_type != "Reactive Maintenance":
		return True

	sla = find_matching_sla(wo)
	if not sla:
		return False
	wo.sla_master = sla.name
	wo.sla_trigger_time = frappe.utils.now_datetime()
	apply_sla(wo, sla)
	return True


# A Preventive Work Order's target start: the schedule slot's planned datetime, else the
# Object's Last Service Date, Commissioning Date or creation plus the slot's frequency, at 08:00.
def compute_preventive_trigger(wo):
	if not wo.object:
		return None
	schedule = wo.maintenance_schedule and frappe.db.get_value(
		"Maintenance Schedule Entry", wo.maintenance_schedule, ["frequency_days", "planned_execution_datetime"], as_dict=True
	)
	if schedule and schedule.planned_execution_datetime:
		return frappe.utils.get_datetime(schedule.planned_execution_datetime)

	frequency_days = frappe.utils.cint(schedule.frequency_days) if schedule else 0
	obj = frequency_days and frappe.db.get_value(
		"Object", wo.object, ["last_service_date", "commissioning_date", "creation"], as_dict=True
	)
	if not obj:
		return None
	base_date = obj.last_service_date or obj.commissioning_date or frappe.utils.getdate(obj.creation)
	return frappe.utils.get_datetime(f"{frappe.utils.add_days(frappe.utils.getdate(base_date), frequency_days)} 08:00:00")


# Freezes a Preventive Work Order's trigger time and binds its contract, default priority and
# targets. Only empty fields are filled, so the frozen timeline survives later saves.
def set_preventive_sla(wo):
	if wo.maintenance_type != "Preventive Maintenance":
		return
	if not wo.sla_trigger_time:
		wo.sla_trigger_time = compute_preventive_trigger(wo)
	if not wo.sla_master:
		sla = find_matching_sla(wo)
		if sla:
			wo.sla_master = sla.name
	if wo.sla_master and wo.sla_trigger_time:
		sla = frappe.get_cached_doc("Maintenance Service Level Agreement", wo.sla_master)
		if not wo.priority and sla.default_priority:
			wo.priority = sla.default_priority
		apply_sla(wo, sla)


# Add the open hold window to Total Paused Minutes and close it.
def bank_open_hold(wo, as_of):
	if not wo.hold_started_on:
		return
	elapsed = (frappe.utils.get_datetime(as_of) - frappe.utils.get_datetime(wo.hold_started_on)).total_seconds() / 60.0
	wo.total_paused_minutes = frappe.utils.flt(frappe.utils.flt(wo.total_paused_minutes) + elapsed, 2)
	wo.hold_started_on = None


def open_hold_minutes(wo, as_of):
	if wo.status == ON_HOLD_STATUS and wo.hold_started_on:
		return (frappe.utils.get_datetime(as_of) - frappe.utils.get_datetime(wo.hold_started_on)).total_seconds() / 60.0
	return 0.0


# The pause clock starts when the Work Order goes On Hold - Parts Required and is banked when it
# leaves. While on hold, every save and countdown run rolls the open window into Total Paused
# Minutes and restarts it, so the paused time shows live. Outside a save there is no previous
# version, so the status counts as unchanged.
def track_pause_windows(wo, as_of=None):
	now = frappe.utils.get_datetime(as_of) if as_of else frappe.utils.now_datetime()
	previous = wo.get_doc_before_save() if hasattr(wo, "get_doc_before_save") else None
	previous_status = previous.status if previous else wo.status

	if wo.status == ON_HOLD_STATUS and previous_status != ON_HOLD_STATUS:
		if not wo.hold_started_on:
			wo.hold_started_on = now
	elif previous_status == ON_HOLD_STATUS and wo.status != ON_HOLD_STATUS:
		bank_open_hold(wo, now)
	elif wo.status == ON_HOLD_STATUS and wo.hold_started_on:
		bank_open_hold(wo, now)
		wo.hold_started_on = now


# The live countdown of a Preventive Work Order: Pre-Start with counters at 0 before the trigger
# time, then Active Counting, then Fail once a target is exceeded. Paused minutes are subtracted.
# The verdicts at check-in and completion are left to evaluate_sla_response and evaluate_sla_resolution.
def refresh_sla_statuses(wo, as_of=None):
	if wo.maintenance_type != "Preventive Maintenance" or not wo.sla_trigger_time:
		return

	now = frappe.utils.get_datetime(as_of) if as_of else frappe.utils.now_datetime()
	trigger = frappe.utils.get_datetime(wo.sla_trigger_time)
	paused = frappe.utils.flt(wo.total_paused_minutes) + open_hold_minutes(wo, now)
	elapsed = (now - trigger).total_seconds() / 60.0 - paused

	if not wo.first_check_in_time and wo.sla_response_status not in FINAL_STATUSES:
		if now < trigger:
			wo.sla_response_status = "Pre-Start"
			wo.actual_response_minutes = 0
		else:
			wo.actual_response_minutes = frappe.utils.flt(elapsed, 2)
			failed = wo.target_response_minutes and elapsed > wo.target_response_minutes
			wo.sla_response_status = "Fail" if failed else "Active Counting"

	if not wo.completion_time and wo.sla_resolution_status not in FINAL_STATUSES:
		if now < trigger:
			wo.sla_resolution_status = "Pre-Start"
			wo.net_resolution_minutes = 0
		else:
			wo.net_resolution_minutes = frappe.utils.flt(elapsed, 2)
			failed = wo.target_resolution_minutes and elapsed > wo.target_resolution_minutes
			wo.sla_resolution_status = "Fail" if failed else "Active Counting"


# At check-in: Actual Response Minutes = First Check In Time - SLA Trigger Time - paused minutes,
# Pass within the target, else Fail. Supersedes the live countdown.
def evaluate_sla_response(wo):
	if not wo.sla_trigger_time or not wo.first_check_in_time:
		return
	elapsed = (
		frappe.utils.get_datetime(wo.first_check_in_time) - frappe.utils.get_datetime(wo.sla_trigger_time)
	).total_seconds() / 60.0 - frappe.utils.flt(wo.total_paused_minutes)
	wo.actual_response_minutes = frappe.utils.flt(elapsed, 2)
	if wo.target_response_minutes:
		wo.sla_response_status = "Pass" if wo.actual_response_minutes <= wo.target_response_minutes else "Fail"


# At completion: Net Resolution Minutes = Completion Time - SLA Trigger Time - paused minutes.
def evaluate_sla_resolution(wo):
	if not wo.sla_trigger_time or not wo.completion_time:
		return
	elapsed = (
		frappe.utils.get_datetime(wo.completion_time) - frappe.utils.get_datetime(wo.sla_trigger_time)
	).total_seconds() / 60.0
	wo.net_resolution_minutes = frappe.utils.flt(elapsed - frappe.utils.flt(wo.total_paused_minutes), 2)
	if wo.target_resolution_minutes:
		wo.sla_resolution_status = "Pass" if wo.net_resolution_minutes <= wo.target_resolution_minutes else "Fail"


# Planned Deadline = SLA Trigger Time + Target Resolution Minutes, counted only inside the
# contract's working hours, skipping weekly offs and holidays. A fixed target: pauses do not move it.
def set_planned_deadline(wo):
	if not wo.sla_trigger_time or not frappe.utils.flt(wo.target_resolution_minutes):
		wo.planned_deadline = None
		return

	remaining = frappe.utils.flt(wo.target_resolution_minutes)
	trigger_dt = frappe.utils.get_datetime(wo.sla_trigger_time)
	sla = wo.sla_master and frappe.get_cached_doc("Maintenance Service Level Agreement", wo.sla_master)
	if not sla or not sla.support_and_resolution:
		wo.planned_deadline = frappe.utils.add_to_date(trigger_dt, minutes=remaining)
		return
	wo.planned_deadline = project_working_deadline(wo, sla, trigger_dt, remaining)


def project_working_deadline(wo, sla, trigger_dt, remaining_minutes):
	working_days = {}
	for day in sla.support_and_resolution:
		start_t, end_t = to_time(day.start_time), to_time(day.end_time)
		if start_t is not None and end_t is not None and end_t > start_t:
			working_days[day.workday] = (start_t, end_t)
	if not working_days:
		return frappe.utils.add_to_date(trigger_dt, minutes=remaining_minutes)

	# Every listed date, weekly off or public holiday, is a full non-working day.
	holidays = set()
	if sla.holiday_list:
		holidays = {
			frappe.utils.getdate(d)
			for d in frappe.get_all("Maintenance Holiday Item", filters={"parent": sla.holiday_list}, pluck="holiday_date")
		}

	cursor = trigger_dt
	remaining = frappe.utils.flt(remaining_minutes)
	# A misconfigured calendar can never loop forever.
	for _ in range(1000):
		if remaining <= 0:
			break
		day_date = cursor.date()
		next_day = datetime.combine(day_date + timedelta(days=1), time(0, 0))
		weekday_name = cursor.strftime("%A")
		if day_date in holidays or weekday_name not in working_days:
			cursor = next_day
			continue

		start_t, end_t = working_days[weekday_name]
		cursor = max(cursor, datetime.combine(day_date, start_t))
		window_end = datetime.combine(day_date, end_t)
		if cursor >= window_end:
			cursor = next_day
			continue

		available = (window_end - cursor).total_seconds() / 60.0
		if remaining <= available:
			return cursor + timedelta(minutes=remaining)
		remaining -= available
		cursor = next_day

	if remaining > 0:
		frappe.log_error(
			title="Planned Deadline Projection Exceeded Calendar Window",
			message="Could not place {0} resolution minutes within the SLA working calendar for Work Order {1}.".format(
				frappe.utils.flt(wo.target_resolution_minutes), wo.name or "(unsaved)"
			),
		)
	return cursor


# Every save of a Work Order.
def calculate(wo):
	fetch_object_details(wo)
	fetch_object_parts(wo)
	populate_maintenance_team(wo)
	route_maintenance_checklist(wo)
	set_preventive_sla(wo)
	track_pause_windows(wo)
	refresh_sla_statuses(wo)
	evaluate_sla_response(wo)
	evaluate_sla_resolution(wo)
	set_planned_deadline(wo)


# Every open Preventive Work Order whose clock has started and has a verdict still to reach.
def advance_countdowns():
	advanced = 0
	for name in frappe.get_all(
		"Maintenance Work Order",
		filters={"docstatus": 0, "maintenance_type": "Preventive Maintenance", "sla_trigger_time": ["is", "set"]},
		pluck="name",
	):
		try:
			wo = frappe.get_doc("Maintenance Work Order", name)
			if wo.sla_response_status in FINAL_STATUSES and wo.sla_resolution_status in FINAL_STATUSES:
				continue
			track_pause_windows(wo)
			refresh_sla_statuses(wo)
			wo.db_set({
				"sla_response_status": wo.sla_response_status,
				"sla_resolution_status": wo.sla_resolution_status,
				"actual_response_minutes": wo.actual_response_minutes,
				"net_resolution_minutes": wo.net_resolution_minutes,
				"total_paused_minutes": wo.total_paused_minutes,
				"hold_started_on": wo.hold_started_on,
			}, update_modified=False)
			advanced += 1
		except Exception:
			frappe.log_error(title="Maintenance SLA Status Update Failed", message=frappe.get_traceback())
	return advanced


if bpmn_id:
	result["countdowns_advanced"] = advance_countdowns()
""",
	"Assign Team Lead": """# Gives the Check In step to the Work Order's Maintenance Team Lead. A Work Order with no team
# yet, such as one raised from the schedule, goes to the Maintenance Manager User in
# Maintenance Settings, for the Maintenance Manager role.
if doc.maintenance_team_lead:
	result["assigned_user"] = doc.maintenance_team_lead
	result["assigned_role"] = ""
else:
	result["assigned_user"] = frappe.db.get_single_value("Maintenance Settings", "maintenance_manager_user") or ""
	result["assigned_role"] = "Maintenance Manager"
""",
	"Record Work Order Check-In": """# Stamps the technician's first on-site check-in and sets the SLA response verdict, by the
# Calculate Work Order rules. The first check-in wins. Written with db_set, so a field the
# technician left invalid on the form cannot halt the process.
from one_fm.one_fm.processa_rules import run_rule

if doc.get("name") and not doc.first_check_in_time:
	doc.first_check_in_time = frappe.utils.now_datetime()
	run_rule("Calculate Work Order", "evaluate_sla_response", doc)
	doc.db_set({
		"first_check_in_time": doc.first_check_in_time,
		"actual_response_minutes": doc.actual_response_minutes,
		"sla_response_status": doc.sla_response_status,
	})
result["checked_in"] = bool(doc.get("first_check_in_time"))
""",
	"Validate Work Order Completion": """# Only a checked-in Work Order whose Status is Completed may be submitted.
problems = []
if doc.status != "Completed":
	problems.append(frappe._("Set the Status to Completed before submitting this Work Order."))
if not doc.first_check_in_time:
	problems.append(frappe._("Record the technician's check-in (the Check In step) before submitting this Work Order."))
for message in problems:
	frappe.msgprint(message, title=frappe._("Work Order Not Ready"), indicator="red")
result["work_order_ready"] = not problems
""",
	"Close Work Order SLA": """# Stamps the Completion Time, banks any hold still open, and sets the SLA resolution verdict by
# the Calculate Work Order rules, just before the Work Order is submitted. Always overwritten,
# so a value typed on the draft is never kept.
from one_fm.one_fm.processa_rules import run_rule

if doc.get("name"):
	doc.completion_time = frappe.utils.now_datetime()
	run_rule("Calculate Work Order", "bank_open_hold", doc, doc.completion_time)
	run_rule("Calculate Work Order", "evaluate_sla_resolution", doc)
	doc.db_set({
		"completion_time": doc.completion_time,
		"hold_started_on": doc.hold_started_on,
		"total_paused_minutes": doc.total_paused_minutes,
		"net_resolution_minutes": doc.net_resolution_minutes,
		"sla_resolution_status": doc.sla_resolution_status,
	})
	result["completion_time"] = str(doc.completion_time)
""",
}


class Rules:
	"""A script's functions and constants as attributes. The attributes are the script's own
	namespace, so patching one (patch.object(rules, "fn")) also changes what the other
	functions of the script call."""


def rules(script_name):
	"""The functions and constants a script defines, without taking its map step."""
	namespace = {"frappe": frappe, "doc": frappe._dict(), "task_data": {}, "result": {},
		"context_doctype": "", "context_docname": "", "bpmn_id": ""}
	exec(SCRIPTS[script_name], namespace)
	found = Rules()
	found.__dict__ = namespace
	return found


def run(script_name, doc=None, **task_data):
	"""Run a script the way the Processa engine does, as a map step, and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc or frappe._dict(),
		"task_data": task_data,
		"result": result,
		"context_doctype": doc.doctype if doc else "",
		"context_docname": doc.name if doc else "",
		"bpmn_id": "test",
	}
	namespace.update(task_data)
	exec(SCRIPTS[script_name], namespace)
	return result


def install_scripts():
	"""Put these bodies on the site, so the hooks under test run the reviewed scripts."""
	for name, body in SCRIPTS.items():
		if frappe.db.exists("Server Script", name):
			frappe.db.set_value("Server Script", name, {"script": body, "disabled": 0}, update_modified=False)
		else:
			frappe.get_doc({"doctype": "Server Script", "name": name, "script_type": "API",
				"api_method": frappe.scrub(name), "script": body}).db_insert()


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is not None:
				self.assertEqual(saved.strip(), body.strip(), msg=name)
