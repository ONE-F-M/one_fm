# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002160: one trip group on one vehicle is one bus run, not two.

A run that both drops off and picks up was split by direction into two pseudo-trips
whose windows overlap each other, so the seat check added the same bus to itself: a
1-passenger drop onto a bus carrying 2 of its 3 seats was refused as "Capacity
Exceeded".

The lane refuses a drop before the save ever sees it, so the canvas and the Route Plan
have to read a run the same way — otherwise the operator is stopped by a rule the plan
would have accepted, or promised a merge the save then refuses.
"""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))
ROUTE_PLAN = pathlib.Path(frappe.get_app_path(
	"one_fm", "operations", "doctype", "route_plan", "route_plan.py"
))


class TestOneTripGroupIsOneRun(FrappeTestCase):
	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_lane_groups_a_run_by_its_trip_alone(self):
		self.assertIn("const key = item.tripId || `_solo_${soloIdx++}`;", self.source)
		self.assertNotIn("`${item.tripId}::${item.direction}`", self.source)

	def test_stops_that_disagree_make_the_run_mixed(self):
		self.assertIn("runDirection(stops) {", self.source)
		self.assertIn(
			"return stops.some(s => (s.direction || 'OUTBOUND') !== first) ? 'MIXED' : first;",
			self.source,
		)

	def test_every_seat_check_reads_the_run_through_that_one_rule(self):
		# The "merge this block into that trip" action re-summed the stops by hand, so
		# it refused merges the lane and the save both accept.
		self.assertNotIn(
			"const tripLoad = targetTripItems.reduce((sum, i) => sum + (i.headcount || 0), 0);",
			self.source,
		)
		# The three places a run is weighed against the seats: the lane's own reading,
		# reassigning a journey to another vehicle, and merging a block into a trip.
		self.assertIn("t.direction = this.runDirection(t.stops);", self.source)
		self.assertIn("direction: self.runDirection(journeyItems),", self.source)
		self.assertIn("direction: self.runDirection(targetTripItems),", self.source)

	def test_the_save_reads_it_the_same_way(self):
		source = ROUTE_PLAN.read_text()

		self.assertIn("key = (row.vehicle, group)", source)
		self.assertIn("trip.direction = MIXED_DIRECTION", source)

	def test_the_leg_walk_reads_a_row_that_has_no_shipment(self):
		# A row carrying no shipment still knows its own leg. Reading only the
		# shipment called those riders outward and doubled the run's peak.
		from one_fm.operations.doctype.route_plan.route_plan import _trip_peak

		trip = frappe._dict(
			direction="MIXED",
			headcount=6,
			rows=[
				frappe._dict(direction="OUTBOUND", headcount=3, stop_index=1,
							 start_time=None, name=None, transportation_shipment=None),
				frappe._dict(direction="RETURN", headcount=3, stop_index=2,
							 start_time=None, name=None, transportation_shipment=None),
			],
		)

		self.assertEqual(_trip_peak(trip), (3, 1))

	def test_the_leg_walk_is_not_left_to_chance(self):
		# Stop order decides the answer — the same two loads read 3 or 6 depending on
		# whether the return riders board before or after the outward ones get off. The
		# child-row name is a random hash, so ordering on it alone made the check
		# non-deterministic once a run held both directions.
		self.assertIn('str(row.start_time or "")', ROUTE_PLAN.read_text())
