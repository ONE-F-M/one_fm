# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The seat check reads the shipments, and does not invent a multi-day lock.

The reported block: a dispatcher could not add one more guard to the 09:09 Eureka run
on VHL-L-0019 (a 22-seat Coaster). The board's own sidebar showed the trip carrying 21,
so a seat was free, but the save refused with "carries 23 passengers but the vehicle
takes 22". One of the four stops, TS-0345, had lost an employee since the card was
dropped: the shipment held 6, the frozen assignment row still held 7. The board reads
the shipment and the save read the row, so the two disagreed by exactly the seat the
dispatcher was trying to use.

The same staleness runs the other way and matters more - two stops of the neighbouring
S-1301 run were storing 1 and 2 against live counts of 2 and 3, so that bus was being
validated as 19 when it really carried 21.

Only the count is touched here. Which trips are judged to share the bus, the leg walk
for a merged run, and the seat limits themselves all still decide exactly what they
decided before - they are simply handed the numbers the board is showing.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

import one_fm.operations.doctype.route_plan.route_plan as mod
from one_fm.operations.doctype.route_plan.route_plan import (
	MIXED_DIRECTION,
	_trip_peak,
	row_headcount,
)


def _row(shipment=None, headcount=0, **kwargs):
	return frappe._dict(transportation_shipment=shipment, headcount=headcount, **kwargs)


class TestAStopIsCountedByItsShipment(FrappeTestCase):
	def test_the_shipment_outranks_the_rows_frozen_copy(self):
		# TS-0345 from the report: the row still says 7, the shipment says 6.
		self.assertEqual(row_headcount(_row("TS-0345", 7), {"TS-0345": 6}), 6)

	def test_a_row_that_under_counts_is_corrected_too(self):
		# S-1301's stops, which were validating a 21-passenger bus as 19.
		self.assertEqual(row_headcount(_row("TS-0297", 2), {"TS-0297": 3}), 3)

	def test_a_shipment_that_carries_nobody_is_an_answer_not_a_gap(self):
		# 0 is a real count; falling back here would resurrect the stale row.
		self.assertEqual(row_headcount(_row("TS-A", 4), {"TS-A": 0}), 0)

	def test_a_deleted_shipment_leaves_the_rows_snapshot_standing(self):
		# The stop must not silently drop out of the sum because its card is gone.
		self.assertEqual(row_headcount(_row("TS-GONE", 5), {"TS-A": 1}), 5)

	def test_a_row_carrying_no_shipment_keeps_its_own_count(self):
		self.assertEqual(row_headcount(_row(None, 3), {}), 3)


class TestTheTripSumsWhatTheBoardShows(FrappeTestCase):
	"""The Eureka run, end to end: stored 2+7+5+8 = 22, live 2+6+5+8 = 21."""

	STOPS = [("TS-0371", 2, 2), ("TS-0345", 7, 6), ("TS-0381", 5, 5), ("TS-0081", 8, 8)]

	def _plan(self):
		plan = frappe.new_doc("Route Plan")
		plan.assignments = []
		for index, (shipment, stored, _live) in enumerate(self.STOPS, start=1):
			plan.append("assignments", {
				"transportation_shipment": shipment,
				"vehicle": "VHL-L-0019",
				"direction": "OUTBOUND",
				"trip_group": "TRIP_VHL-L-0019_6w51vagg",
				"stop_index": index,
				"headcount": stored,
			})
		return plan

	def _trips(self, plan, live):
		real = mod.live_headcounts
		mod.live_headcounts = lambda rows: live
		try:
			return plan._logical_trips()
		finally:
			mod.live_headcounts = real

	def test_the_run_is_weighed_at_what_it_actually_carries(self):
		live = {shipment: count for shipment, _stored, count in self.STOPS}
		(trip,) = self._trips(self._plan(), live)

		self.assertEqual(trip.headcount, 21)
		self.assertEqual(trip.occupancy, 21)

	def test_the_last_free_seat_on_the_coaster_is_usable(self):
		# 21 aboard against 22 seats: adding the guard is a 22-passenger run and fits.
		# On the frozen rows this same save was refused as 23.
		live = {shipment: count for shipment, _stored, count in self.STOPS}
		live["TS-0081"] = 9

		(trip,) = self._trips(self._plan(), live)

		self.assertEqual(trip.occupancy, 22)

	def test_an_overloaded_bus_is_still_refused(self):
		# The fix must not turn the check into a rubber stamp.
		live = {shipment: count for shipment, _stored, count in self.STOPS}
		live["TS-0081"] = 10

		(trip,) = self._trips(self._plan(), live)

		self.assertEqual(trip.occupancy, 23)

	def test_a_stale_row_can_no_longer_hide_an_overload(self):
		# S-1301's failure mode: rows summing to 19 on a bus really carrying 21.
		live = {shipment: count for shipment, _stored, count in self.STOPS}
		live["TS-0371"] = 4

		(trip,) = self._trips(self._plan(), live)

		self.assertEqual(trip.headcount, 23)


class TestTheLegWalkReadsTheSameNumbers(FrappeTestCase):
	"""A merged run is walked stop by stop, so it has to read the live counts too."""

	def _trip(self, live, directions):
		self._directions = directions
		del live
		return frappe._dict(
			key=("V-1", "MIX-test"),
			vehicle="V-1",
			direction=MIXED_DIRECTION,
			headcount=20,
			rows=[
				_row("TS-A", 10, direction="OUTBOUND", stop_index=1, start_time=None, name=None),
				_row("TS-B", 10, direction="RETURN", stop_index=2, start_time=None, name=None),
			],
		)

	def _peak(self, trip, live):
		real_dirs, real_live = mod._shipment_directions, mod.live_headcounts
		mod._shipment_directions = lambda names: self._directions
		mod.live_headcounts = lambda rows: live
		try:
			return _trip_peak(trip)
		finally:
			mod._shipment_directions, mod.live_headcounts = real_dirs, real_live

	def test_a_leg_is_measured_at_the_live_count(self):
		live = {"TS-A": 6, "TS-B": 10}
		trip = self._trip(live, {"TS-A": "OUTBOUND", "TS-B": "RETURN"})

		self.assertEqual(self._peak(trip, live), (10, 2))

	def test_a_trip_whose_cards_are_gone_still_walks_its_rows(self):
		# Nothing to read the counts off, so the rows' own snapshots stand rather than
		# the stops silently dropping out of the walk.
		trip = self._trip({}, {"TS-A": "OUTBOUND", "TS-B": "RETURN"})

		self.assertEqual(self._peak(trip, {}), (10, 1))


class TestTheConcurrencyCheckStillHolds(FrappeTestCase):
	"""Reading live counts must not soften the overlapping-trips check."""

	def _trip(self, group, headcount, start, end):
		return frappe._dict(
			key=("VHL-L-0023", group), vehicle="VHL-L-0023", direction="OUTBOUND",
			headcount=headcount, occupancy=headcount, start=start, end=end,
			live_from=None, live_to=None, rows=[],
		)

	def test_the_double_booked_coaster_is_still_caught(self):
		# S-701 (20 aboard, 04:20-05:35) beside S-1602 (2 aboard, 04:20-05:00).
		trips = [
			self._trip("A", 20, 4 * 3600 + 20 * 60, 5 * 3600 + 35 * 60),
			self._trip("B", 2, 4 * 3600 + 20 * 60, 5 * 3600),
		]

		self.assertEqual(mod._peak_concurrent_headcount(trips), 22)

	def test_a_run_that_has_finished_does_not_block_the_next(self):
		trips = [
			self._trip("A", 20, 4 * 3600 + 20 * 60, 5 * 3600 + 35 * 60),
			self._trip("B", 7, 6 * 3600 + 45 * 60, 7 * 3600 + 35 * 60),
		]

		self.assertEqual(mod._peak_concurrent_headcount(trips), 20)
