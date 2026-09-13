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


def _method(name, args="tripId"):
	"""The named method's source, by counting braces from its opening one."""
	source = CANVAS.read_text()
	start = source.index(f"{name}({args}) {{")
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
		// The real one, not a stub: _retimeTrip lays each stop out after the one before
		// it, so which order it walks is part of what these tests are checking.
		_inRunOrder: function (items) {_method('_inRunOrder', 'items')},
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


def remove(items, removed_card, leg_timings=None):
	"""Take `removed_card` off the run and hand back the blocks and the run's two ends."""
	script = f"""
	const close = function (tripId, removed) {_method('_closeTripGap', 'tripId, removed')};
	const all = {json.dumps(items)};
	all.forEach((i) => {{ i.start = new Date(i.start); i.end = new Date(i.end); }});
	const gone = all.find((i) => i.cardId === {json.dumps(removed_card)});
	const canvas = {{
		swimItems: all.filter((i) => i !== gone),
		legTimings: {json.dumps(leg_timings or {})},
		_runEndsAt: function (stops) {_method('_runEndsAt', 'stops')},
	}};
	close.call(canvas, 'T1', gone);
	console.log(JSON.stringify({{
		blocks: canvas.swimItems.map((i) => ({{
			cardId: i.cardId,
			start: new Date(i.start).toISOString(), end: new Date(i.end).toISOString(),
		}})),
		legs: canvas.legTimings,
	}}));
	"""
	out = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
	if out.returncode:
		raise AssertionError(out.stderr)
	result = json.loads(out.stdout)
	return {row["cardId"]: row for row in result["blocks"]}, result["legs"]


class TestTheRunClosesOverAStopItNoLongerMakes(FrappeTestCase):
	"""WI-002401: removing a card has to take its time off the run.

	The blocks after the removed one used to keep their old positions - a hole was left
	where the stop had been and the drawer went on reading the run's stored arrival, so a
	three-stop run that lost a stop still read "13:00 -> 14:21 (81 min)".
	"""

	# A run of three stops, each block running from where the bus leaves that stop to
	# where it reaches the next, and an arrival that is the end of the last one.
	RUN = [
		_block("A", 1, "2026-08-18T10:27:00Z", "2026-08-18T10:54:00Z", transit=25, buffer=2),
		_block("B", 2, "2026-08-18T10:54:00Z", "2026-08-18T11:04:00Z", transit=10, buffer=0),
		_block("C", 3, "2026-08-18T11:04:00Z", "2026-08-18T11:21:00Z", transit=15, buffer=2),
	]
	LEGS = {"T1": {
		"departure": "2026-08-18T10:00:00Z", "arrival": "2026-08-18T11:21:00Z",
		"home": {"place": "Mahboula Camp", "transit_minutes": 0, "buffer_minutes": 0},
		"camps": {"Mahboula Camp": {"transit_minutes": 25, "buffer_minutes": 2}},
	}}

	def setUp(self):
		if not shutil.which("node"):
			self.skipTest("node is not on this machine")

	def test_the_stops_after_it_move_up_by_what_it_was_using(self):
		blocks, _ = remove(self.RUN, "B", self.LEGS)

		# B was 10 minutes of the run; C now happens 10 minutes earlier.
		self.assertEqual(blocks["A"]["end"], "2026-08-18T10:54:00.000Z")
		self.assertEqual(blocks["C"]["start"], "2026-08-18T10:54:00.000Z")
		self.assertEqual(blocks["C"]["end"], "2026-08-18T11:11:00.000Z")

	def test_the_stops_before_it_are_left_alone(self):
		blocks, _ = remove(self.RUN, "B", self.LEGS)

		self.assertEqual(blocks["A"]["start"], "2026-08-18T10:27:00.000Z")

	def test_the_run_is_over_that_much_sooner(self):
		_, legs = remove(self.RUN, "B", self.LEGS)

		self.assertEqual(legs["T1"]["arrival"], "2026-08-18T11:11:00.000Z")

	def test_the_departure_the_dispatcher_typed_is_not_moved(self):
		# It is a decision, and the camp leg that follows it is unchanged.
		_, legs = remove(self.RUN, "B", self.LEGS)

		self.assertEqual(legs["T1"]["departure"], "2026-08-18T10:00:00Z")
		self.assertEqual(legs["T1"]["camps"], self.LEGS["T1"]["camps"])

	def test_losing_the_first_stop_shortens_the_run_rather_than_delaying_it(self):
		blocks, legs = remove(self.RUN, "A", self.LEGS)

		self.assertEqual(blocks["B"]["start"], "2026-08-18T10:27:00.000Z")
		self.assertEqual(legs["T1"]["arrival"], "2026-08-18T10:54:00.000Z")

	def test_losing_the_last_stop_ends_the_run_where_the_one_before_it_does(self):
		blocks, legs = remove(self.RUN, "C", self.LEGS)

		self.assertEqual(blocks["B"]["end"], "2026-08-18T11:04:00.000Z")
		self.assertEqual(legs["T1"]["arrival"], "2026-08-18T11:04:00.000Z")

	def test_a_combined_stop_keeps_its_window_when_one_of_its_cards_goes(self):
		# One visit where some riders get off and others get on: both cards are drawn on
		# the same window on purpose. The bus is still standing there, so no time is
		# freed and nothing after it may move.
		run = self.RUN + [
			_block("B2", 4, "2026-08-18T10:54:00Z", "2026-08-18T11:04:00Z", transit=10, buffer=0),
		]

		blocks, legs = remove(run, "B", self.LEGS)

		self.assertEqual(blocks["B2"]["start"], "2026-08-18T10:54:00.000Z")
		self.assertEqual(blocks["C"]["start"], "2026-08-18T11:04:00.000Z")
		self.assertEqual(legs["T1"]["arrival"], "2026-08-18T11:21:00Z")

	def test_an_arrival_left_drifted_by_an_earlier_removal_is_repaired(self):
		# Read off the run rather than moved by the offset, so a run that was already
		# wrong comes back right instead of staying wrong by the same amount.
		drifted = {"T1": dict(self.LEGS["T1"], arrival="2026-08-18T11:31:00Z")}

		_, legs = remove(self.RUN, "B", drifted)

		self.assertEqual(legs["T1"]["arrival"], "2026-08-18T11:11:00.000Z")

	def test_the_last_stop_off_a_run_takes_the_runs_timings_with_it(self):
		# Nothing left to time: the camp and home legs belonged to a run that is gone.
		_, legs = remove([self.RUN[0]], "A", self.LEGS)

		self.assertNotIn("T1", legs)


class TestTheDrawerReadsTheRunInOrder(FrappeTestCase):
	"""The stops are listed in the order the bus drives them, and the run's two ends
	are the moment it leaves the camp and the moment it gets back.

	stopIndex is the order the cards were dropped on the lane, not the order of the run:
	a card added first can be the last stop. Sorted by it, a 07:32 stop was listed above
	a 07:20 one and the trip timeline read "07:32 to 07:32 (0 min)".
	"""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_stops_are_sorted_by_when_the_bus_reaches_them(self):
		self.assertIn("new Date(a.start) - new Date(b.start)", self.source)

	def test_the_timeline_starts_where_the_bus_leaves_the_camp(self):
		# Not at the first block: the first block is the first SITE, which the bus
		# reaches after the camp leg, so the journey read short at both ends.
		self.assertIn("const stored = this.selectedTripLegs.departure;", self.source)
		self.assertIn("{{ fmtISO(tripStartsAt()) }}", self.source)

	def test_the_timeline_ends_when_the_bus_is_back(self):
		# The blocks say when that is; the stored arrival is a copy of the same moment and
		# is only read when there are no blocks left to read (WI-002401). The copy is what
		# had a run that lost a stop still reading its old, longer total.
		self.assertIn("return this.lastStopEndsAt() || this.selectedTripLegs.arrival;", self.source)

	def test_the_drive_out_of_the_camp_is_shown_before_the_first_stop(self):
		# The timeline began at 06:45 and the first stop at 07:15, and the half hour
		# between them - the drive to it - was accounted for nowhere.
		self.assertIn("Departure from Camp", self.source)
		self.assertLess(
			self.source.index("Departure from Camp"),
			self.source.index("Stops grouped under their pickup accommodation camp banner"),
		)

	def test_it_spans_the_departure_to_the_first_stop(self):
		self.assertIn(
			"{{ fmtISO(tripStartsAt()) }} &rarr; {{ fmtISO(firstStopStartsAt()) }}",
			self.source,
		)

	def test_the_report_time_is_shown_against_the_leg_it_belongs_to(self):
		# The driver reports before the bus leaves the CAMP, not before a stop it drives
		# to later - and it was printed against that stop, 15 minutes off.
		self.assertIn('v-if="stopQoaTime(stop) && !campLegPlaces().length"', self.source)

	def test_a_stops_second_time_names_the_place_it_belongs_to(self):
		# "Departure -> Target Arrival" on a row headed Siemens reads as the arrival at
		# Siemens. It is the arrival at the stop AFTER it, so it says which.
		self.assertNotIn("Departure &rarr; Target Arrival", self.source)
		self.assertIn("{{ __('Leaves Here') }} &rarr; {{ __('Reaches') }} {{ nextStopName(stop) }}",
					  self.source)

	def test_the_last_stop_reaches_the_camp(self):
		# There is always a next place: the run ends by going home.
		self.assertIn("return (this.selectedTripLegs.home || {}).place || __('Camp');",
					  self.source)

	def test_the_ride_home_is_shown_before_the_trip_total(self):
		self.assertIn("Return to Camp", self.source)
		self.assertLess(
			self.source.index("Return to Camp"), self.source.index("Trip Total")
		)

	def test_a_ride_home_with_no_minutes_in_it_is_not_shown(self):
		# The last drop was already at the camp; the bus is home.
		self.assertIn('v-if="rideHomeMinutes() > 0"', self.source)
