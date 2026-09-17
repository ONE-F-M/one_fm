# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002578: a card is timed from where it was dropped.

The drop event has always carried the position on the lane and the board threw it away.
``onLaneDrop`` read only the vehicle, so a card released at 14:00 opened its trip on a
departure re-derived from the shift window - the operator picked a slot and the board
ignored it.

``dropTimeFrom`` turns the release point into a time, and that time then has to win in
TWO places or the fix is only half done:

* ``runStart`` is the clock the Trip Builder's Initial Departure Time opens on (AC1);
* ``runStartMs`` is what ``_applyMerge`` anchors the re-timed blocks to (AC4).

Setting only the first showed the dropped time in the field and then left the block
sitting where the shift window had put it.

The ACs this file does NOT cover, because they were already delivered and are pinned
elsewhere:

* AC2's forward walk is ``walk_legs`` on the server - one rule shared by the Trip
  Builder, the canvas, the Route Plan and the manifest. Browser-verified: 14:40 + 12
  buffer + 27 transit = 15:19.
* AC3/AC7's round trip comes out of ``build_itinerary`` for a single card, and AC6's
  unblocked Edit Trip Timings, both landed in WI-002539 (test_default_leg_timings).
* AC5's drawer already prints Trip Start, Trip End and the total, above the stop list.
"""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))


class TestTheDropPositionIsRead(FrappeTestCase):
	"""AC1: the release point becomes a time instead of being discarded."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_helper_exists(self):
		self.assertIn("dropTimeFrom(e) {", self.canvas)

	def test_it_measures_against_the_lane_not_the_element_under_the_pointer(self):
		# offsetX is relative to whichever child the pointer happened to be over - a grid
		# line, a wash rect - so the same drop would read as a different time depending
		# on what it landed on.
		self.assertIn("const rect = wrap.getBoundingClientRect();", self.canvas)
		self.assertIn("e.clientX - rect.left", self.canvas)
		self.assertNotIn("e.offsetX", self.canvas)

	def test_the_position_is_clamped_to_the_lane(self):
		self.assertIn("Math.min(Math.max(e.clientX - rect.left, 0), rect.width)", self.canvas)

	def test_it_scales_css_pixels_to_the_svg_coordinate_space(self):
		# The wrapper's rendered width and svgWidth are not the same number once the
		# board is zoomed, and xToTime speaks svgWidth.
		self.assertIn("this.xToTime(x * (this.svgWidth / rect.width))", self.canvas)

	def test_an_unmeasurable_drop_gives_nothing_rather_than_a_bad_time(self):
		self.assertIn("if (!rect.width) return null;", self.canvas)
		self.assertIn("return isNaN(at.getTime()) ? null : at;", self.canvas)

	def test_both_drop_paths_read_it(self):
		# The desktop drag and the tap-to-place path used on touch.
		self.assertIn("this.handleDrop(card, vehicle, this.dropTimeFrom(e));", self.canvas)
		self.assertIn("const droppedAt = this.dropTimeFrom(e);", self.canvas)


class TestTheDroppedTimeReachesTheTripBuilder(FrappeTestCase):
	"""AC1 + AC4: it has to win for the field AND for the blocks."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_it_is_threaded_all_the_way_down(self):
		for signature in (
			"handleDrop(card, vehicle, droppedAt) {",
			"placeCard(card, vehicleId, droppedAt) {",
			"_openMergeTripModal(newCard, existingItems, vehicleId, seedTimings, droppedAt) {",
		):
			self.assertIn(signature, self.canvas)

	def test_the_anchor_and_the_field_come_from_the_same_value(self):
		# runStartMs is the anchor _applyMerge re-times the blocks from, and runStart is
		# what the modal opens on. Deriving the second from the first is what keeps the
		# printed departure and the drawn block from disagreeing.
		self.assertIn("const runStartMs = droppedAt", self.canvas)
		self.assertIn("const runStart = runStartMs === null ? null : clockOf(runStartMs);",
					  self.canvas)

	def test_the_old_field_only_seeding_is_gone(self):
		self.assertNotIn("const runStart = droppedAt\n                    ? clockOf(droppedAt)",
						 self.canvas)

	def test_a_run_with_no_drop_still_opens_where_it_sits(self):
		# Reopening Edit Trip Timings passes no drop, so the stored departure - and then
		# the first block - must still be what the modal opens on.
		self.assertIn("held.departure", self.canvas)
		self.assertIn("Math.min(...existingItems.map((i) => new Date(i.start).getTime()))",
					  self.canvas)

	def test_the_blocks_are_anchored_to_it(self):
		self.assertIn("const anchorMs = (runStartMs === null || runStartMs === undefined",
					  self.canvas)
		self.assertIn("item.start = new Date(anchorMs + stop.departs_offset * 1000);",
					  self.canvas)
		self.assertIn("item.end = new Date(anchorMs + stop.arrives_offset * 1000);",
					  self.canvas)


class TestWhatWasAlreadyDelivered(FrappeTestCase):
	"""The ACs this WI shares with WI-002539, pinned so a later change cannot undo them."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_ac6_edit_trip_timings_works_on_a_single_stop(self):
		self.assertNotIn("A run needs a second stop before its legs can be timed.",
						 self.canvas)

	def test_ac7_a_solo_card_still_gets_its_round_trip(self):
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			get_merge_preview,
		)

		doc = frappe.new_doc("Transportation Shipment")
		doc.status = "Unassigned"
		doc.trip_direction = "Outward"
		doc.accommodation = "ACC-WI2578"
		doc.accommodation_name = "Mahboula Camp"
		doc.stop_location = "KTech"
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)

		stops = get_merge_preview([doc.name])["stops"]

		self.assertEqual(len(stops), 3)
		self.assertEqual(stops[0]["place"], stops[-1]["place"])
		self.assertIsNone(stops[-1]["next_stop_location"])

	def test_ac5_the_drawer_prints_the_trip_window_and_its_total(self):
		self.assertIn("Trip Timeline", self.canvas)
		self.assertIn("fmtISO(tripStartsAt())", self.canvas)
		self.assertIn("fmtISO(tripEndsAt())", self.canvas)
		self.assertIn("new Date(tripEndsAt()) - new Date(tripStartsAt())", self.canvas)

	def test_ac2_the_forward_walk_is_still_the_servers(self):
		# A second implementation in the browser is the drift the existing comments warn
		# about; the canvas lays blocks out on the offsets the walk returned.
		self.assertIn("stop.departs_offset", self.canvas)
		self.assertIn("stop.arrives_offset", self.canvas)
