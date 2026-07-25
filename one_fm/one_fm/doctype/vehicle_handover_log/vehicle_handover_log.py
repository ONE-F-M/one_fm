# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

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


def get_operational_driver(vehicle, at_datetime):
	"""
	Who is driving `vehicle` at `at_datetime`.

	A submitted Vehicle Handover Log covering that moment names the Operational Driver;
	outside every handover window the vehicle falls back to its permanent custodian
	(Vehicle.employee).

	This is what makes the "keep the bus completely free" AC hold: availability is derived
	from a handover's own window only, so a log saved for next week says nothing about the
	vehicle between now and then - the days in between still resolve to the permanent
	driver and stay open for other runs.

	WI-001577 consumes this for the Transportation Schedule lanes and the manifest header.
	"""
	if not (vehicle and at_datetime):
		return None

	operational_driver = frappe.db.get_value(
		"Vehicle Handover Log",
		{
			"vehicle": vehicle,
			"docstatus": 1,
			"handover_start_time": ["<=", at_datetime],
			"handover_end_time": [">=", at_datetime],
		},
		"operational_driver",
		order_by="handover_start_time desc",
	)

	return operational_driver or frappe.db.get_value("Vehicle", vehicle, "employee")


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


def get_manifest_departure_datetime(manifest):
	"""
	When the driver takes the vehicle for a manifest: its earliest scheduled stop time on
	the schedule date. Returns None when the manifest has no timed stops to match against.
	"""
	if not manifest.get("schedule_date"):
		return None

	stop_times = [
		row.get("scheduled_time") or row.get("start_time")
		for row in manifest.get("transportation_manifest_details") or []
	]
	stop_times = [time for time in stop_times if time]
	if not stop_times:
		return None

	return get_datetime(f"{manifest['schedule_date']} {min(stop_times)}")


def set_manifest_drivers_for_tomorrow():
	"""
	Stamp tomorrow's Transportation Manifest headers with the driver who will actually be
	behind the wheel (WI-001577).

	A submitted Vehicle Handover Log covering the manifest's departure names the
	Operational Driver; with no log for those hours the vehicle's permanent custodian
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
			departure = get_manifest_departure_datetime(doc.as_dict())
			if not departure:
				continue

			driver = get_operational_driver(doc.vehicle_no, departure)
			if driver and driver != doc.driver_name:
				doc.db_set("driver_name", driver)

		frappe.db.commit()

	except Exception:
		frappe.log_error(
			title="Error setting manifest drivers from Vehicle Handover Logs",
			message=frappe.get_traceback(),
		)
