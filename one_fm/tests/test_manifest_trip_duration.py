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
	_trip_clock_spans,
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


class TestTripTimeIsEachRunEndToEnd(FrappeTestCase):
	"""AC1, checked against multiple vehicles as the criterion asks.

	Trip Time is each RUN from its departure to its final arrival, added up. Summing the
	assignment ROWS instead counted a shared stop twice: a merged run sets down and picks
	up at the same place in the same minute, so it holds two rows over one window.

	VHL-L-0004 is the case reported - its rows add to 12h22 where its seven runs span
	12h03, and the header then disagreed with the per-trip breakdown printed right under
	it. Row-summing also dropped the camp and home legs, so the figure was wrong in both
	directions at once and only looked plausible because the errors partly cancelled.
	"""

	def _spans(self, card_rows, leg_rows):
		"""The helper answers per trip group now; these tests care about the values."""
		return sorted(_trip_clock_spans(card_rows, leg_rows).values())

	def _rows(self, *windows):
		"""(trip_group, start clock, end clock) -> rows shaped like assignments."""
		return [
			frappe._dict(trip_group=group, start_time=f"2026-09-20 {start}:00",
						 end_time=f"2026-09-20 {end}:00")
			for group, start, end in windows
		]

	def test_one_run_is_its_own_span(self):
		spans = self._spans(self._rows(("T1", "04:50", "05:59")), [])

		self.assertEqual(spans, [69 * 60])

	def test_a_shared_stop_is_not_counted_twice(self):
		# The bug: two cards, one window. It is one run of 17 minutes, not two of 17.
		spans = self._spans(
			self._rows(("T1", "02:15", "02:32"), ("T1", "02:15", "02:32")), []
		)

		self.assertEqual(spans, [17 * 60])

	def test_the_camp_and_home_legs_are_inside_the_run(self):
		# The bus leaves the camp before its first drop and is not done until it is back.
		spans = self._spans(
			self._rows(("T1", "05:00", "05:30")),
			self._rows(("T1", "04:50", "05:00"), ("T1", "05:30", "05:59")),
		)

		self.assertEqual(spans, [69 * 60])

	def test_separate_runs_are_separate_spans(self):
		spans = self._spans(
			self._rows(("T1", "04:50", "05:59"), ("T2", "06:00", "08:06")), []
		)

		self.assertEqual(spans, sorted([69 * 60, 126 * 60]))

	def test_the_gap_between_runs_is_not_driving_time(self):
		# 04:50-05:59 then 06:00-08:06 is 3h15m of running, not the 3h16m between the
		# two ends - the bus is parked in between and Total Time is where that shows.
		spans = self._spans(
			self._rows(("T1", "04:50", "05:59"), ("T2", "06:00", "08:06")), []
		)

		self.assertEqual(sum(spans), (69 + 126) * 60)

	def test_a_row_with_no_group_is_a_run_of_its_own(self):
		spans = self._spans(
			self._rows((None, "04:50", "05:00"), (None, "06:00", "06:20")), []
		)

		self.assertEqual(spans, sorted([10 * 60, 20 * 60]))

	def test_a_run_crossing_midnight_reads_as_the_hours_it_is(self):
		spans = self._spans(self._rows(("T1", "22:40", "00:30")), [])

		self.assertEqual(spans, [110 * 60])

	def test_a_row_with_no_start_is_skipped_rather_than_zeroed(self):
		rows = self._rows(("T1", "04:50", "05:59"))
		rows.append(frappe._dict(trip_group="T1", start_time=None, end_time=None))

		self.assertEqual(self._spans(rows, []), [69 * 60])

	def test_the_reported_vehicle_adds_up(self):
		# Seven runs on VHL-L-0004, by the clock: 69 + 126 + 95 + 50 + 172 + 120 + 91.
		spans = self._spans(self._rows(
			("S-101", "04:50", "05:59"), ("S-102", "06:00", "08:06"),
			("S-103", "08:20", "09:55"), ("S-104", "10:00", "10:50"),
			("S-105", "13:00", "15:52"), ("S-106", "18:00", "20:00"),
			("S-107", "21:10", "22:41"),
		), [])

		self.assertEqual(sum(spans) // 60, 723)
		self.assertEqual((sum(spans) // 3600, (sum(spans) % 3600) // 60), (12, 3))

	def test_driving_can_never_exceed_the_shift_it_happens_in(self):
		# The invariant that would have caught this: eight hours of driving inside a
		# two-hour shift is what WI-002614 was reported for.
		windows = (("T1", "04:50", "05:59"), ("T2", "06:00", "08:06"))
		spans = self._spans(self._rows(*windows), [])
		shift = _clock_gap("2026-09-20 04:50:00", "2026-09-20 08:06:00")

		self.assertLessEqual(sum(spans), shift)


class TestTheBadgeAndItsBreakdownCannotDrift(FrappeTestCase):
	"""AC2's breakdown itemises AC1's badge, so it must print the same seconds.

	They were measured twice and disagreed in two ways at once:

	* the page reads the clock in Asia/Kuwait where the server reads it in UTC, so a run
	  from 22:40 to 00:30 crossed midnight for one of them and not the other - VHL-S-0010
	  read 22h30m for a trip of 1h50m;
	* a run whose last stop ENDS after the bus is recorded home is longer than its two
	  ends suggest. VHL-L-0012's S-603 reaches 18:00 against an arrival of 17:50, which
	  only the rows can tell you - 6h00m against the badge's 6h10m.

	The server now hands each run its own span and the page prints it.
	"""

	def test_the_helper_answers_per_run(self):
		spans = _trip_clock_spans(
			[frappe._dict(trip_group="T1", start_time="2026-09-20 04:50:00",
						  end_time="2026-09-20 05:59:00"),
			 frappe._dict(trip_group="T2", start_time="2026-09-20 06:00:00",
						  end_time="2026-09-20 08:06:00")], [])

		self.assertEqual(spans, {"T1": 69 * 60, "T2": 126 * 60})

	def test_the_badge_is_the_sum_of_those_spans(self):
		spans = _trip_clock_spans(
			[frappe._dict(trip_group="T1", start_time="2026-09-20 04:50:00",
						  end_time="2026-09-20 05:59:00"),
			 frappe._dict(trip_group="T2", start_time="2026-09-20 06:00:00",
						  end_time="2026-09-20 08:06:00")], [])

		self.assertEqual(sum(spans.values()), 195 * 60)

	def test_each_run_is_handed_its_span(self):
		server = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_schedule",
			"transportation_schedule.py"))
		self.assertIn('held["span_seconds"] = trip_spans.get(group_key, 0)', server)

	def test_the_page_prints_the_span_it_was_given(self):
		page = SHEET.read_text()
		self.assertIn("let length = legs.span_seconds;", page)

	def test_the_page_still_has_a_fallback(self):
		# A run the server sent no span for must still draw, not vanish from the strip.
		page = SHEET.read_text()
		tail = page.split("let length = legs.span_seconds;", 1)[1][:400]
		self.assertIn("length === null || length === undefined", tail)
		self.assertIn("length += 24 * 3600", tail)

	def test_a_run_a_row_outlasts_is_measured_by_the_row(self):
		# S-603: the bus is recorded home at 17:50 but a stop runs to 18:00.
		spans = _trip_clock_spans([
			frappe._dict(trip_group="S-603", start_time="2026-09-20 15:30:00",
						 end_time="2026-09-20 17:30:00"),
			frappe._dict(trip_group="S-603", start_time="2026-09-20 17:40:00",
						 end_time="2026-09-20 18:00:00"),
		], [
			frappe._dict(trip_group="S-603", start_time="2026-09-20 17:50:00",
						 end_time=None),
		])

		self.assertEqual(spans["S-603"], 150 * 60)
