# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002614: the manifest's clock arithmetic, and the one field it was doing it on.

A Route Plan Assignment's ``start_time``/``end_time`` carry two different things: the
TIME is the daily trip window, the DATE is the multi-day vehicle lock's lifespan (TR-8).
Two stops of a single run therefore routinely hold unrelated dates - they are stamped
when the lock is set, not when the bus drives.

The manifest was subtracting those timestamps whole, which is how one run produced both
symptoms in the report:

* "+11 DAY", "+12 DAY", "+27 DAY" badges on an intraday run (AC2) - a date difference
  rendered as a day offset.
* A 24-hour drive between two stops twenty minutes apart (AC3) - the same difference
  reaching ``fmtDuration``, which clamps anything past a day to a flat "24h".

Both now read the time of day and nothing else, in Asia/Kuwait, which is the clock every
time on the page is printed in. The fix is in ``secondsOfDay`` alone; these tests walk
the same arithmetic in Python so a change to either reader is caught.
"""

import json
import pathlib
import re
import shutil
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

SHEET = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_manifest_page",
	"transportation_manifest_page.js"
))

DAY = 24 * 3600


def day_offset(from_sec, to_sec):
	"""The JS rule, in Python: a leg crosses midnight when it lands earlier on the clock."""
	if from_sec is None or to_sec is None:
		return 0
	return 1 if to_sec < from_sec else 0


def clock_gap(from_sec, to_sec):
	"""The JS fallback, in Python: the clock gap, wrapped at midnight."""
	if from_sec is None or to_sec is None:
		return 0
	gap = to_sec - from_sec
	if gap < 0:
		gap += DAY
	return max(0, gap)


def at(hh, mm=0):
	return hh * 3600 + mm * 60


class TestTheRolloverBadge(FrappeTestCase):
	"""AC2: +1 DAY, only for a leg that really crosses 00:00."""

	def test_an_intraday_run_is_never_badged(self):
		# The report's own example: 14:00 -> 16:25 finishes the same afternoon.
		self.assertEqual(day_offset(at(14, 0), at(16, 25)), 0)

	def test_a_leg_that_crosses_midnight_says_so(self):
		# 22:30 out, 00:20 back. AC 1.6 still has to hold.
		self.assertEqual(day_offset(at(22, 30), at(0, 20)), 1)

	def test_the_badge_can_never_exceed_one_day(self):
		# +11/+12/+27 were date arithmetic on the lock lifespan, not journeys.
		for start in range(0, DAY, 3607):
			for end in range(0, DAY, 3607):
				self.assertIn(day_offset(start, end), (0, 1))

	def test_a_missing_timestamp_is_not_a_rollover(self):
		self.assertEqual(day_offset(None, at(6)), 0)
		self.assertEqual(day_offset(at(6), None), 0)

	def test_the_same_minute_is_not_a_rollover(self):
		self.assertEqual(day_offset(at(6, 30), at(6, 30)), 0)


class TestTheDriveDuration(FrappeTestCase):
	"""AC3: no leg reports a day's driving because its dates disagreed."""

	def test_a_twenty_minute_drive_reads_as_twenty_minutes(self):
		self.assertEqual(clock_gap(at(14, 0), at(14, 20)), 20 * 60)

	def test_the_reports_own_numbers(self):
		# 14:00 + 15 -> 14:15, then + 25 -> 14:40, then + 25 + 40 -> 15:45 (AC1's walk,
		# measured back off the clock the way the transit label does it).
		self.assertEqual(clock_gap(at(14, 0), at(14, 15)), 15 * 60)
		self.assertEqual(clock_gap(at(14, 15), at(14, 40)), 25 * 60)
		self.assertEqual(clock_gap(at(14, 40), at(15, 45)), 65 * 60)

	def test_a_leg_past_midnight_wraps_instead_of_going_negative(self):
		# 23:40 -> 00:20 is a forty minute drive, not minus twenty-three hours.
		self.assertEqual(clock_gap(at(23, 40), at(0, 20)), 40 * 60)

	def test_no_gap_can_reach_a_full_day(self):
		for start in range(0, DAY, 3607):
			for end in range(0, DAY, 3607):
				self.assertLess(clock_gap(start, end), DAY)

	def test_the_24h_fallback_is_unreachable(self):
		# The defect: a date difference of one day surviving into fmtDuration, which
		# clamps past-a-day to exactly 86400 and prints "24h".
		same_clock_next_day = clock_gap(at(6, 0), at(6, 0))
		self.assertEqual(same_clock_next_day, 0)


class TestTheFixIsInOnePlace(FrappeTestCase):
	"""Both readers go through secondsOfDay, or the next one to be added will not."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.sheet = SHEET.read_text()

	def test_the_helper_exists_and_is_timezone_aware(self):
		self.assertIn("function secondsOfDay(value) {", self.sheet)
		# Asia/Kuwait, the same clock fmtTime prints in - reading the raw string would
		# take UTC hours and shift every calculation by three.
		helper = self.sheet.split("function secondsOfDay(value) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn('timeZone: "Asia/Kuwait"', helper)

	def test_the_rollover_badge_uses_it(self):
		body = self.sheet.split("function dayOffset(fromISO, toISO) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("secondsOfDay(fromISO)", body)
		self.assertIn("secondsOfDay(toISO)", body)

	def test_the_transit_fallback_uses_it(self):
		self.assertIn("const from = secondsOfDay(t1), to = secondsOfDay(t2);", self.sheet)

	def test_the_whole_timestamp_subtraction_is_gone(self):
		# Both defects were this one expression, in two places.
		self.assertNotIn("const day = 24 * 3600000;", self.sheet)
		self.assertNotIn("const ms = new Date(t2).getTime() - new Date(t1).getTime();",
						 self.sheet)
		self.assertNotIn("Math.floor((to - from) / day)", self.sheet)

	def test_the_badge_still_renders_at_most_one_day(self):
		self.assertIn("return to < from ? 1 : 0;", self.sheet)
		self.assertIn('`<span class="mfst-stop-tag tag-stop">+${offset} Day</span>`', self.sheet)

	def test_the_page_prints_every_time_in_one_clock(self):
		# If fmtTime ever moved off Asia/Kuwait, secondsOfDay would have to move with it.
		fmt = self.sheet.split("function fmtTime(isoStr) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn('timeZone: "Asia/Kuwait"', fmt)
		self.assertEqual(len(re.findall(r'timeZone: "Asia/Kuwait"', self.sheet)),
						 self.sheet.count('timeZone: "Asia/Kuwait"'))


HARNESS = frappe.get_app_path("one_fm", "tests", "js", "manifest_transit_harness.js")


def leg(from_iso, to_iso, stop=None):
	"""Run the SHIPPED calcTransit and return {drive, buffer} in minutes."""
	out = subprocess.run(
		["node", HARNESS, json.dumps({"from": from_iso, "to": to_iso, "stop": stop})],
		capture_output=True, text=True, env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
		check=True,
	)
	return json.loads(out.stdout)


class TestWhichStopCarriesTheLeg(FrappeTestCase):
	"""S-101, from the report: the manifest printed the NEXT leg's minutes.

	A stop's transit and buffer describe the leg that DEPARTS it - the Route Plan row
	starts when the bus pulls away and ends when it reaches the next stop, which is why
	the Trip Builder prints them on the same row as "Next Stop". The manifest passed the
	stop being ARRIVED at, so every gap showed the figures of the leg after it.

	The real rows, in Kuwait time:

	    1 Mahboula Camp   04:50 -> 05:15   transit 20  buffer 5
	    2 Alghanim        05:15 -> 05:32   transit 15  buffer 2
	    3 Salmiya         05:32 -> 05:59   transit 25  buffer 2

	The manifest read the first leg as "15 min drive, 2 min buffer" - Alghanim's figures,
	one leg early - while the Trip Builder read the same run as 20 and 5.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not shutil.which("node"):
			raise cls.failureException("node is needed to run the shipped rule")
		# 01:50Z is 04:50 in Kuwait, which is how these timestamps are actually stored.
		cls.camp = {"transit_minutes": 20, "buffer_minutes": 5}
		cls.alghanim = {"transitMinutes": 15, "bufferMinutes": 2}
		cls.salmiya = {"transitMinutes": 25, "bufferMinutes": 2}

	def test_the_first_drive_is_the_camps_own_figures(self):
		self.assertEqual(
			leg("2026-09-20T01:50:00Z", "2026-09-20T02:15:00Z", self.camp),
			{"drive": 20, "buffer": 5},
		)

	def test_it_is_not_the_arriving_stops_figures(self):
		# The reported symptom: 15 and 2 belong to the leg OUT of Alghanim.
		self.assertNotEqual(
			leg("2026-09-20T01:50:00Z", "2026-09-20T02:15:00Z", self.camp),
			{"drive": 15, "buffer": 2},
		)

	def test_each_later_leg_is_the_stop_it_leaves(self):
		self.assertEqual(
			leg("2026-09-20T02:15:00Z", "2026-09-20T02:32:00Z", self.alghanim),
			{"drive": 15, "buffer": 2},
		)

	def test_the_ride_home_is_the_last_stops_figures(self):
		self.assertEqual(
			leg("2026-09-20T02:32:00Z", "2026-09-20T02:59:00Z", self.salmiya),
			{"drive": 25, "buffer": 2},
		)

	def test_the_printed_minutes_add_up_to_the_clock(self):
		# drive + buffer must equal the gap between the two stamps, or the driver is
		# reading a leg that does not match the times either side of it.
		for start, end, stop in (
			("2026-09-20T01:50:00Z", "2026-09-20T02:15:00Z", self.camp),
			("2026-09-20T02:15:00Z", "2026-09-20T02:32:00Z", self.alghanim),
			("2026-09-20T02:32:00Z", "2026-09-20T02:59:00Z", self.salmiya),
		):
			printed = leg(start, end, stop)
			gap = (frappe.utils.get_datetime(end.replace("Z", ""))
				   - frappe.utils.get_datetime(start.replace("Z", ""))).total_seconds() / 60
			self.assertEqual(printed["drive"] + printed["buffer"], gap, msg=str(stop))

	def test_two_visits_to_one_stop_have_nothing_driven_between_them(self):
		# A drop-off and the pick-up after it are one physical stop printed twice. The
		# minutes of the leg out of that stop belong further down, not in a gap of zero.
		self.assertEqual(
			leg("2026-09-20T02:15:00Z", "2026-09-20T02:15:00Z", self.alghanim),
			{"drive": 0, "buffer": 0},
		)

	def test_a_leg_with_no_minutes_still_falls_back_to_the_clock(self):
		self.assertEqual(
			leg("2026-09-20T02:15:00Z", "2026-09-20T02:32:00Z", None),
			{"drive": 17, "buffer": 0},
		)

	def test_the_clock_fallback_still_wraps_past_midnight(self):
		# AC3: never the flat 24h the raw subtraction used to produce.
		self.assertEqual(
			leg("2026-09-20T20:50:00Z", "2026-09-20T21:20:00Z", None),
			{"drive": 30, "buffer": 0},
		)

	def test_both_spellings_of_the_fields_are_read(self):
		# Camp legs come from the server in snake_case; site stops in camelCase.
		self.assertEqual(
			leg("2026-09-20T01:50:00Z", "2026-09-20T02:15:00Z", {"transitMinutes": 20, "bufferMinutes": 5}),
			leg("2026-09-20T01:50:00Z", "2026-09-20T02:15:00Z", {"transit_minutes": 20, "buffer_minutes": 5}),
		)


class TestBothItinerariesPassTheDepartingStop(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.page = SHEET.read_text()

	def test_the_mixed_run_carries_the_previous_stop(self):
		self.assertIn("let prevStop = o.originLeg;", self.page)
		self.assertIn("o.calcTransit(prevTime, stop.time, prevStop)", self.page)

	def test_the_mixed_run_gets_the_camp_leg_for_its_first_drive(self):
		self.assertIn("originLeg: (legs.camps_ordered || [])[0] || null,", self.page)

	def test_the_camp_by_camp_run_carries_it_too(self):
		self.assertIn("calcTransit(prevTime, item.stop.time, prevStop)", self.page)
		self.assertIn("prevStop = item.stop;", self.page)

	def test_the_ride_home_is_timed_by_the_last_stop(self):
		self.assertIn("calcTransit(prevTime, lastTimeISO, prevStop)", self.page)
		self.assertIn("o.calcTransit(prevTime, o.lastTimeISO, prevStop)", self.page)

	def test_no_loop_still_passes_the_arriving_stop(self):
		# The bug, exactly as it read before.
		self.assertNotIn("calcTransit(prevTime, item.stop.time, item.stop)", self.page)
		self.assertNotIn("o.calcTransit(prevTime, stop.time, stop)", self.page)
