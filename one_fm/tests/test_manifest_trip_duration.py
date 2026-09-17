# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002545: the manifest's trip duration, and the navigation around it.

AC1 asks for the Active Trip duration to be CHECKED against several vehicles rather than
changed. Checking it found a real defect.

``r_s``/``r_e`` - the route's two ends - were picked with ``min()``/``max()`` over the ISO
strings. Those stamps carry two different things: the TIME is the daily trip window, the
DATE is the multi-day lock's lifespan (TR-8). Sorting them whole therefore sorts by the
LOCK, not by when the bus runs, so a vehicle whose rows carry different lock dates had its
span measured between two unrelated days and then reduced ``% 86400`` into an arbitrary
remainder. WI-002614 fixed exactly this mistake on the manifest page; this is its
server-side twin.

What that looked like on the live board, before and after:

    vehicle       Total Time  Trip Time      Total Time  Trip Time
    VHL-L-0010    1h 40m      8h 7m    ->    19h 23m     8h 7m
    VHL-L-0007    3h 55m      3h 30m   ->    14h 55m     3h 30m

A bus driving eight hours inside a one-hour-forty shift is not a rounding problem. After
the fix, all eight vehicles checked report Total >= Trip.

AC2-AC5 are the navigation around that number: a breakdown of what makes it up, pills to
jump between runs, and the shift drawn as a bar. All three are measured from ONE pass over
the trips, because a run that reads 2h05m in the tooltip and draws a different width on
the strip is worse than not drawing it at all.
"""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	_clock_gap,
	_clock_seconds,
	_earliest_by_clock,
	_latest_by_clock,
)

SHEET = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_manifest_page",
	"transportation_manifest_page.js"
))

# Two stamps whose CLOCK order is the opposite of their DATE order - the shape that
# produced the defect. The bus runs 04:00 to 23:23; the dates are lock lifespans.
LATE_ON_AN_EARLY_DAY = "2026-08-18 23:23:00"
EARLY_ON_A_LATE_DAY = "2026-08-30 04:00:00"


class TestTheRouteSpanIsReadOffTheClock(FrappeTestCase):
	"""AC1: the defect the check found."""

	def test_the_clock_is_read_without_the_date(self):
		self.assertEqual(_clock_seconds("2026-08-30 04:00:00"), 4 * 3600)
		self.assertEqual(_clock_seconds("2026-08-18 23:23:00"), 23 * 3600 + 23 * 60)

	def test_a_missing_or_unparseable_stamp_is_not_a_time(self):
		self.assertIsNone(_clock_seconds(""))
		self.assertIsNone(_clock_seconds(None))
		self.assertIsNone(_clock_seconds("not a date"))

	def test_the_earliest_is_the_earliest_clock_not_the_earliest_date(self):
		# min() on the strings picks the 18th; the bus starts at 04:00 on the 30th.
		self.assertEqual(
			_earliest_by_clock([LATE_ON_AN_EARLY_DAY, EARLY_ON_A_LATE_DAY]),
			EARLY_ON_A_LATE_DAY,
		)

	def test_the_latest_is_the_latest_clock_not_the_latest_date(self):
		self.assertEqual(
			_latest_by_clock([LATE_ON_AN_EARLY_DAY, EARLY_ON_A_LATE_DAY]),
			LATE_ON_AN_EARLY_DAY,
		)

	def test_the_span_between_them_is_the_working_day(self):
		# The defect: (18th 23:23 -> 30th 04:00) % 86400 == 4h37m, reported as the whole
		# shift. Read off the clock it is the 19h23m the board now shows.
		span = _clock_gap(
			_earliest_by_clock([LATE_ON_AN_EARLY_DAY, EARLY_ON_A_LATE_DAY]),
			_latest_by_clock([LATE_ON_AN_EARLY_DAY, EARLY_ON_A_LATE_DAY]),
		)
		self.assertEqual(span, 19 * 3600 + 23 * 60)

	def test_a_run_across_midnight_wraps_instead_of_going_negative(self):
		self.assertEqual(_clock_gap("2026-08-30 23:40:00", "2026-08-31 00:20:00"), 40 * 60)

	def test_a_gap_can_never_reach_a_full_day(self):
		for start in range(0, 86400, 3607):
			for end in range(0, 86400, 3607):
				a = f"2026-08-30 {start // 3600:02d}:{(start % 3600) // 60:02d}:00"
				b = f"2026-08-31 {end // 3600:02d}:{(end % 3600) // 60:02d}:00"
				self.assertLess(_clock_gap(a, b), 86400)

	def test_empty_input_is_handled_rather_than_throwing(self):
		self.assertEqual(_earliest_by_clock([]), "")
		self.assertEqual(_latest_by_clock([None, ""]), "")
		self.assertEqual(_clock_gap(None, "2026-08-30 04:00:00"), 0)


class TestTheBreakdownAndTheStripAgree(FrappeTestCase):
	"""AC2, AC4, AC5: three views, one measurement."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.sheet = SHEET.read_text()

	def test_every_run_is_measured_once(self):
		self.assertIn("const tripSpans = allTrips.map((trip, i) => {", self.sheet)

	def test_the_spans_are_time_of_day_like_everything_else_on_this_page(self):
		span = self.sheet.split("const tripSpans = allTrips.map", 1)[1].split("}).filter", 1)[0]
		self.assertIn("secondsOfDay(st.time)", span)
		self.assertIn("if (length < 0) length += 24 * 3600;", span)

	def test_the_badge_can_be_taken_apart(self):
		self.assertIn('class="mfst-stat-box mfst-stat-trip-time" title="${escHtml(breakdown)}"',
					  self.sheet)
		self.assertIn("(${lengthOf(t.length)})", self.sheet)

	def test_the_strip_is_positioned_in_percentages(self):
		# Percentages need no measured width, so the bar is right on first paint and
		# stays right when the panel is resized.
		self.assertIn("const pct = (sec) => shiftSpan ? ((sec - spanStart) / shiftSpan) * 100 : 0;",
					  self.sheet)

	def test_driving_and_waiting_are_different_segments(self):
		self.assertIn("mfst-timeline-drive", self.sheet)
		self.assertIn("mfst-timeline-idle", self.sheet)

	def test_a_gap_between_runs_becomes_a_waiting_segment(self):
		self.assertIn("if (prev && t.start > prev.end) {", self.sheet)

	def test_both_segment_kinds_name_themselves_on_hover(self):
		# AC5's two wordings, exactly.
		self.assertIn("Driving Segment: ${escHtml(t.label", self.sheet)
		self.assertIn("Waiting Segment: Rest Time |", self.sheet)

	def test_a_zero_width_run_is_still_visible(self):
		# A single-stop run has no span; drawn at 0% it would vanish from the strip.
		self.assertIn("Math.max(0.6, pct(t.end) - pct(t.start))", self.sheet)


class TestJumpingBetweenTrips(FrappeTestCase):
	"""AC3."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.sheet = SHEET.read_text()

	def test_there_is_a_pill_per_run(self):
		self.assertIn('class="mfst-jump-pill"', self.sheet)
		self.assertIn('data-trip-index="${i}"', self.sheet)

	def test_the_bar_is_only_drawn_when_there_is_somewhere_to_jump(self):
		self.assertIn("const jumpBar = tripSpans.length > 1 ?", self.sheet)

	def test_every_trip_block_is_a_target(self):
		self.assertIn('<div class="mfst-trip-group ${dirClass}" data-trip-index="${ti}">',
					  self.sheet)

	def test_the_pill_scrolls_smoothly_to_its_block(self):
		self.assertIn('target.scrollIntoView({ behavior: "smooth", block: "start" });',
					  self.sheet)

	def test_the_handler_is_delegated_so_it_survives_a_re_render(self):
		# Bound to the pills directly it would die with the first tab change.
		self.assertIn('$container.on("click", ".mfst-jump-pill", function () {', self.sheet)

	def test_the_bar_stays_reachable_while_reading_a_trip(self):
		self.assertIn(".mfst-jump-bar {", self.sheet)
		bar = self.sheet.split(".mfst-jump-bar {", 1)[1].split("}", 1)[0]
		self.assertIn("position: sticky;", bar)
