# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A saved run is redrawn on today's lane, and its stops must land on the same day."""

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
		# Rounding, not flooring: a stop landing slightly before stop one stays put.
		self.assertNotIn("Math.ceil((anchor.ms - startMs)", self.source)
		self.assertIn("Math.round((anchor.ms - startMs)", self.source)

	def test_the_shift_is_not_decided_by_the_trips_earliest_stamp(self):
		# The earliest raw timestamp is a lock lifespan, not the run's date.
		self.assertNotIn("tripShift[i.tripId] = { earliest", self.source)
