# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002578: a dropped card is timed from its SHIFT, not from where the pointer let go.

AC1 asks for the release position to seed the Trip Builder's Initial Departure Time, and
for a while it did. Testing showed that reads as a fault rather than a feature.

A 17:00 card has to REACH site by 17:00, so the bus leaves the camp at 16:40 - the arrival
anchor less buffer and transit. Releasing the card somewhere else offered a departure with
no operational meaning: a 17:00 card dropped mid-board opened on 12:34, and the itinerary
walked forward from there.

Worse, it was only half applied. ``_doPlace`` draws the block from the shift window and
never saw the release point, so the modal said 12:34 while the lane showed 16:40. They
agreed only once Confirm re-timed the blocks; cancelling left them disagreeing for good.
Reproduced against live data - TS-1090, an Outward card with start_time 17:00, whose block
persisted as 13:40Z (16:40 Kuwait) while the modal offered 12:34:12.

So the release point now decides WHICH LANE and nothing else, and the departure comes from
the same place the block does. Deviation from AC1, agreed with the requester and flagged
for the BA.

The rest of WI-002578 is unchanged and pinned below: the forward walk, the automatic round
trip, the drawer's trip window, and Edit Trip Timings on a single-stop trip.
"""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
	get_merge_preview,
)

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))

SEEDED = "WI-002578-DROP-"


def _clear():
	frappe.db.delete("Transportation Shipment", {"name": ["like", SEEDED + "%"]})


def _card(suffix, start="17:00:00", end="05:00:00", direction="Outward"):
	"""An Outward card whose shift starts at 17:00 - the case from the report."""
	doc = frappe.new_doc("Transportation Shipment")
	doc.name = SEEDED + suffix
	doc.status = "Unassigned"
	doc.trip_direction = direction
	doc.start_time = start
	doc.end_time = end
	doc.headcount = 1
	# Real links, mirrored from TS-1090 - the card this was reported on. build_itinerary
	# needs an accommodation AND a stop location to give a solo card the camp -> site ->
	# home shape; with free text it collapses to a single stop and AC7 cannot be tested.
	doc.accommodation = "ACC-08"
	doc.accommodation_name = "Mangaf 182"
	doc.stop_location = "Khairan Mall Stop Locations"
	doc.operations_site = "Foodhall khiran Mall"
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	doc.insert(ignore_permissions=True)
	return doc.name


class TestTheDepartureComesFromTheShift(FrappeTestCase):
	"""The rule, executed rather than grepped: 17:00 arrival - 5 buffer - 15 transit."""

	def setUp(self):
		_clear()
		self.addCleanup(_clear)
		self.card = _card("A")
		self.timings = {self.card: {"transit_minutes": 15, "buffer_minutes": 5}}

	def _preview(self, current_departure=None, departure=None):
		return get_merge_preview([self.card], vehicle=None, timings=self.timings,
								 departure=departure, current_departure=current_departure)

	def test_a_seventeen_hundred_card_leaves_at_sixteen_forty(self):
		self.assertEqual(self._preview()["departure_input"], "16:40:00")

	def test_the_legs_walk_forward_from_there(self):
		# AC2's arithmetic, unchanged: next = previous + transit + buffer.
		stops = self._preview()["stops"]
		self.assertEqual([s["departs"] for s in stops][:2], ["16:40", "17:00"])

	def test_the_bus_reaches_site_exactly_on_the_shift_start(self):
		# The whole point of backing off buffer + transit.
		self.assertEqual(self._preview()["stops"][0]["arrives"], "17:00")

	def test_a_longer_run_backs_off_further(self):
		self.timings[self.card] = {"transit_minutes": 30, "buffer_minutes": 15}

		self.assertEqual(self._preview()["departure_input"], "16:15:00")

	def test_a_departure_the_dispatcher_types_still_wins(self):
		# Overriding by hand must keep working - that is the field's whole purpose.
		self.assertEqual(self._preview(departure="09:00:00")["departure_input"], "09:00:00")

	def test_the_modal_opens_where_the_run_already_sits(self):
		# What the canvas now sends: the block's own start, not a release point. A run
		# already on the lane must reopen on itself so Confirm moves nothing.
		self.assertEqual(self._preview(current_departure="16:40:00")["departure_input"],
						 "16:40:00")

	def test_no_drop_position_is_needed_for_any_of_this(self):
		# The server default and the block's own time are the same number, which is what
		# makes the modal and the lane agree without anything being threaded through.
		self.assertEqual(self._preview()["departure_seconds"],
						 self._preview(current_departure="16:40:00")["departure_seconds"])


class TestTheReleasePointIsNoLongerRead(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_helper_is_gone(self):
		self.assertNotIn("dropTimeFrom", self.canvas)

	def test_nothing_carries_a_dropped_time_any_more(self):
		# One leftover parameter would put the old behaviour back on whichever path still
		# passed it, and the two paths would disagree again.
		self.assertNotIn("droppedAt", self.canvas)

	def test_both_drop_paths_place_without_a_time(self):
		self.assertIn("this.handleDrop(card, vehicle);", self.canvas)
		self.assertIn("handleDrop(card, vehicle) {", self.canvas)

	def test_the_modal_opens_on_where_the_run_sits(self):
		self.assertIn("const runStartMs = held.departure", self.canvas)
		self.assertIn("Math.min(...existingItems.map((i) => new Date(i.start).getTime()))",
					  self.canvas)

	def test_the_blocks_are_still_anchored_to_that_same_value(self):
		# AC4: the block's left edge is the departure. Unchanged - only the source of the
		# departure moved.
		self.assertIn("const anchorMs = (runStartMs === null || runStartMs === undefined",
					  self.canvas)
		self.assertIn("item.start = new Date(anchorMs + stop.departs_offset * 1000);",
					  self.canvas)


class TestWhatWasAlreadyDelivered(FrappeTestCase):
	"""The rest of WI-002578, untouched by this change."""

	def setUp(self):
		_clear()
		self.addCleanup(_clear)
		self.card = _card("B")

	def test_ac7_a_solo_card_still_gets_its_round_trip(self):
		# camp -> site -> home, built for ONE card with nothing merged into it.
		stops = get_merge_preview([self.card], vehicle=None, timings={})["stops"]
		self.assertEqual(len(stops), 3)
		self.assertEqual(stops[0]["place"], stops[2]["place"])

	def test_ac7_nobody_boards_the_ride_home(self):
		stops = get_merge_preview([self.card], vehicle=None, timings={})["stops"]
		self.assertEqual(stops[2].get("boarding_count") or 0, 0)

	def test_ac6_edit_trip_timings_works_on_a_single_stop(self):
		canvas = CANVAS.read_text()
		self.assertIn("_openMergeTripModal(null, stops, item.vehicleId)", canvas)

	def test_ac1_the_button_opens_the_trip_builder(self):
		# The one part of AC1 that stands: the assignment modal hands straight over.
		self.assertIn("primary_action_label: __('Open Trip Builder')", CANVAS.read_text())
