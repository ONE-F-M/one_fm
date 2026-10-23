# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-003536 P1: the Employee Traceability Matrix server half.

Run with ``--skip-before-tests``. classify() and can_be_permanent() are pure, so most of
this needs no records at all.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.page.transportation_schedule.traceability_matrix import (
	MATRIX_ROLES,
	_roster_row,
	_time_text,
	can_be_permanent,
	classify,
	get_traceability_matrix,
)

ROW_KEYS = {
	"id", "name", "designation", "project", "master_shift", "roster_shift", "roster_start",
	"roster_end", "camp", "room", "is_reliever", "reliever_name", "status", "badge_text",
	"subtext", "can_be_permanent", "legs",
}


def _ctx(**overrides):
	"""An active camp resident with a Working row and nothing else - the Missing case."""
	ctx = {
		"employee_status": "Active",
		"card": None,
		"card_status": None,
		"placement": None,
		"has_in": True,
		"checked_out": False,
		"on_leave": False,
		"availabilities": ["Working"],
		"is_driver": False,
	}
	ctx.update(overrides)
	return ctx


class TestClassify(FrappeTestCase):
	def test_assigned_to_a_live_vehicle(self):
		result = classify(_ctx(
			card="TSHIP-1", card_status="Assigned",
			placement={"vehicle_label": "VHL-0005 (Coaster)", "trip_id": "S-503"},
		))
		self.assertEqual(result["status"], "Assigned")
		self.assertEqual(result["badge_text"], "VHL-0005 (Coaster) · Trip S-503")

	def test_assigned_card_with_no_placement_in_the_plan_is_still_assigned(self):
		result = classify(_ctx(card="TSHIP-1", card_status="Assigned"))
		self.assertEqual(result["status"], "Assigned")

	def test_staged_in_the_unassigned_pool(self):
		result = classify(_ctx(card="TSHIP-POOL-0001", card_status="Unassigned"))
		self.assertEqual(result["status"], "Pool")
		self.assertEqual(result["badge_text"], "Unassigned Pool · TSHIP-POOL-0001")

	def test_missing_from_card(self):
		result = classify(_ctx())
		self.assertEqual(result["status"], "Missing")
		self.assertEqual(result["badge_text"], "MISSING FROM CARD")
		self.assertEqual(result["subtext"], "Eligible, but no shipment generated")

	def test_missing_carries_a_known_reason(self):
		result = classify(_ctx(missing_reason="Relieving Ann, but no shipment generated"))
		self.assertEqual(result["status"], "Missing")
		self.assertEqual(result["subtext"], "Relieving Ann, but no shipment generated")

	def test_stale_when_inactive_employee_is_on_a_card(self):
		result = classify(_ctx(employee_status="Left", card="TSHIP-1", card_status="Assigned"))
		self.assertEqual(result["status"], "Stale")
		self.assertEqual(result["badge_text"], "STALE BLOCK DETECTED")

	def test_stale_when_rider_has_no_in_row(self):
		result = classify(_ctx(has_in=False, card="TSHIP-1", card_status="Unassigned"))
		self.assertEqual(result["status"], "Stale")

	def test_stale_when_rider_has_checked_out(self):
		result = classify(_ctx(checked_out=True, card="TSHIP-1", card_status="Assigned"))
		self.assertEqual(result["status"], "Stale")

	def test_stale_beats_assigned(self):
		result = classify(_ctx(
			employee_status="Inactive", card="TSHIP-1", card_status="Assigned",
			placement={"vehicle_label": "V", "trip_id": "1"},
		))
		self.assertEqual(result["status"], "Stale")

	def test_no_open_in_is_live_out_exempt(self):
		for ctx in (_ctx(has_in=False), _ctx(checked_out=True)):
			result = classify(ctx)
			self.assertEqual(result["status"], "Exempt")
			self.assertEqual(result["badge_text"], "Self-Commuting / Exempt")
			self.assertEqual(result["subtext"], "Live-Out")

	def test_leave_is_exempt_on_leave(self):
		result = classify(_ctx(on_leave=True))
		self.assertEqual(result["status"], "Exempt")
		self.assertEqual(result["badge_text"], "No seat needed (on leave)")

	def test_day_off_and_client_day_off_are_exempt_on_leave(self):
		for availability in ("Day Off", "Client Day Off"):
			result = classify(_ctx(availabilities=[availability]))
			self.assertEqual(result["status"], "Exempt")
			self.assertEqual(result["badge_text"], "No seat needed (on leave)")

	def test_no_working_row_is_exempt_on_leave(self):
		result = classify(_ctx(availabilities=[]))
		self.assertEqual(result["status"], "Exempt")
		self.assertEqual(result["badge_text"], "No seat needed (on leave)")

	def test_driver_is_exempt(self):
		result = classify(_ctx(is_driver=True))
		self.assertEqual(result["status"], "Exempt")


class TestCanBePermanent(FrappeTestCase):
	def _row(self, shift="SHIFT-A", availability="Working", roster_type="Basic", relieving=0):
		return {
			"shift": shift, "employee_availability": availability,
			"roster_type": roster_type, "is_relieving_schedule": relieving,
		}

	def test_true_when_the_one_working_row_matches_the_master_shift(self):
		self.assertTrue(can_be_permanent([self._row()], "SHIFT-A"))

	def test_false_when_the_shift_differs_from_the_master(self):
		self.assertFalse(can_be_permanent([self._row("SHIFT-B")], "SHIFT-A"))

	def test_false_for_a_reliever(self):
		self.assertFalse(can_be_permanent([self._row(relieving=1)], "SHIFT-A"))

	def test_false_for_over_time_only(self):
		self.assertFalse(can_be_permanent([self._row(roster_type="Over-Time")], "SHIFT-A"))

	def test_false_with_more_than_one_working_row(self):
		rows = [self._row(), self._row(roster_type="Over-Time")]
		self.assertFalse(can_be_permanent(rows, "SHIFT-A"))

	def test_false_with_no_working_row_or_no_master_shift(self):
		self.assertFalse(can_be_permanent([self._row(availability="Day Off")], "SHIFT-A"))
		self.assertFalse(can_be_permanent([self._row()], None))


class TestRosterHelpers(FrappeTestCase):
	def test_basic_working_row_is_the_rostered_shift_over_over_time(self):
		rows = [
			{"shift": "OT", "employee_availability": "Working", "roster_type": "Over-Time"},
			{"shift": "BASIC", "employee_availability": "Working", "roster_type": "Basic"},
		]
		self.assertEqual(_roster_row(rows)["shift"], "BASIC")

	def test_no_working_row_gives_none(self):
		self.assertIsNone(_roster_row([{"employee_availability": "Day Off", "roster_type": "Basic"}]))

	def test_midnight_is_a_stated_time(self):
		from datetime import timedelta

		self.assertEqual(_time_text(timedelta(0)), "00:00:00")
		self.assertEqual(_time_text(timedelta(hours=9)), "09:00:00")
		self.assertIsNone(_time_text(None))


class TestEndpoint(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_the_roles_are_the_agreed_ones(self):
		self.assertEqual(
			MATRIX_ROLES, ("Transportation Supervisor", "Transportation Manager", "System Manager")
		)

	def test_a_user_without_the_roles_is_refused(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			get_traceability_matrix()

	def test_an_authorised_user_gets_the_agreed_shape(self):
		result = get_traceability_matrix()

		self.assertNotEqual(result.get("status"), "error", result.get("message"))
		self.assertIsInstance(result["rows"], list)
		self.assertTrue(result["synced_at"])
		if result["rows"]:
			self.assertEqual(ROW_KEYS - set(result["rows"][0]), set())
