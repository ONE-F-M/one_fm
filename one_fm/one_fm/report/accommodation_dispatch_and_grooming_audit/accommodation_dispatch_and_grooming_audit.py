# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

"""Accommodation Dispatch and Grooming Audit (WI-003682).

One row per CAMP DEPARTURE run (level 1), with the rostered boarding passengers
nested underneath it (level 2).

A run is a camp departure when its Stop 1 is an Accommodation: it has a Boarding row on
stop_sequence 1 carrying a pickup_accommodation. Return legs (their rows are Dropping
Off), shuttles and site transfers (no accommodation at Stop 1) are left out.

Lock Status is the check-in lock, read per run exactly as the manifest reads it:
Not Started / In Progress (Stop N) / Completed.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, cstr, getdate, today
from frappe.utils import to_timedelta

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
	names = fetch_employee_names(collect_employee_ids(parents, children))

	trips = build_trips(parents, children, names)
	trips = [trip for trip in trips if trip_matches_filters(trip, filters)]

	return columns, build_rows(trips, filters.get("search"))


# ── Data access ──────────────────────────────────────────────────────────────


def fetch_parents(report_date):
	return frappe.get_list(
		"Transportation Manifest",
		filters={"schedule_date": report_date},
		fields=[
			"name",
			"vehicle_no",
			"license_plate",
			"driver_name",
			"active_stop_by_trip",
			"active_stop_sequence",
		],
		order_by="name asc",
		limit_page_length=0,
	)


def fetch_children(parent_names):
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
			"scheduled_time",
			"employee",
			"employee_name",
			"attendance_status",
			"boarding_time",
			"qoa_status",
			"qoa_reason",
			"reliever_employee",
		],
		order_by="parent asc, idx asc",
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


# ── Row logic ────────────────────────────────────────────────────────────────


def get_active_stop_map(parent) -> dict:
	"""{trip_id: active stop} for one manifest, as TransportationManifest.active_stop_map.

	A manifest written before the per-run split carries a single number for the whole
	vehicle; every run inherits it.
	"""
	try:
		stored = json.loads(parent.get("active_stop_by_trip") or "{}") or {}
	except ValueError:
		stored = {}
	return {str(key): cint(value) for key, value in stored.items()}


def get_lock_status(active_stop, last_stop):
	"""Check-in lock of one run: a stop below the pointer is Completed (see
	TransportationManifest.enforce_stop_locking), the pointer itself is in progress."""
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


def format_departure(value):
	if not value:
		return ""
	minutes = int(to_timedelta(value).total_seconds() // 60) % (24 * 60)
	return f"{minutes // 60:02d}:{minutes % 60:02d}"


def build_trips(parents, children, names):
	"""Group the boarding rows into runs and keep only the camp departures."""
	by_parent = {}
	for child in children:
		by_parent.setdefault(child.parent, []).append(child)

	trips = []
	for parent in parents:
		grouped = {}
		for child in by_parent.get(parent.name, []):
			grouped.setdefault(cstr(child.trip_id or UNGROUPED_TRIP), []).append(child)

		active_map = get_active_stop_map(parent)
		legacy_active = cint(parent.get("active_stop_sequence")) if not active_map else 0

		for trip_id, rows in grouped.items():
			camp_rows = [
				row for row in rows if cint(row.stop_sequence or 1) == 1 and row.pickup_accommodation
			]
			if not camp_rows:
				continue

			camps = []
			for row in camp_rows:
				if row.pickup_accommodation not in camps:
					camps.append(row.pickup_accommodation)

			passengers = []
			for row in rows:
				info = classify_passenger(row, names.get(row.reliever_employee))
				info["row"] = row
				passengers.append(info)

			times = [to_timedelta(row.scheduled_time) for row in camp_rows if row.scheduled_time]
			active = active_map.get(trip_id, legacy_active)
			headcount = len(passengers)
			passed = sum(p["passed"] for p in passengers)

			trips.append(
				frappe._dict(
					manifest=parent.name,
					trip_id=trip_id,
					departure=format_departure(min(times)) if times else "",
					vehicle=parent.license_plate or parent.vehicle_no,
					driver=names.get(parent.driver_name) or parent.driver_name or "",
					camps=camps,
					headcount=headcount,
					passed=passed,
					absent=sum(p["absent"] for p in passengers),
					warnings=sum(p["failed"] for p in passengers),
					lock_status=get_lock_status(active, max(cint(r.stop_sequence or 1) for r in rows)),
					passengers=passengers,
				)
			)
	return trips


def trip_matches_filters(trip, filters):
	camp = filters.get("camp")
	if camp and camp not in trip.camps:
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


def build_rows(trips, search=None):
	"""Flatten the runs into indented rows: each run, then its passengers."""
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
		passengers = trip.passengers
		if needle:
			trip_hit = _contains(needle, trip.vehicle, trip.driver)
			matching = [
				p for p in passengers
				if _contains(needle, p["row"].employee, p["row"].employee_name)
			]
			if not trip_hit and not matching:
				continue
			if not trip_hit:
				passengers = matching

		trip_key = unique(trip.trip_id or trip.manifest)
		data.append(
			{
				"row_id": trip_key,
				"parent_row": "",
				"indent": 0,
				"trip_id": trip.trip_id,
				"manifest": trip.manifest,
				"departure_time": trip.departure,
				"vehicle": trip.vehicle,
				"driver": trip.driver,
				"camp": ", ".join(trip.camps),
				"headcount": trip.headcount,
				"compliance_summary": f"{trip.passed}/{trip.headcount} Passed",
				"compliance_warnings": trip.warnings,
				"lock_status": trip.lock_status,
			}
		)

		for p in passengers:
			row = p["row"]
			label = f"{row.employee or ''} - {row.employee_name or ''}".strip(" -")
			data.append(
				{
					"row_id": unique(label or row.name),
					"parent_row": trip_key,
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
