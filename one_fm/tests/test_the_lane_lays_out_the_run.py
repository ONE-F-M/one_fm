# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The blocks on a lane are a drawing of the minutes, so the arithmetic is tested.

`_retimeTrip` is the only place a run's blocks are positioned. It lives in a Vue app and
cannot be imported, so the method is lifted out of the source and run in node against a
fake canvas - which is worth the awkwardness, because every timing bug reported on this
board so far has been in these few lines.
"""

import json
import pathlib
import shutil
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))
MINUTE = 60000


def _method(name):
	"""The named method's source, by counting braces from its opening one."""
	source = CANVAS.read_text()
	start = source.index(f"{name}(tripId) {{")
	depth, i = 0, source.index("{", start)
	while True:
		if source[i] == "{":
			depth += 1
		elif source[i] == "}":
			depth -= 1
			if depth == 0:
				break
		i += 1
	return source[source.index("{", start):i + 1]


def retime(items, leg_timings=None, own=None):
	"""Run _retimeTrip over `items` in node and hand back where the blocks landed."""
	script = f"""
	const retime = function (tripId) {_method('_retimeTrip')};
	const canvas = {{
		swimItems: {json.dumps(items)},
		legTimings: {json.dumps(leg_timings or {})},
		_ownDirection: (item) => ({json.dumps(own or {})})[item.cardId] || 'OUTBOUND',
	}};
	canvas.swimItems.forEach((i) => {{ i.start = new Date(i.start); i.end = new Date(i.end); }});
	retime.call(canvas, 'T1');
	console.log(JSON.stringify(canvas.swimItems.map((i) => ({{
		cardId: i.cardId, start: i.start.toISOString(), end: i.end.toISOString(),
	}}))));
	"""
	out = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
	if out.returncode:
		raise AssertionError(out.stderr)
	return {row["cardId"]: row for row in json.loads(out.stdout)}


def _block(card, stop_index, start, end, transit=0, buffer=0):
	return {
		"cardId": card, "tripId": "T1", "stopIndex": stop_index,
		"start": start, "end": end, "transitMinutes": transit, "bufferMinutes": buffer,
	}


class TestAnOutwardRunIsPinnedOnSite(FrappeTestCase):
	"""The reported bug: the departure moved on its own after a merge.

	Every stop's minutes are the drive AWAY from it. The first stop's own minutes are
	therefore the leg to the SECOND stop - and subtracting them backwards from its
	arrival moved the departure by however long that next drive happened to be.
	"""

	def setUp(self):
		if not shutil.which("node"):
			self.skipTest("node is not on this machine")

	def test_the_departure_is_the_camp_leg_back_from_the_first_arrival(self):
		# Camp leg 5 + 25 = 30 minutes, so a 07:00 arrival departs at 06:30 - whatever
		# the drive from the first site to the second turns out to be.
		placed = retime(
			[_block("A", 1, "2026-08-18T06:00:00Z", "2026-08-18T07:00:00Z", transit=40, buffer=5)],
			leg_timings={"T1": {"Camp": {"transit_minutes": 25, "buffer_minutes": 5}}},
		)

		self.assertEqual(placed["A"]["start"], "2026-08-18T06:30:00.000Z")
		self.assertEqual(placed["A"]["end"], "2026-08-18T07:00:00.000Z")

	def test_the_second_drive_does_not_move_the_departure(self):
		# The same run with a longer drive to stop two departs at exactly the same time.
		short = retime(
			[_block("A", 1, "2026-08-18T06:00:00Z", "2026-08-18T07:00:00Z", transit=10, buffer=0)],
			leg_timings={"T1": {"Camp": {"transit_minutes": 25, "buffer_minutes": 5}}},
		)
		long = retime(
			[_block("A", 1, "2026-08-18T06:00:00Z", "2026-08-18T07:00:00Z", transit=90, buffer=0)],
			leg_timings={"T1": {"Camp": {"transit_minutes": 25, "buffer_minutes": 5}}},
		)

		self.assertEqual(short["A"]["start"], long["A"]["start"])

	def test_the_stops_after_it_follow_the_leg_out_of_the_one_before(self):
		# A 07:00 arrival at A, 20 minutes out of A, so B runs 07:00 to 07:20.
		placed = retime(
			[
				_block("A", 1, "2026-08-18T06:00:00Z", "2026-08-18T07:00:00Z", transit=15, buffer=5),
				_block("B", 2, "2026-08-18T07:00:00Z", "2026-08-18T07:05:00Z", transit=30, buffer=0),
			],
			leg_timings={"T1": {"Camp": {"transit_minutes": 25, "buffer_minutes": 5}}},
		)

		self.assertEqual(placed["A"]["start"], "2026-08-18T06:30:00.000Z")
		self.assertEqual(placed["B"]["start"], "2026-08-18T07:00:00.000Z")
		self.assertEqual(placed["B"]["end"], "2026-08-18T07:20:00.000Z")

	def test_a_run_with_no_camp_leg_yet_keeps_the_old_behaviour(self):
		# A plan saved before camp legs were recorded still has to draw something.
		placed = retime(
			[_block("A", 1, "2026-08-18T06:00:00Z", "2026-08-18T07:00:00Z", transit=40, buffer=5)]
		)

		self.assertEqual(placed["A"]["start"], "2026-08-18T06:15:00.000Z")


class TestAReturnRunIsPinnedAtCollection(FrappeTestCase):
	def setUp(self):
		if not shutil.which("node"):
			self.skipTest("node is not on this machine")

	def test_it_runs_forward_from_the_moment_the_shift_ends(self):
		# The riders are collected at 18:00 and the drive away is 5 + 25.
		placed = retime(
			[_block("R", 1, "2026-08-18T18:00:00Z", "2026-08-18T18:05:00Z", transit=25, buffer=5)],
			leg_timings={"T1": {"Camp": {"transit_minutes": 90, "buffer_minutes": 0}}},
			own={"R": "RETURN"},
		)

		self.assertEqual(placed["R"]["start"], "2026-08-18T18:00:00.000Z")
		self.assertEqual(placed["R"]["end"], "2026-08-18T18:30:00.000Z")
