# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A saved run is redrawn on today's lane, and its stops must land on the same day.

Route Plan Assignment timestamps carry two things: the TIME is the daily trip window,
the DATE is the multi-day lock lifespan. The canvas therefore shifts every block onto
today by whole days. Two faults came out of doing that per block:

* The plan window is about thirty hours wide, so a run sitting across its edge had its
  first stop shifted three days and the rest two — a 45-minute trip redrawn as a band
  nearly a day wide, which then overlapped every other run on the lane and painted them
  Overcapacity (reported on 23/79322, trips S-1701 and S-1703).
* Reaching the window was not the same as reaching today: planStart carries a 3h margin
  before today's local midnight, so a stop whose time of day fell in that margin settled
  a day early and rendered off the visible axis.
"""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))


class TestATripComesBackInOnePiece(FrappeTestCase):
	def setUp(self):
		self.source = CANVAS.read_text()

	def test_every_block_lands_on_today_at_its_own_time_of_day(self):
		self.assertIn(
			"const todayStart = this.planStart.getTime() + (3 * 3600000);", self.source
		)
		self.assertIn(
			"const dayShift = (startMs) => -Math.floor((startMs - todayStart) / dayMs) * dayMs;",
			self.source,
		)
		self.assertIn("return { ...i, start: new Date(startMs + dayShift(startMs)) };", self.source)

	def test_a_trip_is_then_pulled_onto_one_day(self):
		self.assertIn("const tripAnchor = {};", self.source)
		self.assertIn(
			"if (anchor) startMs += Math.round((anchor.ms - startMs) / dayMs) * dayMs;",
			self.source,
		)

	def test_the_day_is_the_nearest_one_not_the_next_one(self):
		# Rounding, not flooring. The stops of one trip carry unrelated save-dates —
		# S-102's stop 3 was saved 20 days after its stop 1 — so a stop that ends up
		# slightly before stop one must stay where it is. Pushing it forward a day put
		# the run back across the whole lane, which is the fault this is fixing.
		self.assertNotIn("Math.ceil((anchor.ms - startMs)", self.source)
		self.assertIn("Math.round((anchor.ms - startMs)", self.source)

	def test_the_shift_is_not_decided_by_the_trips_earliest_stamp(self):
		# Anchoring on the earliest raw timestamp reads the lock lifespan as if it were
		# the run's date, so a trip whose stops were saved on different days is dragged
		# apart by the difference between them.
		self.assertNotIn("tripShift[i.tripId] = { earliest", self.source)


class TestTheLegsWithNoBlockAreRebasedToo(FrappeTestCase):
	"""A camp departure and a home arrival are stored stamps like any other.

	Their DATE half is a lock lifespan, and the one they inherited is whichever row of
	the run the server anchored them on - not the row the canvas draws first. Left raw
	while every block was rebased onto today, a departure stored 26 days from its own run
	put the trip block's left edge that far off the axis: 97 of 106 runs on the live plan
	were drawn up to 35,000px wide on a 1,000px lane (WI-002401).
	"""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_leg_timings_are_moved_onto_the_run_they_belong_to(self):
		self.assertIn("const ontoRun = (stamp, anchorMs) => {", self.source)
		self.assertIn("ms + Math.round((anchorMs - ms) / dayMs) * dayMs", self.source)
		self.assertIn("departure: ontoRun(held.departure, runStart[tripId]),", self.source)
		self.assertIn("arrival: ontoRun(held.arrival, runStart[tripId]),", self.source)

	def test_the_anchor_is_the_runs_own_earliest_rebased_stop(self):
		self.assertIn("if (runStart[i.tripId] === undefined || ms < runStart[i.tripId]) {",
					  self.source)

	def test_a_block_always_covers_every_stop_it_holds(self):
		# Clamped, so a stored leg timing can widen the block but never shrink it below
		# its own stops - and a garbage stamp can no longer invert it.
		self.assertIn("stated(held.departure) ?? Infinity, spanStart.getTime()", self.source)
		self.assertIn("stated(held.arrival) ?? -Infinity, spanEnd.getTime()", self.source)

	def test_the_span_is_read_over_all_stops_not_the_first_and_last_by_number(self):
		# After the rebase a stop can sit a few minutes before stop one, which gave the
		# block a negative width and drew it as the 8px minimum.
		self.assertIn("const spanStart = new Date(Math.min(", self.source)
		self.assertIn("const spanEnd = new Date(Math.max(", self.source)
		self.assertNotIn("const lastItem = stops[stops.length - 1];", self.source)


class TestRemovingAStopTakesTheStopYouPicked(FrappeTestCase):
	"""Clicking a merged block selects stop 1, whichever stop you are reading.

	So "Remove from Lane" silently took the first stop of the run while the operator was
	looking at the last one (WI-002401).
	"""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_a_stop_row_in_the_drawer_can_be_picked(self):
		self.assertIn('@click.stop="selectedItem = stop.item"', self.source)
		# It already showed which stop was selected; there was just no way to change it.
		self.assertIn("stop.item.id === selectedItem.id ? '#f97316'", self.source)

	def test_the_button_names_the_stop_it_will_take(self):
		self.assertIn("removeButtonLabel()", self.source)
		self.assertIn("__('Remove Stop {0} ({1}) from Lane'", self.source)

	def test_a_single_stop_run_keeps_the_plain_label(self):
		self.assertIn("if (!this.selectedItem || stops.length < 2) return __('Remove from Lane');",
					  self.source)
