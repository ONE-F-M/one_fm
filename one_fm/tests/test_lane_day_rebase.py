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
