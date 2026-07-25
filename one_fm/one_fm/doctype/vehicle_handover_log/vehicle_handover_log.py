# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime

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
