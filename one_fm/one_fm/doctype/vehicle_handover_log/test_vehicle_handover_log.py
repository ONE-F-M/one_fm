# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime

from one_fm.one_fm.doctype.vehicle_handover_log.vehicle_handover_log import (
	calculate_total_kilometers,
	get_handover_status,
	get_handover_windows,
	get_manifest_departure_datetime,
	validate_handover_window,
	validate_odometer_readings,
)


class TestVehicleHandoverLog(FrappeTestCase):
	"""
	WI-001576 handover session rules. Exercised through the module-level functions the
	controller delegates to, so they run without Vehicle/Employee/Manifest fixtures.
	"""

	# ------------------------------------------------------------------
	# Total kilometres driven
	# ------------------------------------------------------------------

	def test_total_kilometers_is_the_odometer_delta(self):
		# AC: 150,400 out and 150,650 back logs a delta of 250 KM
		self.assertEqual(calculate_total_kilometers(150400, 150650), 250)

	def test_total_kilometers_zero_while_session_open(self):
		# No end reading yet -> nothing driven has been recorded
		self.assertEqual(calculate_total_kilometers(150400, None), 0)
		self.assertEqual(calculate_total_kilometers(150400, 0), 0)

	def test_total_kilometers_zero_when_vehicle_did_not_move(self):
		self.assertEqual(calculate_total_kilometers(150400, 150400), 0)

	def test_total_kilometers_handles_string_input(self):
		# Values arrive as strings from the form / API
		self.assertEqual(calculate_total_kilometers("150400", "150650"), 250)

	# ------------------------------------------------------------------
	# Odometer validation
	# ------------------------------------------------------------------

	def test_odometer_end_below_start_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			validate_odometer_readings(150400, 150200, session_closed=True)

	def test_open_session_skips_odometer_check(self):
		# Start reading only, session still running -> no error despite end reading 0
		validate_odometer_readings(150400, 0, session_closed=False)
		validate_odometer_readings(150400, None, session_closed=False)

	def test_closing_a_session_without_an_end_reading_is_blocked(self):
		# An untouched Int reads as 0, which is below the start reading
		with self.assertRaises(frappe.ValidationError):
			validate_odometer_readings(150400, 0, session_closed=True)

	def test_equal_odometer_readings_accepted(self):
		validate_odometer_readings(150400, 150400, session_closed=True)

	# ------------------------------------------------------------------
	# Handover window
	# ------------------------------------------------------------------

	def test_end_time_before_start_time_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			validate_handover_window("2026-07-14 06:00:00", "2026-07-14 05:00:00")

	def test_end_time_equal_to_start_time_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			validate_handover_window("2026-07-14 06:00:00", "2026-07-14 06:00:00")

	def test_overnight_handover_window_accepted(self):
		validate_handover_window("2026-07-14 18:00:00", "2026-07-15 04:00:00")

	def test_open_session_window_accepted(self):
		# Start time recorded, end time still blank
		validate_handover_window("2026-07-14 06:00:00", None)

	# ------------------------------------------------------------------
	# Status lifecycle
	# ------------------------------------------------------------------

	def test_saved_session_is_active(self):
		self.assertEqual(get_handover_status(0), "Active")

	def test_submitted_session_is_completed(self):
		# AC: on submit "the record updates to Completed"
		self.assertEqual(get_handover_status(1), "Completed")

	def test_cancelled_session_is_cancelled(self):
		self.assertEqual(get_handover_status(2), "Cancelled")


class TestManifestDepartureDatetime(FrappeTestCase):
	"""
	WI-001577: the instant the 12:10am job matches a handover log against, taken from the
	manifest's earliest scheduled stop.
	"""

	def test_earliest_scheduled_time_wins(self):
		manifest = {
			"schedule_date": "2026-07-26",
			"transportation_manifest_details": [
				{"scheduled_time": "14:30:00"},
				{"scheduled_time": "05:45:00"},
				{"scheduled_time": "09:15:00"},
			],
		}
		self.assertEqual(
			get_manifest_departure_datetime(manifest), get_datetime("2026-07-26 05:45:00")
		)

	def test_falls_back_to_start_time_when_unscheduled(self):
		# Rows compiled without a scheduled_time still carry the shift's start_time.
		manifest = {
			"schedule_date": "2026-07-26",
			"transportation_manifest_details": [{"scheduled_time": None, "start_time": "06:00:00"}],
		}
		self.assertEqual(
			get_manifest_departure_datetime(manifest), get_datetime("2026-07-26 06:00:00")
		)

	def test_no_timed_stops_returns_none(self):
		# Nothing to match a handover window against - the job leaves the header alone
		# rather than guessing, so the permanent driver from fetch_from stands.
		for details in ([], [{"scheduled_time": None, "start_time": None}]):
			manifest = {"schedule_date": "2026-07-26", "transportation_manifest_details": details}
			self.assertIsNone(get_manifest_departure_datetime(manifest))

	def test_no_schedule_date_returns_none(self):
		manifest = {
			"schedule_date": None,
			"transportation_manifest_details": [{"scheduled_time": "06:00:00"}],
		}
		self.assertIsNone(get_manifest_departure_datetime(manifest))


class TestHandoverWindows(FrappeTestCase):
	def test_no_vehicles_skips_the_query(self):
		# Guards the canvas payload: an empty lane list must not build a query with an
		# empty IN clause.
		self.assertEqual(get_handover_windows([], "2026-07-25 00:00:00", "2026-07-25 23:59:59"), {})
		self.assertEqual(
			get_handover_windows([None], "2026-07-25 00:00:00", "2026-07-25 23:59:59"), {}
		)
