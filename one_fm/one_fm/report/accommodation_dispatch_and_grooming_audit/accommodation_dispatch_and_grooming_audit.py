# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

"""Accommodation Dispatch and Grooming Audit (WI-003682).

One row per CAMP DEPARTURE run (level 1, indent 0), with the rostered boarding passengers
nested underneath it (level 2, indent 1, ``parent_trip`` pointing at the run).

A camp pickup is any manifest child row whose ``employee_action`` is "Boarding". A run
(one ``trip_id`` on one manifest) is in scope when it has at least one. Return legs
(Dropping Off rows), shuttles and site transfers carry no Boarding rows and are left out.
Scope deliberately does not read ``stop_sequence`` as "stop 1": in a Mixed manifest the
sequence counts visits, not the position in the run.

Lock Status is the check-in lock, read per run exactly as the manifest reads it
(``active_stop_for``): Not Started / In Progress (Stop N) / Completed.
"""

import frappe
from frappe import _
from frappe.utils import cint, cstr, getdate, today

from one_fm.one_fm.doctype.transportation_manifest.manifest_sheet import _accommodation_labels

UNGROUPED_TRIP = ""

COMPLIANCE_ALL = "All Trips"
COMPLIANCE_PASSED = "100% Passed Trips"
COMPLIANCE_ABSENTEES = "Trips with Absentees"
COMPLIANCE_FAILS = "Trips with Grooming/Uniform Fails"

# Attendance / appearance labels. The JS formatter keys its indicator colours on these.
PRESENT = "Present"
ABSENT = "Absent"
ABSENT_UNCOVERED = "Absent (Uncovered)"
PENDING = "Pending"
PASSED = "Eligible & Dispatched"
FAILED = "Failed"
NOT_CHECKED = "Not Checked"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()

	report_date = getdate(filters.get("date") or today())
	# Nothing has been checked or boarded on a day that has not happened yet.
	if report_date > getdate(today()):
		return columns, []

	parents = fetch_parents(report_date)
	if not parents:
		return columns, []

	children = fetch_children([parent.name for parent in parents])
	if not children:
		return columns, []

	names = fetch_employee_names(collect_employee_ids(parents, children))
	labels = _accommodation_labels(
		list({child.pickup_accommodation for child in children if child.pickup_accommodation})
	)

	trips = build_trips(parents, children, names, labels)
	attach_departures(trips)
	trips = [trip for trip in trips if trip_matches_filters(trip, filters)]

	return columns, build_rows(trips, filters.get("search"))


# ── Data access ──────────────────────────────────────────────────────────────


def fetch_parents(report_date):
	"""The day's manifests the current user may read (get_list applies permissions)."""
	try:
		return frappe.get_list(
			"Transportation Manifest",
			filters={"schedule_date": report_date},
			fields=["name", "vehicle_no", "license_plate", "driver_name"],
			order_by="name asc",
			limit_page_length=0,
		)
	except frappe.PermissionError:
		return []


def fetch_children(parent_names):
	"""Every camp pickup (Boarding row) on the permitted manifests, in stop order."""
	return frappe.get_all(
		"Transportation Manifest Details",
		filters={
			"parent": ["in", parent_names],
			"parenttype": "Transportation Manifest",
			"employee_action": "Boarding",
		},
		fields=[
			"name",
			"parent",
			"idx",
			"trip_id",
			"stop_sequence",
			"pickup_accommodation",
			"employee",
			"employee_name",
			"attendance_status",
			"boarding_time",
			"qoa_status",
			"qoa_reason",
			"reliever_employee",
		],
		order_by="parent asc, stop_sequence asc, idx asc",
		limit_page_length=0,
	)


def fetch_employee_names(employee_ids):
	if not employee_ids:
		return {}
	rows = frappe.get_all(
		"Employee",
		filters={"name": ["in", list(employee_ids)]},
		fields=["name", "employee_name"],
		limit_page_length=0,
	)
	return {row.name: row.employee_name for row in rows}


def collect_employee_ids(parents, children):
	ids = {parent.driver_name for parent in parents if parent.driver_name}
	ids.update(child.reliever_employee for child in children if child.reliever_employee)
	ids.update(child.employee for child in children if child.employee)
	return ids


def fetch_departures(trip_ids):
	"""{trip_id: "HH:MM:SS"} - the camp leg's start time on the Route Plan Assignment.

	One batched query. The departure is the start of the run's lowest-numbered camp leg
	(never a manifest row's scheduled_time, which on a Boarding row is the arrival at the
	drop-off site). Only the time of day is used, so the plan rows are not filtered by
	date. A run with no camp leg gets no departure.
	"""
	trip_ids = [trip_id for trip_id in set(trip_ids) if trip_id]
	if not trip_ids:
		return {}

	from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
		_local_seconds,
		_time_field,
	)

	rows = frappe.get_all(
		"Route Plan Assignment",
		filters={"trip_group": ["in", trip_ids], "is_camp_leg": 1},
		fields=["trip_group", "stop_index", "start_time"],
		limit_page_length=0,
	)

	first = {}
	for row in rows:
		current = first.get(row.trip_group)
		if current is None or cint(row.stop_index) < cint(current.stop_index):
			first[row.trip_group] = row

	return {
		trip_id: _time_field(_local_seconds(row.start_time)) or ""
		for trip_id, row in first.items()
	}


# ── Row logic ────────────────────────────────────────────────────────────────


def get_lock_status(active_stop, last_stop):
	"""Check-in lock of one run: pointer 0 has not started, a pointer past the run's
	highest stop has finished it, anything between is in progress at that stop."""
	active_stop = cint(active_stop)
	if not active_stop:
		return _("Not Started")
	if active_stop > cint(last_stop):
		return _("Completed")
	return _("In Progress (Stop {0})").format(active_stop)


def classify_passenger(child, reliever_name=None):
	"""Attendance / appearance result of one boarding row.

	Returns a dict: attendance, appearance, failure_reason, reliever, passed, absent, failed.
	"""
	status = child.get("attendance_status")
	result = {
		"attendance": PENDING,
		"appearance": "",
		"failure_reason": "",
		"reliever": "",
		"passed": 0,
		"absent": 0,
		"failed": 0,
	}

	if status == "Absent":
		result["absent"] = 1
		result["attendance"] = ABSENT if child.get("reliever_employee") else ABSENT_UNCOVERED
	elif status == "Present":
		result["attendance"] = PRESENT
		qoa = child.get("qoa_status")
		if qoa == "Pass":
			result["appearance"] = PASSED
			result["passed"] = 1
		elif qoa == "Fail":
			result["appearance"] = FAILED
			result["failure_reason"] = child.get("qoa_reason") or ""
			result["failed"] = 1
		else:
			result["appearance"] = NOT_CHECKED

	if child.get("reliever_employee"):
		original = child.get("employee_name") or child.get("employee") or ""
		substitute = reliever_name or child.get("reliever_employee")
		result["reliever"] = f"{original} \u2794 {substitute}"

	return result


def build_trips(parents, children, names, labels):
	"""Group the Boarding rows by (manifest, trip_id) into runs."""
	parent_by_name = {parent.name: parent for parent in parents}

	grouped = {}
	for child in children:
		key = (child.parent, cstr(child.trip_id or UNGROUPED_TRIP))
		grouped.setdefault(key, []).append(child)

	active_cache = {}

	def active_stop(manifest, trip_id):
		if manifest not in active_cache:
			active_cache[manifest] = frappe.get_doc("Transportation Manifest", manifest)
		return active_cache[manifest].active_stop_for(trip_id)

	trips = []
	for (manifest, trip_id), rows in grouped.items():
		parent = parent_by_name.get(manifest)
		if not parent:
			continue

		# The rows arrive ordered by stop, so the labels come out in stop order.
		camp_ids = []
		for row in rows:
			if row.pickup_accommodation and row.pickup_accommodation not in camp_ids:
				camp_ids.append(row.pickup_accommodation)
		camp_labels = []
		for acc in camp_ids:
			label = labels.get(acc) or acc
			if label not in camp_labels:
				camp_labels.append(label)

		passengers = []
		for row in rows:
			info = classify_passenger(row, names.get(row.reliever_employee))
			info["row"] = row
			info["reliever_name"] = names.get(row.reliever_employee) or ""
			passengers.append(info)

		highest = max(cint(row.stop_sequence or 1) for row in rows)
		trips.append(
			frappe._dict(
				manifest=manifest,
				trip_id=trip_id,
				departure="",
				vehicle=parent.license_plate or parent.vehicle_no,
				driver=names.get(parent.driver_name) or parent.driver_name or "",
				camp_ids=camp_ids,
				camps=camp_labels,
				headcount=len(passengers),
				present=sum(1 for p in passengers if p["attendance"] == PRESENT),
				passed=sum(p["passed"] for p in passengers),
				absent=sum(p["absent"] for p in passengers),
				warnings=sum(p["failed"] for p in passengers),
				lock_status=get_lock_status(active_stop(manifest, trip_id), highest),
				passengers=passengers,
			)
		)
	return trips


def attach_departures(trips):
	departures = fetch_departures([trip.trip_id for trip in trips])
	for trip in trips:
		trip.departure = departures.get(trip.trip_id, "")


def trip_matches_filters(trip, filters):
	camp = filters.get("camp")
	if camp and camp not in trip.camp_ids:
		return False

	compliance = filters.get("compliance") or COMPLIANCE_ALL
	if compliance == COMPLIANCE_PASSED:
		return trip.headcount > 0 and trip.passed == trip.headcount
	if compliance == COMPLIANCE_ABSENTEES:
		return trip.absent > 0
	if compliance == COMPLIANCE_FAILS:
		return trip.warnings > 0
	return True


def _contains(needle, *haystack):
	return any(needle in cstr(value).lower() for value in haystack)


def trip_matches_search(trip, needle):
	if _contains(needle, trip.vehicle, trip.driver):
		return True
	return any(
		_contains(
			needle,
			p["row"].employee,
			p["row"].employee_name,
			p["row"].reliever_employee,
			p["reliever_name"],
		)
		for p in trip.passengers
	)


def compliance_summary(passed, headcount):
	percent = round(passed * 100 / headcount) if headcount else 0
	return f"{passed}/{headcount} ({percent}%)"


def build_rows(trips, search=None):
	"""Flatten the runs into indented rows: each run, then all of its passengers.

	A run that matches the search is shown whole - the audit trail is never cut down to
	the passengers that happened to match.
	"""
	needle = cstr(search).strip().lower()
	data = []
	seen = set()

	def unique(label):
		key, n = label, 1
		while key in seen:
			n += 1
			key = f"{label} #{n}"
		seen.add(key)
		return key

	for trip in trips:
		if needle and not trip_matches_search(trip, needle):
			continue

		trip_key = unique(trip.trip_id or trip.manifest)
		data.append(
			{
				"row_id": trip_key,
				"parent_trip": None,
				"indent": 0,
				"trip_id": trip.trip_id,
				"manifest": trip.manifest,
				"departure_time": trip.departure,
				"vehicle": trip.vehicle,
				"driver": trip.driver,
				"camp": ", ".join(trip.camps),
				"headcount": trip.headcount,
				"present": trip.present,
				"compliance_summary": compliance_summary(trip.passed, trip.headcount),
				"compliance_warnings": trip.warnings,
				"lock_status": trip.lock_status,
			}
		)

		for p in trip.passengers:
			row = p["row"]
			label = f"{row.employee or ''} - {row.employee_name or ''}".strip(" -")
			data.append(
				{
					"row_id": unique(label or row.name),
					"parent_trip": trip_key,
					"indent": 1,
					"employee": row.employee,
					"employee_name": row.employee_name,
					"camp": row.pickup_accommodation,
					"boarding_time": row.boarding_time,
					"attendance_result": p["attendance"],
					"appearance_result": p["appearance"],
					"failure_reason": p["failure_reason"],
					"reliever_pairing": p["reliever"],
				}
			)
	return data


def get_columns():
	return [
		{"label": _("Trip / Passenger"), "fieldname": "row_id", "fieldtype": "Data", "width": 220},
		{"label": _("Trip ID"), "fieldname": "trip_id", "fieldtype": "Data", "width": 110},
		{"label": _("Manifest"), "fieldname": "manifest", "fieldtype": "Link", "options": "Transportation Manifest", "width": 150},
		{"label": _("Departure Time"), "fieldname": "departure_time", "fieldtype": "Data", "width": 100},
		{"label": _("Vehicle"), "fieldname": "vehicle", "fieldtype": "Data", "width": 110},
		{"label": _("Driver"), "fieldname": "driver", "fieldtype": "Data", "width": 150},
		{"label": _("Camp"), "fieldname": "camp", "fieldtype": "Data", "width": 150},
		{"label": _("Total Boarding Headcount"), "fieldname": "headcount", "fieldtype": "Int", "width": 90},
		{"label": _("Present"), "fieldname": "present", "fieldtype": "Int", "width": 80},
		{"label": _("Compliance Summary"), "fieldname": "compliance_summary", "fieldtype": "Data", "width": 130},
		{"label": _("Compliance Warnings"), "fieldname": "compliance_warnings", "fieldtype": "Int", "width": 100},
		{"label": _("Lock Status"), "fieldname": "lock_status", "fieldtype": "Data", "width": 150},
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 110},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
		{"label": _("Boarding Time"), "fieldname": "boarding_time", "fieldtype": "Datetime", "width": 160},
		{"label": _("Attendance"), "fieldname": "attendance_result", "fieldtype": "Data", "width": 140},
		{"label": _("Appearance"), "fieldname": "appearance_result", "fieldtype": "Data", "width": 150},
		{"label": _("Failure Reason"), "fieldname": "failure_reason", "fieldtype": "Data", "width": 110},
		{"label": _("Reliever"), "fieldname": "reliever_pairing", "fieldtype": "Data", "width": 260},
	]
