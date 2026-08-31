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


class TestTheRunWalksForward(FrappeTestCase):
	"""One rule, the server's: a stop's minutes are the leg that BRINGS the bus to it.

	The lane used to walk its own way - the first block pinned at its arrival and every
	block after it sized by the minutes of the stop before. So the modal said one thing
	and the blocks said another, and the departure appeared to move on its own.
	"""

	def setUp(self):
		if not shutil.which("node"):
			self.skipTest("node is not on this machine")

	def test_a_block_is_as_long_as_its_own_leg(self):
		# Arrival = Departure + Buffer + Transit, read literally.
		placed = retime(
			[_block("A", 1, "2026-08-18T06:30:00Z", "2026-08-18T06:35:00Z", transit=25, buffer=5)]
		)

		self.assertEqual(placed["A"]["start"], "2026-08-18T06:30:00.000Z")
		self.assertEqual(placed["A"]["end"], "2026-08-18T07:00:00.000Z")

	def test_the_next_stop_departs_when_this_one_is_done(self):
		placed = retime([
			_block("A", 1, "2026-08-18T06:30:00Z", "2026-08-18T06:35:00Z", transit=25, buffer=5),
			_block("B", 2, "2026-08-18T09:00:00Z", "2026-08-18T09:05:00Z", transit=10, buffer=5),
		])

		self.assertEqual(placed["B"]["start"], "2026-08-18T07:00:00.000Z")
		self.assertEqual(placed["B"]["end"], "2026-08-18T07:15:00.000Z")

	def test_the_first_block_is_not_moved(self):
		# It is where the run is on the lane; dragging it is how a run is moved, and
		# nothing else may move it underneath the dispatcher.
		placed = retime([
			_block("A", 1, "2026-08-18T06:30:00Z", "2026-08-18T07:00:00Z", transit=90, buffer=0),
		])

		self.assertEqual(placed["A"]["start"], "2026-08-18T06:30:00.000Z")

	def test_an_untimed_block_keeps_the_width_it_has(self):
		# A trip saved before the minutes were persisted is not collapsed to nothing.
		placed = retime([_block("A", 1, "2026-08-18T06:00:00Z", "2026-08-18T07:00:00Z")])

		self.assertEqual(placed["A"]["end"], "2026-08-18T07:00:00.000Z")

	def test_a_return_run_walks_the_same_way(self):
		# There is no second rule for a return run; there never should have been.
		placed = retime(
			[_block("R", 1, "2026-08-18T18:00:00Z", "2026-08-18T18:05:00Z", transit=25, buffer=5)],
			own={"R": "RETURN"},
		)

		self.assertEqual(placed["R"]["start"], "2026-08-18T18:00:00.000Z")
		self.assertEqual(placed["R"]["end"], "2026-08-18T18:30:00.000Z")
