# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, get_datetime, getdate

# Document lifecycle -> Status (AC: a submitted record "updates to Completed").
STATUS_BY_DOCSTATUS = {0: "Active", 1: "Completed", 2: "Cancelled"}


def calculate_total_kilometers(odometer_start_km, odometer_end_km):
	"""Distance driven during the handover. Zero while the session is still open."""
	if not odometer_end_km:
		return 0

	return cint(odometer_end_km) - cint(odometer_start_km)


def get_handover_status(docstatus):
	return STATUS_BY_DOCSTATUS.get(cint(docstatus), "Active")


def validate_handover_window(handover_start_time, handover_end_time):
	if not (handover_start_time and handover_end_time):
		return

	if get_datetime(handover_end_time) <= get_datetime(handover_start_time):
		frappe.throw(
			_("Handover End Time must be after Handover Start Time."),
			title=_("Invalid Handover Window"),
		)


def validate_odometer_readings(odometer_start_km, odometer_end_km, session_closed=False):
	"""
	The vehicle cannot come back with fewer kilometres on it than it left with.

	Skipped while the session is open (no end time and no end reading), since an
	untouched Int field reads as 0 and would otherwise look like a rollback.
	"""
	if not session_closed and not odometer_end_km:
		return

	if cint(odometer_end_km) < cint(odometer_start_km):
		frappe.throw(
			_("Odometer End ({0} KM) cannot be lower than Odometer Start ({1} KM).").format(
				cint(odometer_end_km), cint(odometer_start_km)
			),
			title=_("Invalid Odometer Reading"),
		)


class VehicleHandoverLog(Document):
	def validate(self):
		validate_handover_window(self.handover_start_time, self.handover_end_time)
		validate_odometer_readings(
			self.odometer_start_km,
			self.odometer_end_km,
			session_closed=bool(self.handover_end_time),
		)
		self.total_kilometers = calculate_total_kilometers(
			self.odometer_start_km, self.odometer_end_km
		)
		# Freezing the form on submit needs no code - Frappe makes every field on a
		# submitted document read-only.
		self.status = get_handover_status(self.docstatus)

	def before_submit(self):
		"""
		Closing the session needs the end of the shift recorded (WI-001576).

		The end odometer reading is covered by validate_odometer_readings, which rejects
		anything below the start reading - including the 0 an untouched Int field holds.
		"""
		if not self.handover_end_time:
			frappe.throw(
				_("Handover End Time is required to close this handover."),
				title=_("Handover Not Finished"),
			)

	def on_cancel(self):
		# validate does not run on cancel, so the status is set directly.
		self.db_set("status", "Cancelled")


def get_handover_windows(vehicles, from_datetime, to_datetime):
	"""
	Submitted handover windows per vehicle overlapping [from_datetime, to_datetime].

	Batched for the Transportation Schedule canvas (WI-001577): one query for the whole
	day instead of a driver lookup per block. Windows with no Operational Driver are
	dropped so the block falls back to the vehicle's permanent custodian.

	Returns {vehicle: [{"start", "end", "operational_driver", "driver_name"}]}, each list
	ordered by start time.
	"""
	vehicles = [v for v in (vehicles or []) if v]
	if not vehicles:
		return {}

	logs = frappe.get_all(
		"Vehicle Handover Log",
		filters={
			"vehicle": ["in", vehicles],
			"docstatus": 1,
			"handover_start_time": ["<=", to_datetime],
			"handover_end_time": [">=", from_datetime],
		},
		fields=["vehicle", "handover_start_time", "handover_end_time", "operational_driver"],
		order_by="handover_start_time asc",
	)

	driver_ids = list({log.operational_driver for log in logs if log.operational_driver})
	driver_names = {}
	if driver_ids:
		driver_names = {
			row.name: row.employee_name
			for row in frappe.get_all(
				"Employee", filters={"name": ["in", driver_ids]}, fields=["name", "employee_name"]
			)
		}

	windows = {}
	for log in logs:
		if not log.operational_driver:
			continue

		windows.setdefault(log.vehicle, []).append(
			{
				"start": log.handover_start_time,
				"end": log.handover_end_time,
				"operational_driver": log.operational_driver,
				"driver_name": driver_names.get(log.operational_driver) or log.operational_driver,
			}
		)

	return windows


def as_time_string(value):
	"""Normalise a Time field (which reads back as a timedelta) to HH:MM:SS."""
	if isinstance(value, timedelta):
		seconds = int(value.total_seconds())
		return f"{seconds // 3600 % 24:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"

	return str(value)


def get_manifest_shift_windows(manifest):
	"""
	The shift windows a manifest's stops cover, earliest first.

	Each stop carries its shift's start_time and end_time. A night shift whose end is at
	or before its start runs into the following day, so it is extended by a day rather
	than collapsing to an empty window. Windows are de-duplicated because several stops
	normally belong to the same shift.

	Matching on the shift window rather than the pickup instant is what AC5 means by "the
	shift hours": a driver holds the vehicle for the whole shift, and a handover raised
	against an evening shift would never line up with a morning pickup time.
	"""
	schedule_date = manifest.get("schedule_date")
	if not schedule_date:
		return []

	windows = set()
	for row in manifest.get("transportation_manifest_details") or []:
		start, end = row.get("start_time"), row.get("end_time")
		if not (start and end):
			continue

		start_datetime = get_datetime(f"{schedule_date} {as_time_string(start)}")
		end_datetime = get_datetime(f"{schedule_date} {as_time_string(end)}")
		if end_datetime <= start_datetime:
			end_datetime = add_days(end_datetime, 1)

		windows.add((start_datetime, end_datetime))

	return sorted(windows)


def get_operational_driver_in_window(vehicle, from_datetime, to_datetime):
	"""
	Operational Driver from a submitted handover overlapping [from_datetime, to_datetime].

	None when no handover covers any part of the window - the caller then falls back to
	the vehicle's permanent custodian.
	"""
	if not (vehicle and from_datetime and to_datetime):
		return None

	return frappe.db.get_value(
		"Vehicle Handover Log",
		{
			"vehicle": vehicle,
			"docstatus": 1,
			"handover_start_time": ["<", to_datetime],
			"handover_end_time": [">", from_datetime],
		},
		"operational_driver",
		order_by="handover_start_time asc",
	)


def get_manifest_operational_driver(manifest, vehicle):
	"""
	Who drives this manifest: the Operational Driver of the earliest shift a submitted
	handover covers, else the vehicle's permanent custodian.

	A manifest can span more than one shift while its header holds a single driver, so the
	earliest matching shift wins. Recording the remaining shifts' drivers is left to a
	later story.
	"""
	for from_datetime, to_datetime in get_manifest_shift_windows(manifest):
		driver = get_operational_driver_in_window(vehicle, from_datetime, to_datetime)
		if driver:
			return driver

	return frappe.db.get_value("Vehicle", vehicle, "employee") if vehicle else None


def set_manifest_drivers_for_tomorrow():
	"""
	Stamp tomorrow's Transportation Manifest headers with the driver who will actually be
	behind the wheel (WI-001577).

	A submitted Vehicle Handover Log overlapping one of the manifest's shift windows names
	the Operational Driver; with no log for those hours the vehicle's permanent custodian
	stands. Runs at 12:10am for the following day's manifests.
	"""
	try:
		tomorrow = add_days(getdate(), 1)

		manifests = frappe.get_all(
			"Transportation Manifest",
			filters={"schedule_date": tomorrow, "docstatus": ["!=", 2], "vehicle_no": ["is", "set"]},
			fields=["name", "vehicle_no", "schedule_date", "driver_name"],
		)

		for manifest in manifests:
			doc = frappe.get_doc("Transportation Manifest", manifest.name)

			driver = get_manifest_operational_driver(doc.as_dict(), doc.vehicle_no)
			if driver and driver != doc.driver_name:
				doc.db_set("driver_name", driver)

		frappe.db.commit()

	except Exception:
		frappe.log_error(
			title="Error setting manifest drivers from Vehicle Handover Logs",
			message=frappe.get_traceback(),
		)
