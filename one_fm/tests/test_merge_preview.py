# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002078: what the Merge Trip modal is shown before anyone confirms.

The preview is computed on the server so the seat count an operator sees is the one the
Route Plan save will judge them by. A second implementation in the browser would drift,
and the modal would promise a merge the save then refuses.
"""

import pathlib
import re

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.operations.doctype.route_plan.route_plan import leg_occupancy

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))
CANVAS_SERVER = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.py"
))
MANIFEST = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_manifest_page", "transportation_manifest_page.js"
))
MERGE_COLOUR = "#819171"


class TestLegOccupancy(FrappeTestCase):
	"""The shared walk. Route Plan validation and the modal both read this."""

	def _stops(self, *pairs):
		return [{"headcount": n, "boards": boards} for n, boards in pairs]

	def test_a_drop_then_a_board_never_ride_together(self):
		peak, _worst, per_leg = leg_occupancy(self._stops((12, False), (12, True)))

		self.assertEqual(peak, 12)
		self.assertEqual(per_leg, [0, 12])

	def test_two_outward_loads_do_ride_together(self):
		peak, _worst, _per_leg = leg_occupancy(self._stops((10, False), (10, False)))

		self.assertEqual(peak, 20)

	def test_the_loop_from_the_criteria(self):
		# Camp -> drop 10 -> drop 12 -> board 10 -> Camp. 32 carried, 22 at the peak.
		peak, worst, per_leg = leg_occupancy(
			self._stops((10, False), (12, False), (10, True))
		)

		self.assertEqual(peak, 22)
		self.assertEqual(worst, 1)
		self.assertEqual(per_leg, [12, 0, 10])

	def test_the_peak_can_fall_later_in_the_run(self):
		peak, worst, _per_leg = leg_occupancy(self._stops((5, True), (9, True)))

		self.assertEqual(peak, 14)
		self.assertEqual(worst, 2)

	def test_an_empty_run_peaks_at_nothing(self):
		self.assertEqual(leg_occupancy([]), (0, 1, []))

	def test_disembarking_is_applied_before_boarding(self):
		# Both at one stop: 10 off then 10 on never exceeds 10.
		peak, _worst, _per_leg = leg_occupancy(self._stops((10, False), (10, True)))

		self.assertEqual(peak, 10)


class TestTheCanvasSpeaksMixed(FrappeTestCase):
	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_merge_colour_is_the_one_the_story_names(self):
		self.assertIn(f"--rp-color-mixed: {MERGE_COLOUR}", self.source)

	def test_a_merged_block_paints_itself_with_it(self):
		# Without this a merged block borrowed whichever direction was dropped first.
		self.assertIn("item.direction === 'MIXED'", self.source)
		self.assertIn("--rp-color-mixed", self.source)

	def test_the_legend_offers_mixed(self):
		self.assertIn('class="rp-legend-item rp-legend-mixed">Mixed<', self.source)

	def test_mixed_sits_between_return_and_conflict(self):
		order = [
			m.group(1) for m in re.finditer(r'class="rp-legend-item rp-legend-(\w+)"', self.source)
		]

		self.assertEqual(order[:4], ["out", "ret", "mixed", "conflict"])

	def test_the_legend_badge_is_styled(self):
		self.assertIn(".rp-legend-mixed", self.source)

	def test_the_dark_theme_covers_it_too(self):
		self.assertIn("rp-dark .rp-legend-mixed", self.source)


class TestMergePreviewShape(FrappeTestCase):
	"""The endpoint's contract, exercised without touching real shipments."""

	def test_it_is_whitelisted_for_the_canvas_to_call(self):
		# The canvas reaches it over frappe.call, so it has to be whitelisted or the modal
		# gets a PermissionError instead of a preview.
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			get_merge_preview,
			merge_trip_shipments,
		)

		frappe.is_whitelisted(get_merge_preview)
		frappe.is_whitelisted(merge_trip_shipments)

	def test_merging_needs_more_than_one_card(self):
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			get_merge_preview,
		)

		with self.assertRaises(frappe.ValidationError):
			get_merge_preview(["TS-only-one"])

	def test_minutes_are_read_defensively(self):
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import _minutes

		self.assertEqual(_minutes(None), 0)
		self.assertEqual(_minutes(""), 0)
		self.assertEqual(_minutes("15"), 15)
		self.assertEqual(_minutes(-5), 0)          # a negative wait would run the clock backwards
		self.assertEqual(_minutes("not a number"), 0)


class TestTheMergeModal(FrappeTestCase):
	"""AC1-AC4: what the drop opens, and what it shows before Confirm is enabled."""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_a_drop_onto_an_occupied_lane_opens_the_modal(self):
		# Before this the card was silently re-timed on a default 30-minute transit.
		self.assertIn("_isMergeDrop(newCard, existingItems)", self.source)
		self.assertIn("_openMergeTripModal(newCard, existingItems, vehicleId)", self.source)

	def test_chaining_two_stops_the_same_way_is_left_alone(self):
		# Multi-stop chaining in one direction is existing behaviour, not a merge.
		self.assertIn("return dirs.size > 1 || dirs.has('MIXED')", self.source)

	def test_the_direction_badge_is_mixed_and_read_only(self):
		self.assertIn(">MIXED<", self.source)
		self.assertIn("cannot be changed here", self.source)

	def test_the_modal_shows_the_vehicle_capacity(self):
		self.assertIn("Max Passenger Capacity", self.source)

	def test_the_primary_action_commits_the_merge(self):
		# Renamed with the forward-scheduling work (WI-002151): the modal now states the
		# departure and applies the whole itinerary, not just the merge. What has to hold
		# is that its primary action is the thing that commits it.
		self.assertIn("__('Confirm & Apply')", self.source)
		self.assertIn("merge_trip_shipments", self.source)

	def test_each_visit_is_its_own_container(self):
		self.assertIn("Seq ${s.stop_index}", self.source)
		self.assertIn("EMPLOYEES BOARDING", self.source)
		self.assertIn("DROPPING OFF EMPLOYEES", self.source)

	def test_there_is_a_per_leg_transit_and_buffer_table(self):
		# The table gained the rest of the leg picture in WI-002151 - card, direction,
		# origin, next stop and the forward-calculated arrival - but the two editable
		# minute fields are what re-time the run and they still have to be there.
		self.assertIn("Legs — arrival is calculated forward from the departure above", self.source)
		# The two editable minute fields are emitted from one helper now that a row is a
		# stop rather than a card, so the key is templated.
		self.assertIn('data-key="${key}"', self.source)
		self.assertIn("minutes('buffer_minutes', s.buffer_minutes)", self.source)
		self.assertIn("minutes('transit_minutes', s.transit_minutes)", self.source)

	def test_editing_a_leg_re_times_the_rest_of_the_run(self):
		# The change handler re-renders from the server, which recomputes every later stop.
		self.assertIn(".rp-leg-min", self.source)
		self.assertIn("render();   // re-times every stop after this one", self.source)

	def test_an_exceeded_leg_is_banned_in_red_and_disables_confirm(self):
		self.assertIn("#fee2e2", self.source)
		self.assertIn("get_primary_btn().prop('disabled', !p.can_merge)", self.source)

	def test_the_failing_stop_is_highlighted_in_the_itinerary(self):
		self.assertIn("s.exceeded ?", self.source)

	def test_confirming_calls_the_merge_endpoint(self):
		self.assertIn("transportation_shipment.merge_trip_shipments", self.source)

	def test_confirming_marks_every_stop_mixed_under_one_group(self):
		self.assertIn("item.tripId = tripId; item.direction = 'MIXED';", self.source)


class TestCardIdsResolveToShipments(FrappeTestCase):
	"""The canvas sends card ids, not document names.

	The regression this covers: both endpoints were handed "TSHIP-TS-0659" and looked up a
	document by that name, so Confirm & Merge Trip answered 404 - Transportation Shipment
	TSHIP-TS-0659 not found.
	"""

	def setUp(self):
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			resolve_shipment_names,
		)
		self.resolve = resolve_shipment_names

	def test_a_card_id_is_stripped_to_its_shipment(self):
		self.assertEqual(self.resolve(["TSHIP-TS-0659"]), ["TS-0659"])

	def test_a_direction_suffix_is_stripped_too(self):
		# The canvas suffixes a card when it places both legs of one demand.
		self.assertEqual(self.resolve(["TSHIP-TS-0659_OUT"]), ["TS-0659"])
		self.assertEqual(self.resolve(["TSHIP-TS-0659_RET"]), ["TS-0659"])
		self.assertEqual(self.resolve(["TSHIP-TS-0659_OUTBOUND"]), ["TS-0659"])
		self.assertEqual(self.resolve(["TSHIP-TS-0659_RETURN"]), ["TS-0659"])

	def test_a_plain_shipment_name_passes_through(self):
		# Callers other than the canvas pass real names; both have to work.
		self.assertEqual(self.resolve(["TS-0659"]), ["TS-0659"])

	def test_the_two_legs_of_one_card_collapse_to_one_shipment(self):
		self.assertEqual(self.resolve(["TSHIP-TS-0659_OUT", "TSHIP-TS-0659_RET"]), ["TS-0659"])

	def test_order_is_preserved(self):
		self.assertEqual(
			self.resolve(["TSHIP-TS-2", "TSHIP-TS-1"]), ["TS-2", "TS-1"]
		)

	def test_blanks_are_dropped(self):
		self.assertEqual(self.resolve(["", None, "TSHIP-TS-1"]), ["TS-1"])

	def test_nothing_in_nothing_out(self):
		self.assertEqual(self.resolve([]), [])
		self.assertEqual(self.resolve(None), [])

	def test_a_merge_of_one_card_placed_twice_is_still_rejected(self):
		# Both legs of one card are one shipment, so this is not a merge and must not
		# silently proceed as if it were.
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			merge_trip_shipments,
		)

		with self.assertRaises(frappe.ValidationError):
			merge_trip_shipments(["TSHIP-TS-0659_OUT", "TSHIP-TS-0659_RET"])


class TestTheMergedBlockPaintsMixed(FrappeTestCase):
	"""The regression the reporter hit: a merged trip still rendered in the Return colour.

	A multi-stop block and a single block are drawn by different branches of the template,
	and the merged branch carried its own inline colour ladder that never learned about
	MIXED. Both now share one rule.
	"""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_merged_block_uses_the_shared_fill(self):
		self.assertIn(':fill="mfill(entry)"', self.source)

	def test_the_merged_branch_no_longer_hardcodes_its_colours(self):
		self.assertNotIn(
			"entry.direction === 'OUTBOUND' ? '#1565c0' : '#e65100'", self.source
		)

	def test_the_shared_rule_is_the_one_that_knows_mixed(self):
		self.assertIn("mfill(entry) {", self.source)
		self.assertIn("return this.bfill({", self.source)

	def test_a_run_is_mixed_once_any_stop_is(self):
		# Taking the first stop's direction left a merged run reading as whatever leg
		# happened to be placed first. The block now asks runDirection, which answers
		# MIXED whenever the stops do not all agree - so a run holding one MIXED stop is
		# still Mixed, and so is one whose stops merely disagree, which is the shape a
		# run chained through the trip picker has (WI-002160).
		self.assertIn("direction: this.runDirection(stops),", self.source)
		self.assertIn("runDirection(stops) {", self.source)
		self.assertIn(
			"return stops.some(s => (s.direction || 'OUTBOUND') !== first) ? 'MIXED' : first;",
			self.source,
		)

	def test_both_block_shapes_still_show_conflict_and_overcapacity(self):
		self.assertIn("conflict: entry.conflict", self.source)
		self.assertIn("overcapacity: entry.overcapacity", self.source)


class TestTheLaneMeasuresAMergedRunByItsPeak(FrappeTestCase):
	"""The regression the reporter hit: a merged block painted purple for overcapacity.

	The browser keeps its own copy of the logical-trip walk for the lane colours, and it
	was still summing headcounts - 2 dropped plus 5 collected read as 7 on a 6-seat van,
	so a run that never carries more than 5 was flagged over capacity.
	"""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_lane_walks_a_merged_trip_leg_by_leg(self):
		self.assertIn("tripOccupancy(trip) {", self.source)
		self.assertIn("if (trip.direction !== 'MIXED') return trip.headcount;", self.source)

	def test_the_overcapacity_check_reads_the_occupancy(self):
		self.assertNotIn("reduce((sum, t) => sum + t.headcount, 0)", self.source)
		self.assertIn("reduce((sum, t) => sum + t.occupancy, 0)", self.source)

	def test_alighting_is_applied_before_boarding(self):
		self.assertIn("boards(s) ? (s.headcount || 0) : -(s.headcount || 0)", self.source)

	def test_a_stop_knows_which_way_its_own_riders_travel(self):
		# item.direction reads MIXED for every stop of a merged run, so the per-stop
		# answer has to come from the card.
		self.assertIn("cardOwnDirection(item) {", self.source)
		self.assertIn("card.own_direction", self.source)

	def test_the_server_sends_that_direction_with_every_card(self):
		card_builder = pathlib.Path(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.py"
		)).read_text()

		self.assertIn('"own_direction":         own_direction', card_builder)
		self.assertIn("_card_direction(s.trip_direction, s.pre_merge_trip_direction)", card_builder)

	def test_the_lane_and_the_save_share_one_rule(self):
		# tripOccupancy mirrors _trip_peak; if they drift the operator is told a run fits
		# and the save refuses it, or the reverse.
		from one_fm.operations.doctype.route_plan.route_plan import _trip_peak

		self.assertIsNotNone(_trip_peak)
		self.assertIn("Mirrors _trip_peak on the", self.source)


class TestAMergedRunIsNamedMixed(FrappeTestCase):
	"""Every ad-hoc `=== 'OUTBOUND' ? ... : 'Return'` labelled a merged run Return."""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_there_is_one_place_that_names_a_direction(self):
		self.assertIn("dirName(direction) {", self.source)
		self.assertIn("dirLabel(direction) {", self.source)
		self.assertIn("dirBadgeClass(direction) {", self.source)

	def test_mixed_is_named_rather_than_defaulted(self):
		self.assertIn("if (direction === 'MIXED') return 'Mixed';", self.source)

	def test_the_details_badge_asks_for_the_label(self):
		self.assertIn("dirLabel(selectedItem.direction)", self.source)
		self.assertIn("dirBadgeClass(selectedItem.direction)", self.source)

	def test_the_old_inline_badge_rule_is_gone(self):
		self.assertNotIn("selectedItem.direction === 'OUTBOUND' ? 'rp-dir-out' : 'rp-dir-ret'", self.source)

	def test_the_badge_is_styled_in_the_merge_colour(self):
		self.assertIn(".rp-dir-mixed { background: var(--rp-color-mixed-container)", self.source)

	def test_the_dark_theme_covers_the_badge_too(self):
		self.assertIn("rp-dark .rp-dir-mixed", self.source)


class TestPerLegMinutesSurviveARefresh(FrappeTestCase):
	"""Feedback on WI-002074: the minutes typed into the modal had nowhere to live.

	They positioned one block and were then dropped. Merging a third card onto a run
	reopened the modal on defaults, the Shipment Details panel never mentioned them, and
	the manifest reported whatever spacing the blocks happened to have.
	"""

	def setUp(self):
		self.canvas = CANVAS.read_text()
		self.server = CANVAS_SERVER.read_text()
		self.manifest = MANIFEST.read_text()

	def test_timings_keyed_by_card_id_reach_the_right_shipment(self):
		# The canvas has to be able to seed saved timings before the first preview, and
		# all it knows its blocks by then is the card id.
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			_timings_by_shipment,
		)

		leg = {"transit_minutes": 20, "buffer_minutes": 5}

		self.assertEqual(_timings_by_shipment({"TSHIP-TS-0001": leg}), {"TS-0001": leg})
		self.assertEqual(_timings_by_shipment({"TS-0001": leg}), {"TS-0001": leg})
		self.assertEqual(_timings_by_shipment(None), {})

	def test_a_leg_defaults_to_the_transit_the_canvas_would_have_used(self):
		# The modal used to print 0 while the canvas quietly placed the block on 30, so
		# the itinerary shown was never the run that got drawn.
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			DEFAULT_TRANSIT_MINUTES,
		)

		self.assertEqual(DEFAULT_TRANSIT_MINUTES, 30)
		self.assertIn("default_transit = 0 if index == 1 else DEFAULT_TRANSIT_MINUTES", (
			pathlib.Path(frappe.get_app_path(
				"one_fm", "one_fm", "doctype", "transportation_shipment",
				"transportation_shipment.py"
			)).read_text()
		))

	def test_the_block_carries_the_minutes_it_was_placed_on(self):
		self.assertIn("bufferMinutes: Math.round(bufferMs / 60000),", self.canvas)
		self.assertIn("transitMinutes: Math.round(durMs / 60000),", self.canvas)

	def test_the_two_numbers_have_one_name(self):
		# The placement stamped bufferMin/transitMin, which nothing read and nothing
		# saved, so a card placed on 60/15 opened the merge modal on defaults.
		self.assertNotIn("bufferMin:", self.canvas)
		self.assertNotIn("transitMin:", self.canvas)

	def test_the_merge_takes_them_from_the_leg_the_operator_edited(self):
		self.assertIn("transitMinutes: parseInt(adj.transit_minutes, 10) || 0,", self.canvas)
		self.assertIn("bufferMinutes: parseInt(adj.buffer_minutes, 10) || 0,", self.canvas)

	def test_confirming_re_times_the_whole_run(self):
		# The numbers are the run's timing, not a note about it.
		self.assertIn("self._retimeTrip(tripId);", self.canvas)
		self.assertIn("_retimeTrip(tripId) {", self.canvas)

	def test_a_return_run_is_pinned_at_its_start_not_its_end(self):
		# Pinning a return run at its end would move the collection off the shift end.
		self.assertIn("if (this._ownDirection(stops[0]) === 'RETURN') {", self.canvas)

	def test_every_stop_of_the_run_is_stamped_not_just_the_new_one(self):
		# Matched by shipment now that a leg belongs to a stop rather than to a card.
		self.assertIn("const leg = legs[shipmentOf(item.cardId)];", self.canvas)

	def test_the_save_and_the_reload_agree_on_the_field_names(self):
		self.assertIn('"transit_minutes":         item.get("transitMinutes") or 0', self.server)
		self.assertIn('"transitMinutes": row.transit_minutes or 0', self.server)
		self.assertIn('"bufferMinutes": row.buffer_minutes or 0', self.server)

	def test_the_modal_reopens_on_what_was_saved(self):
		self.assertIn("timings[item.cardId] = {", self.canvas)

	def test_the_shipment_details_panel_reports_them(self):
		self.assertIn("min transit", self.canvas)
		self.assertIn("min buffer", self.canvas)

	def test_the_manifest_prefers_the_entered_minutes_over_the_clock_gap(self):
		self.assertIn("function calcTransit(t1, t2, stop)", self.manifest)
		self.assertIn("travelDuration: transit * 60", self.manifest)
		self.assertIn("buffer", self.manifest)


class TestTheRunIsTimedFromTheMinutes(FrappeTestCase):
	"""The rule the modal prints and the canvas draws, on the numbers from the feedback.

	A card placed on 15 buffer + 60 transit sits 12:45 - 14:00 on the lane. Merging a
	return card onto it and setting the first leg to 60/10 and the second to 15/5 has to
	move the run to 12:50 - 14:20: the first stop still arrives at 14:00 because that is
	the shift it exists to hit, but it now leaves five minutes later, and the second stop
	follows on its own dwell and drive. Before this the modal accepted the numbers and the
	blocks kept the ones they were dropped with.
	"""

	def _walk(self, legs, anchor="14:00"):
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			_clock,
			walk_legs,
		)

		hours, minutes = (int(part) for part in anchor.split(":"))
		return [
			(_clock(departs), _clock(arrives))
			for departs, arrives in walk_legs(legs, hours * 3600 + minutes * 60)
		]

	def test_the_feedbacks_merge(self):
		# A leg now departs when the bus is released from the stop before it, with its
		# buffer counted as dwell inside the leg (WI-002151). The arrivals are the same
		# numbers as before; only the departure column moved, so that AC 1.1's
		# Arrival = Departure + Buffer + Transit reads literally - which is how the
		# process owner's sample itinerary is walked.
		self.assertEqual(
			self._walk([(60, 10), (15, 5)]),
			[("12:50", "14:00"), ("14:00", "14:20")],
		)

	def test_the_placement_that_preceded_it(self):
		# 15 buffer + 60 transit, arriving on a 14:00 shift: the block the operator saw.
		self.assertEqual(self._walk([(60, 15)]), [("12:45", "14:00")])

	def test_the_first_stop_keeps_its_arrival_whatever_its_minutes_say(self):
		# Its minutes decide when the run leaves, never when it is due on site.
		for legs in ([(60, 10)], [(90, 0)], [(5, 5)]):
			self.assertEqual(self._walk(legs)[0][1], "14:00")

	def test_an_edit_high_up_the_run_moves_everything_after_it(self):
		relaxed = self._walk([(60, 10), (15, 5), (20, 5)])
		stretched = self._walk([(90, 10), (15, 5), (20, 5)])

		# The anchor holds, so a longer first drive only moves the departure.
		self.assertEqual(relaxed[0][1], stretched[0][1])
		self.assertEqual(stretched[0][0], "12:20")
		# ...and the stops after it are unmoved, because they hang off that arrival.
		self.assertEqual(relaxed[1:], stretched[1:])

	def test_a_later_stops_dwell_pushes_the_stops_after_it(self):
		self.assertEqual(
			self._walk([(60, 10), (15, 30), (20, 5)])[2],
			("14:45", "15:10"),   # stop 2's 30min dwell pushed this leg back half an hour
		)

	def test_a_dwell_lengthens_its_own_leg_rather_than_delaying_its_departure(self):
		# The same total either way - what changed is which column the buffer shows in.
		lazy = self._walk([(60, 10), (15, 30)])

		self.assertEqual(lazy[1][0], lazy[0][1])            # departs when stop 1 is done
		self.assertEqual(lazy[1], ("14:00", "14:45"))       # 30 dwell + 15 drive

	def test_an_empty_run_walks_to_nothing(self):
		self.assertEqual(self._walk([]), [])


class TestATripIsJoinedWhole(FrappeTestCase):
	"""Proximity chooses WHICH run to join, never how much of it takes part.

	A trip whose stops spread wider than the two-hour proximity window used to arrive at
	the merge half-present: the modal drew half an itinerary, the seat walk counted half
	the riders - S-803 read as 3 stops peaking at 6 against a run of 9 peaking at 11 -
	and the merge marked only those stops Mixed, leaving the rest on their old heading.
	"""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_grouped_trip_is_expanded_to_all_of_its_stops(self):
		self.assertIn("tripMap[key] = this.swimItems.filter(", self.source)
		self.assertIn("i.vehicleId === vehicle.id && i.tripId === key", self.source)

	def test_a_standalone_block_is_left_as_itself(self):
		# Items with no tripId are each their own trip and must not be swept together.
		self.assertIn("if (key.startsWith('_solo_')) return;", self.source)

	def test_the_expansion_happens_before_the_operator_is_asked(self):
		# The picker and the confirm both read tripMap, so it has to be whole by then.
		self.assertLess(
			self.source.index("tripMap[key] = this.swimItems.filter("),
			self.source.index("const tripKeys = Object.keys(tripMap);"),
		)


class TestTheModalOpensOnTheRunAsItStands(FrappeTestCase):
	"""What the operator is shown before they agree to anything.

	The confirm named only the stops proximity had picked out while the merge took the
	whole trip - so a three-stop run was described as two. And a leg that carries no
	recorded minutes still has a length on the lane: sending nothing for it collapsed it,
	and S-302's 07:00-09:00 run opened as 08:00-09:00 with its first hour gone.
	"""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_confirm_names_every_stop_the_merge_will_take(self):
		self.assertIn("const existingStops = tripMap[tripKeys[0]].map(", self.source)
		self.assertNotIn("const existingStops = nearbyBlocks.map(", self.source)

	def test_a_leg_with_no_recorded_minutes_sends_the_length_it_is_drawn_with(self):
		self.assertIn("transit_minutes: span, buffer_minutes: 0", self.source)

	def test_a_leg_that_has_minutes_still_sends_those(self):
		# Real minutes always win; the span is only the fallback for an untimed leg.
		self.assertIn("if (item.transitMinutes || item.bufferMinutes) {", self.source)


class TestWhatAMergeWritesBack(FrappeTestCase):
	"""The minutes typed into the modal have to land on the blocks that get saved.

	The modal times the leg OUT of a stop, the way the sample sheet reads, but a block is
	drawn from the drive that BROUGHT the bus to it. Keying the write-back on each stop's
	own card gave every block the drive away from it, and the newly merged card - which is
	nobody's inbound leg - got nothing at all, saving with 0/0 and a blank trip name.
	"""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_a_row_keeps_the_minutes_typed_against_it(self):
		# One framing everywhere: a row's minutes are the drive AWAY from it, as the
		# sample sheet reads and as the modal is typed. Storing the inbound drive meant
		# the number typed against DHL Ardiya came back on the Kuwait Airways block.
		self.assertIn("(stop.cards || []).forEach((shipment) => { legs[shipment] = stop; });", self.source)

	def test_a_block_is_laid_out_from_the_stop_before_it(self):
		# Which is where the drive to it is recorded.
		self.assertIn("const { buffer, transit } = leg(stops[position]);", self.source)

	def test_the_write_back_matches_a_block_to_its_shipment(self):
		# Stops carry shipment names; blocks carry TSHIP- card ids.
		self.assertIn("const shipmentOf = (cardId) =>", self.source)
		self.assertIn("legs[shipmentOf(item.cardId)]", self.source)

	def test_a_merged_block_joins_the_run_by_name_too(self):
		self.assertIn("tripName: existingItems.find((i) => i.tripName)?.tripName || null,", self.source)
