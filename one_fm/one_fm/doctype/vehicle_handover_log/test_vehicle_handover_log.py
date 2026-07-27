# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from datetime import timedelta

from frappe.utils import get_datetime

from one_fm.one_fm.doctype.vehicle_handover_log.vehicle_handover_log import (
	calculate_total_kilometers,
	get_handover_status,
	as_time_string,
	get_handover_windows,
	get_manifest_shift_windows,
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


class TestManifestShiftWindows(FrappeTestCase):
	"""
	WI-001577 AC5: the job matches a handover against the manifest's SHIFT hours, not the
	pickup instant. A handover raised for an evening shift never lines up with a morning
	pickup time, which is how a real submitted handover came to be ignored.
	"""

	def _manifest(self, *stops, schedule_date="2026-07-28"):
		return {
			"schedule_date": schedule_date,
			"transportation_manifest_details": list(stops),
		}

	def test_shift_window_comes_from_start_and_end_time(self):
		manifest = self._manifest({"start_time": "10:00:00", "end_time": "23:00:00"})
		self.assertEqual(
			get_manifest_shift_windows(manifest),
			[(get_datetime("2026-07-28 10:00:00"), get_datetime("2026-07-28 23:00:00"))],
		)

	def test_night_shift_crosses_midnight(self):
		# 18:00 -> 06:00 must run into the next day, not collapse to an empty window.
		manifest = self._manifest({"start_time": "18:00:00", "end_time": "06:00:00"})
		self.assertEqual(
			get_manifest_shift_windows(manifest),
			[(get_datetime("2026-07-28 18:00:00"), get_datetime("2026-07-29 06:00:00"))],
		)

	def test_windows_are_deduplicated_and_ordered(self):
		# Several stops normally share one shift; the header needs each window once,
		# earliest first, because the earliest match wins.
		manifest = self._manifest(
			{"start_time": "18:00:00", "end_time": "06:00:00"},
			{"start_time": "10:00:00", "end_time": "23:00:00"},
			{"start_time": "10:00:00", "end_time": "23:00:00"},
		)
		windows = get_manifest_shift_windows(manifest)

		self.assertEqual(len(windows), 2)
		self.assertEqual(windows[0][0], get_datetime("2026-07-28 10:00:00"))
		self.assertEqual(windows[1][0], get_datetime("2026-07-28 18:00:00"))

	def test_time_fields_read_back_as_timedelta(self):
		# Child Time fields come back as timedelta, and str() drops the leading zero on
		# single-digit hours ("6:00:00"), so they are normalised before parsing.
		self.assertEqual(as_time_string(timedelta(seconds=21600)), "06:00:00")
		self.assertEqual(as_time_string(timedelta(seconds=82800)), "23:00:00")

		manifest = self._manifest(
			{"start_time": timedelta(seconds=64800), "end_time": timedelta(seconds=21600)}
		)
		self.assertEqual(
			get_manifest_shift_windows(manifest),
			[(get_datetime("2026-07-28 18:00:00"), get_datetime("2026-07-29 06:00:00"))],
		)

	def test_stops_without_shift_hours_are_skipped(self):
		manifest = self._manifest(
			{"start_time": None, "end_time": None},
			{"start_time": "10:00:00", "end_time": None},
		)
		self.assertEqual(get_manifest_shift_windows(manifest), [])

	def test_no_schedule_date_yields_no_windows(self):
		# Nothing to match against; the job leaves the header alone rather than guessing.
		self.assertEqual(
			get_manifest_shift_windows(
				{"schedule_date": None, "transportation_manifest_details": [
					{"start_time": "10:00:00", "end_time": "23:00:00"}
				]}
			),
			[],
		)


class TestHandoverWindows(FrappeTestCase):
	def test_no_vehicles_skips_the_query(self):
		# Guards the canvas payload: an empty lane list must not build a query with an
		# empty IN clause.
		self.assertEqual(get_handover_windows([], "2026-07-25 00:00:00", "2026-07-25 23:59:59"), {})
		self.assertEqual(
			get_handover_windows([None], "2026-07-25 00:00:00", "2026-07-25 23:59:59"), {}
		)
