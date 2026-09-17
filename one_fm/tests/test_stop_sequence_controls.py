# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002542: reordering a run's stops without a long vertical drag.

The drawer could only reorder by dragging, and a run of a dozen stops is taller than the
drawer - on a laptop the target position is off screen while the drag is in progress, and
HTML5 drag does not scroll a container by itself.

Three additions, and one bug they exposed:

* **Arrows.** One click per position. They go through the SAME ``_reorderStop`` the drag
  uses, because AC4 asks that an arrow move re-index and re-time "exactly as before" and
  the only way to mean that literally is for it to be the same code.
* **Compact view.** Collapses each stop to one line. Measured on the live board:
  474px -> 66px per row, so 8 fit in the drawer where 1 did (AC2 asks for 6-8).
* **Auto-scroll.** Within 15% of either edge the drawer scrolls while dragging.

The bug: the existing guard read ``targetIndex >= tripStops.length``. ``targetIndex`` is
an insert-BEFORE position, so ``length`` is legal - it means "put it at the end". A drag
never produces that, because every drop target is an existing row, so the guard had never
been wrong. The down arrow on the second-to-last stop is exactly the move that has to
append, and it was silently swallowed - the click did nothing at all. Caught in the
browser, not by these tests, which is why the down-arrow case is pinned here.
"""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))


def _reorder(stops, source_index, target_index):
	"""The JS reorder's index arithmetic, in Python.

	Mirrors ``_reorderStop``: remove the source, then insert before ``target_index``
	measured on the list as it stood, which is why a downward move adjusts by one.
	"""
	if source_index >= len(stops) or target_index > len(stops):
		return list(stops)
	out = list(stops)
	insert_at = target_index - 1 if source_index < target_index else target_index
	moved = out.pop(source_index)
	out.insert(insert_at, moved)
	return out


class TestTheArrowArithmetic(FrappeTestCase):
	"""AC1: one click moves a stop exactly one position, in both directions."""

	def setUp(self):
		self.stops = ["A", "B", "C", "D"]

	def _up(self, stop_num):
		return _reorder(self.stops, stop_num - 1, stop_num - 2)

	def _down(self, stop_num):
		# index + 2, not + 1: see the module docstring.
		return _reorder(self.stops, stop_num - 1, stop_num + 1)

	def test_moving_up_swaps_with_the_stop_above(self):
		self.assertEqual(self._up(3), ["A", "C", "B", "D"])

	def test_moving_down_swaps_with_the_stop_below(self):
		self.assertEqual(self._down(2), ["A", "C", "B", "D"])

	def test_the_second_to_last_stop_can_move_to_the_end(self):
		# The case the old `>=` guard swallowed: target index == length.
		self.assertEqual(self._down(3), ["A", "B", "D", "C"])

	def test_the_last_stop_moving_up_is_the_same_swap_in_reverse(self):
		self.assertEqual(self._up(4), ["A", "B", "D", "C"])

	def test_up_then_down_returns_the_run_to_where_it_started(self):
		moved = _reorder(self.stops, 2, 1)          # move C up
		back = _reorder(moved, 1, 3)               # move it down again
		self.assertEqual(back, self.stops)

	def test_a_target_past_the_end_is_refused(self):
		self.assertEqual(_reorder(self.stops, 0, 99), self.stops)

	def test_a_two_stop_run_still_swaps_both_ways(self):
		pair = ["A", "B"]
		self.assertEqual(_reorder(pair, 1, 0), ["B", "A"])
		self.assertEqual(_reorder(pair, 0, 2), ["B", "A"])


class TestOneReorderPath(FrappeTestCase):
	"""AC4: the arrows and the drag are the same code, so they cannot drift."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_reorder_is_extracted(self):
		self.assertIn("_reorderStop(sourceIndex, targetIndex) {", self.canvas)

	def test_all_three_triggers_call_it(self):
		self.assertEqual(self.canvas.count("this._reorderStop("), 3)

	def test_the_drop_handler_no_longer_holds_the_logic(self):
		drop = self.canvas.split("onStopDrop(event, targetIndex) {", 1)[1].split("\n            },", 1)[0]
		self.assertNotIn("tripStops.splice(", drop)
		self.assertIn("this._reorderStop(sourceIndex, targetIndex);", drop)

	def test_the_insert_before_guard_allows_appending(self):
		self.assertIn("targetIndex > tripStops.length) return;", self.canvas)
		self.assertNotIn("targetIndex >= tripStops.length) return;", self.canvas)

	def test_the_reorder_still_persists_and_rechecks_conflicts(self):
		body = self.canvas.split("_reorderStop(sourceIndex, targetIndex) {", 1)[1].split("\n            },", 1)[0]
		self.assertIn("stop.stopIndex = idx + 1;", body)
		self.assertIn("this.checkConflicts();", body)
		self.assertIn("this.persistAssignments();", body)

	def test_the_arrows_are_hidden_at_the_ends_of_the_run(self):
		self.assertIn("canMoveStopUp(stopNum) { return stopNum > 1; }", self.canvas)
		self.assertIn("canMoveStopDown(stopNum) { return stopNum < this.selectedTripStops.length; }",
					  self.canvas)
		self.assertIn('v-if="canMoveStopUp(stop.stopNum)"', self.canvas)
		self.assertIn('v-if="canMoveStopDown(stop.stopNum)"', self.canvas)

	def test_clicking_an_arrow_does_not_also_reselect_the_stop(self):
		self.assertIn('@click.stop="moveStopUp(stop.stopNum)"', self.canvas)
		self.assertIn('@click.stop="moveStopDown(stop.stopNum)"', self.canvas)


class TestCompactView(FrappeTestCase):
	"""AC2: one line per stop, so a long run can be reordered without scrolling."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_mode_defaults_to_detailed(self):
		self.assertIn("stopViewMode: 'detailed',", self.canvas)

	def test_the_detail_is_what_collapses(self):
		self.assertIn("""<template v-if="stopViewMode === 'detailed'">""", self.canvas)

	def test_the_header_survives_in_compact_mode(self):
		# [handle] [arrows] [seq] [stop name] [direction] must stay on the line.
		header = self.canvas.split('class="rp-detail-card rp-stop-draggable"', 1)[1]
		header = header.split("""<template v-if="stopViewMode === 'detailed'">""", 1)[0]
		self.assertIn("rp-stop-drag-handle", header)
		self.assertIn("rp-stop-move-btn", header)
		self.assertIn("rp-stop-num", header)
		self.assertIn("stop.card.site_location", header)

	def test_the_row_padding_collapses_too(self):
		# Hiding the content but keeping the padding leaves the run as tall as it was.
		self.assertIn(".rp-stop-compact-row {", self.canvas)
		self.assertIn(""":class="{ 'rp-stop-compact-row': stopViewMode === 'compact' }\"""",
					  self.canvas)

	def test_the_toggle_is_only_offered_where_it_helps(self):
		self.assertIn("""<div class="rp-view-toggle" v-if="selectedTripStops.length > 1">""",
					  self.canvas)


class TestAutoScroll(FrappeTestCase):
	"""AC3: the drawer follows a drag that reaches its edges."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_trigger_zone_is_fifteen_percent(self):
		self.assertIn("const EDGE = 0.15;", self.canvas)

	def test_it_scrolls_both_ways(self):
		body = self.canvas.split("_autoScrollDrawer(event) {", 1)[1].split("\n            },", 1)[0]
		self.assertIn("if (fromTop < zone)", body)
		self.assertIn("else if (fromBottom < zone)", body)

	def test_it_keeps_scrolling_while_the_pointer_is_held_still(self):
		# dragover only fires while the pointer MOVES; a dispatcher holding at the edge
		# still expects the list to keep coming.
		self.assertIn("this._autoScrollTimer = setInterval(", self.canvas)

	def test_it_stops_when_the_gesture_ends(self):
		# A timer left running scrolls the drawer for the rest of the session.
		for ender in ("onStopDragEnd(event) {", "onStopDrop(event, targetIndex) {"):
			body = self.canvas.split(ender, 1)[1].split("\n            },", 1)[0]
			self.assertIn("this._stopAutoScroll();", body)

	def test_leaving_the_edge_stops_it_too(self):
		body = self.canvas.split("_autoScrollDrawer(event) {", 1)[1].split("\n            },", 1)[0]
		self.assertIn("if (!step) { this._stopAutoScroll(); return; }", body)


def _leg_edges(departure, arrival, span_start, span_end):
	"""The JS `_legEdges` rule, in Python.

	A bus leaves before its first stop and gets home after its last. A stored pair that
	cannot say that came from a different timing of the run, and BOTH halves are dropped
	together rather than one being half-trusted.
	"""
	departs_too_late = departure is not None and span_start is not None and departure > span_start
	arrives_too_early = arrival is not None and span_end is not None and arrival < span_end
	if departs_too_late or arrives_too_early:
		return (None, None)
	return (departure, arrival)


class TestTheRunsOwnEndsMoveWithIt(FrappeTestCase):
	"""The over-stretch reported on S-101.

	The camp departure and the ride home are stored against the TRIP, not on any block,
	and the reorder re-timed the stops without touching them. The lane draws a trip from
	min(stored departure, first stop) to max(stored arrival, last stop), so a run re-timed
	into the evening kept its morning departure and the block stretched across the whole
	day - 04:50 to 19:01 on a run whose stops ran 17:33 to 19:01. The drawer read the same
	stale pair and printed "04:50 -> 05:59 (-1371 min)".
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_reorder_moves_both_stored_ends(self):
		body = self.canvas.split("_reorderStop(sourceIndex, targetIndex) {", 1)[1] \
						  .split("\n            },", 1)[0]
		self.assertIn("departure: shifted(held.departure, startDelta),", body)
		self.assertIn("arrival: shifted(held.arrival, endDelta),", body)

	def test_each_end_moves_by_its_own_delta(self):
		# One shared delta puts the arrival wrong whenever the reorder changes the run's
		# overall length, which it does whenever the gaps are not all equal.
		body = self.canvas.split("_reorderStop(sourceIndex, targetIndex) {", 1)[1] \
						  .split("\n            },", 1)[0]
		self.assertIn("const startDelta = Math.min(...edgesOf(tripStops, 'start')) - oldFirstStart;",
					  body)
		self.assertIn("const endDelta = Math.max(...edgesOf(tripStops, 'end')) - oldLastEnd;",
					  body)

	def test_a_run_with_no_stored_ends_is_left_alone(self):
		body = self.canvas.split("_reorderStop(sourceIndex, targetIndex) {", 1)[1] \
						  .split("\n            },", 1)[0]
		self.assertIn("if (held) {", body)

	def test_a_stale_pair_is_refused_by_the_reads(self):
		# S-101's actual numbers: stops 17:33-19:01, stored pair 04:50-05:59.
		self.assertEqual(_leg_edges(290, 359, 1053, 1141), (None, None))

	def test_a_real_camp_leg_still_widens_the_block(self):
		# The bus does leave before its first stop and get back after its last - that
		# widening is the point, and refusing it would shrink every run to its stops.
		self.assertEqual(_leg_edges(1020, 1160, 1053, 1141), (1020, 1160))

	def test_a_departure_after_the_first_stop_is_impossible(self):
		self.assertEqual(_leg_edges(1100, 1160, 1053, 1141), (None, None))

	def test_an_arrival_before_the_last_stop_is_impossible(self):
		self.assertEqual(_leg_edges(1020, 1100, 1053, 1141), (None, None))

	def test_a_run_with_no_stored_pair_falls_back_to_its_stops(self):
		self.assertEqual(_leg_edges(None, None, 1053, 1141), (None, None))

	def test_both_halves_are_dropped_together(self):
		# Keeping the plausible half of a broken pair still draws the block from a time
		# the run does not have.
		self.assertEqual(_leg_edges(1020, 1100, 1053, 1141), (None, None))
		self.assertEqual(_leg_edges(1100, 1160, 1053, 1141), (None, None))

	def test_the_drawer_and_the_lane_use_the_same_rule(self):
		# Two implementations would let the header and the block disagree again.
		self.assertIn("_legEdges(tripId, spanStartMs, spanEndMs) {", self.canvas)
		self.assertIn("this._legEdges(tripId, spanStart.getTime(), spanEnd.getTime());",
					  self.canvas)
		self.assertEqual(self.canvas.count("this._legEdges("), 3)
