# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Every reader of a plan's assignments sees the standalone records.

Records written after Route Plan Assignment stopped being a child table have no parent,
parenttype or parentfield, so anything still filtering on those would silently skip them.
"""

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from one_fm.operations.doctype.route_plan.route_plan import get_plan_rows
from one_fm.operations.doctype.route_plan.test_route_plan import pin_three_passenger_seats
from one_fm.operations.doctype.route_plan_assignment.test_route_plan_assignment import (
	_child_rows,
	make_card_shipment,
	make_route_plan,
)

VEHICLE = "VHL-L-0022"


def _shipment(headcount):
	name = make_card_shipment(headcount)
	if not name:
		raise unittest.SkipTest("needs an Accommodation and a Location")
	return name


def _row(card, vehicle=VEHICLE, **values):
	return {
		"card_id": f"TSHIP-{card}", "transportation_shipment": card, "vehicle": vehicle,
		"direction": "OUTBOUND", "start_time": f"{today()}T06:00:00Z",
		"end_time": f"{today()}T07:00:00Z", **values,
	}


class TestAStandaloneRecordIsRead(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("Vehicle", VEHICLE):
			self.skipTest(f"Fixture vehicle {VEHICLE} missing on this site")
		pin_three_passenger_seats(VEHICLE)

	def test_the_traceability_matrix_finds_a_card_placed_after_the_change(self):
		from one_fm.one_fm.page.transportation_schedule import traceability_matrix as tm

		card = _shipment(headcount=2)
		plan = make_route_plan([_row(card, trip_name="S-101", headcount=2)])

		self.assertIn(card, tm._placements(plan))
		self.assertEqual(tm._vehicle_load(card)["vehicle"], VEHICLE)
		self.assertEqual(tm._vehicle_load(card)["load"], 2)

	def test_the_seat_check_sees_the_bus_the_card_is_on(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import _SeatCheck

		card = _shipment(headcount=2)
		make_route_plan([_row(card, headcount=2)])

		# Three passenger seats, two taken: one more rider fits.
		self.assertEqual(_SeatCheck().room(card, staying=2, wanted=5), 1)

	def test_the_compiler_groups_outbound_records_by_shift(self):
		from one_fm.one_fm.doctype.transportation_manifest.manifest_compiler import (
			_outbound_assignments_by_shift,
		)

		plan = make_route_plan([
			{"card_id": "C1", "vehicle": VEHICLE, "direction": "OUTBOUND", "shift": "SHIFT-A"},
			{"card_id": "C2", "vehicle": VEHICLE, "direction": "RETURN", "shift": "SHIFT-A"},
			{"card_id": "C3", "vehicle": VEHICLE, "direction": "OUTBOUND", "shift": "SHIFT-B"},
		])

		grouped = _outbound_assignments_by_shift(plan)

		self.assertEqual({shift: [r.card_id for r in rows] for shift, rows in grouped.items()},
						 {"SHIFT-A": ["C1"], "SHIFT-B": ["C3"]})


class TestTheOldPatchesRunOnRecords(FrappeTestCase):
	"""Install marks them done on a fresh site, but tests still call execute()."""

	def test_the_duplicate_trip_name_repair_renames_the_later_run(self):
		from one_fm.patches.v15_0.rename_duplicate_trip_names import execute

		plan = make_route_plan([
			{"card_id": "C1", "vehicle": "BUS-A", "direction": "OUTBOUND", "trip_group": "T1",
			 "trip_name": "S-106", "start_time": "2026-07-20T05:30:00Z", "end_time": "2026-07-20T06:05:00Z"},
			{"card_id": "C2", "vehicle": "BUS-A", "direction": "OUTBOUND", "trip_group": "T2",
			 "trip_name": "S-106", "start_time": "2026-07-20T22:00:00Z", "end_time": "2026-07-20T23:15:00Z"},
		])

		with patch("one_fm.operations.doctype.route_plan.route_plan._canvas_series", return_value={}):
			execute()

		names = {row.trip_group: row.trip_name for row in get_plan_rows(plan)}
		self.assertEqual(names, {"T1": "S-106", "T2": "S-101"})

	def test_the_series_repair_runs_without_failing(self):
		from one_fm.patches.v15_0.rename_trip_names_into_canvas_series import execute

		plan = make_route_plan([
			{"card_id": "C1", "vehicle": "V9", "direction": "OUTBOUND", "trip_group": "T1",
			 "trip_name": "S-101", "start_time": "2026-07-20T05:30:00Z", "end_time": "2026-07-20T06:30:00Z"},
		])

		with patch("one_fm.operations.doctype.route_plan.route_plan._canvas_series",
				   return_value={"V9": "S-9"}):
			execute()

		self.assertEqual([row.trip_name for row in get_plan_rows(plan)], ["S-901"])


class _Stop(Exception):
	pass


class TestTheManifestKeepsEachVehiclesOrder(FrappeTestCase):
	def test_the_rows_of_each_vehicle_come_in_the_order_they_had_before(self):
		from one_fm.one_fm.page.transportation_schedule import transportation_schedule as ts
		from one_fm.patches.v15_0 import route_plan_assignment_standalone

		if not frappe.db.has_column("Route Plan Assignment", "parent"):
			self.skipTest("this site never had Route Plan Assignment as a child table")
		plan = make_route_plan()
		names = _child_rows(plan, [
			{"card_id": "C-2", "vehicle": "V-1", "trip_group": "T1", "stop_index": 2},
			{"card_id": "C-9", "vehicle": "V-2"},
			{"card_id": "C-1", "vehicle": "V-1", "trip_group": "T1", "stop_index": 1},
			{"card_id": "C-3", "vehicle": "V-1", "trip_group": "T2", "stop_index": 1},
		])
		as_child = frappe.get_all("Route Plan Assignment", filters={"name": ["in", names]},
								  fields=["card_id", "vehicle"], order_by="idx asc")
		route_plan_assignment_standalone.execute()

		seen = []

		def capture(rows):
			seen.extend(rows)
			raise _Stop

		with patch.object(ts, "card_rows", side_effect=capture), self.assertRaises(_Stop):
			ts.get_manifest_data_for_plan(plan)

		def by_vehicle(rows):
			out = {}
			for row in rows:
				out.setdefault(row.vehicle, []).append(row.card_id)
			return out

		self.assertEqual(by_vehicle(seen), by_vehicle(as_child))
