# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002160: one trip group on one vehicle is one bus run, not two.

The lane refuses a drop before the save ever sees it, so the canvas and the Route Plan
have to read a run the same way.
"""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from one_fm.patches.v15_0.mark_unflagged_mixed_trips import execute as execute_mixed_patch

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
		# The "merge into that trip" action re-summed the stops by hand.
		self.assertNotIn(
			"const tripLoad = targetTripItems.reduce((sum, i) => sum + (i.headcount || 0), 0);",
			self.source,
		)
		# The three places a run is weighed: the lane, a reassign, and a merge.
		self.assertIn("t.direction = this.runDirection(t.stops);", self.source)
		self.assertIn("direction: self.runDirection(journeyItems),", self.source)
		self.assertIn("direction: self.runDirection(targetTripItems),", self.source)

	def test_the_save_reads_it_the_same_way(self):
		source = ROUTE_PLAN.read_text()

		self.assertIn("key = (row.vehicle, group)", source)
		self.assertIn("trip.direction = MIXED_DIRECTION", source)

	def test_the_leg_walk_reads_a_row_that_has_no_shipment(self):
		# A row carrying no shipment still knows its own leg.
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
		# The child-row name is a random hash, so ordering on it alone was non-
		# deterministic once a run held both directions.
		self.assertIn('str(row.start_time or "")', ROUTE_PLAN.read_text())


class TestARunIsDrawnAsWhatItIs(FrappeTestCase):
	"""A run reading MIXED for the seat check must not still draw as an outbound one."""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_block_colour_comes_from_the_same_rule(self):
		self.assertIn("direction: this.runDirection(stops),", self.source)
		self.assertNotIn(
			"stops.some(s => s.direction === 'MIXED') ? 'MIXED' : firstItem.direction",
			self.source,
		)


class TestARefusalNamesTheRunThatTookTheSeats(FrappeTestCase):
	"""A card is placed at its own shift window, never where it was dropped, so the run
	that blocks it is often not the block the operator was aiming at.
	"""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_message_can_name_the_blocking_runs(self):
		self.assertIn("capacityMessage(headcount, vehicle, blockers) {", self.source)
		self.assertIn("Those seats are held by {0}.", self.source)

	def test_the_check_and_the_message_read_one_list(self):
		# Computed separately they would drift, and name runs the check never counted.
		self.assertIn("tripsDuringCardWindows(card, vehicleId, direction) {", self.source)
		self.assertIn(
			"return this.tripsDuringCardWindows(card, vehicleId, direction)", self.source
		)

	def test_a_logical_trip_carries_its_name(self):
		self.assertIn("tripName: item.tripName || null,", self.source)


class TestTripNamesAreNotReissued(FrappeTestCase):
	"""Removing a trip that is not the last used to hand its successor a taken name."""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_next_free_number_is_used_not_the_count(self):
		self.assertIn("while (taken.has(name(seq))) seq++;", self.source)
		self.assertNotIn("const nextSeq = existingTripIds.size + 1;", self.source)


class TestEveryMergeGoesThroughTheMergeWindow(FrappeTestCase):
	"""The picker used to chain a cross-direction stop without ever showing the modal."""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_a_transit_time_no_longer_skips_the_merge_window(self):
		self.assertIn("if (self._isMergeDrop(newCard, existingItems)) {", self.source)
		self.assertNotIn(
			"if (!presetTransitMin && self._isMergeDrop(newCard, existingItems)) {", self.source
		)

	def test_the_picker_offers_the_nearest_run_first(self):
		# Options were built in row order, so any run could be the default.
		self.assertIn("tripKeys.sort((a, b) => gapToCard(tripMap[a]) - gapToCard(tripMap[b]));", self.source)


class TestMarkUnflaggedMixedTripsPatch(FrappeTestCase):
	"""The runs merged through the trip picker before it reached merge_trip_shipments."""

	VEHICLE = "VHL-L-0022"  # 4 seats -> 3 legal passenger seats

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Vehicle", cls.VEHICLE):
			raise cls.skipTest(cls, f"Fixture vehicle {cls.VEHICLE} missing on this site")

	def _shipment(self, direction):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = "Assigned"
		doc.trip_direction = direction
		doc.headcount = 1
		doc.generation_key = frappe.generate_hash("TS-MIX", 10)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _plan(self, *legs):
		"""One run on one vehicle; each leg is (direction, shipment)."""
		group = frappe.generate_hash("RUN", 8)
		doc = frappe.new_doc("Route Plan")
		doc.title = frappe.generate_hash("RP-MIX", 8)
		doc.status = "Draft"
		doc.effective_from = today()
		for index, (direction, shipment) in enumerate(legs, start=1):
			doc.append("assignments", {
				"card_id": f"TSHIP-{shipment}",
				"transportation_shipment": shipment,
				"vehicle": self.VEHICLE,
				"direction": direction,
				"trip_group": group,
				"trip_name": group,
				"stop_index": index,
				"headcount": 1,
			})
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		return doc

	def _read(self, name):
		return frappe.db.get_value(
			"Transportation Shipment", name,
			["trip_direction", "pre_merge_trip_direction"], as_dict=True
		)

	def test_a_run_whose_stops_disagree_is_marked_mixed(self):
		out, ret = self._shipment("Outward"), self._shipment("Return")
		plan = self._plan(("OUTBOUND", out), ("RETURN", ret))

		execute_mixed_patch()

		plan.reload()
		self.assertEqual({row.direction for row in plan.assignments}, {"MIXED"})
		self.assertEqual(self._read(out).trip_direction, "Mixed")
		self.assertEqual(self._read(ret).trip_direction, "Mixed")

	def test_each_card_keeps_a_record_of_the_leg_it_was_generated_for(self):
		out, ret = self._shipment("Outward"), self._shipment("Return")
		self._plan(("OUTBOUND", out), ("RETURN", ret))

		execute_mixed_patch()

		self.assertEqual(self._read(out).pre_merge_trip_direction, "Outward")
		self.assertEqual(self._read(ret).pre_merge_trip_direction, "Return")

	def test_the_repair_is_reversible(self):
		# Without a remembered direction there is nothing to restore (WI-002071).
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			unmerge_trip_shipment,
		)

		out, ret = self._shipment("Outward"), self._shipment("Return")
		self._plan(("OUTBOUND", out), ("RETURN", ret))
		execute_mixed_patch()

		self.assertTrue(unmerge_trip_shipment(out))
		self.assertEqual(self._read(out).trip_direction, "Outward")
		self.assertIsNone(self._read(out).pre_merge_trip_direction)

	def test_a_single_direction_run_is_left_alone(self):
		# Several camps on one outbound run is not a merge.
		a, b = self._shipment("Outward"), self._shipment("Outward")
		plan = self._plan(("OUTBOUND", a), ("OUTBOUND", b))

		execute_mixed_patch()

		plan.reload()
		self.assertEqual({row.direction for row in plan.assignments}, {"OUTBOUND"})
		self.assertEqual(self._read(a).trip_direction, "Outward")
		self.assertFalse(self._read(a).pre_merge_trip_direction)

	def test_running_it_twice_does_not_overwrite_the_original_with_mixed(self):
		out, ret = self._shipment("Outward"), self._shipment("Return")
		self._plan(("OUTBOUND", out), ("RETURN", ret))

		execute_mixed_patch()
		execute_mixed_patch()

		self.assertEqual(self._read(out).pre_merge_trip_direction, "Outward")
		self.assertEqual(self._read(out).trip_direction, "Mixed")
