# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.vehicle_handover_log.vehicle_handover_log import (
	calculate_total_kilometers,
	get_handover_status,
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
