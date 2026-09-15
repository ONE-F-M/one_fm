# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The canvas seat rule, and the drawer actions around it (WI-002401).

The seat check on the board and the one on save must not be able to disagree, or the
canvas accepts a drop the save then refuses. The rule itself is exercised end to end by
``transportation_schedule/test_seat_rule.js`` (``node test_seat_rule.js``), which reads
the shipped helpers rather than copying them; what is asserted here is that the canvas
keeps asking the question the right way round.
"""

import pathlib
import subprocess
import sys

import frappe
from frappe.tests.utils import FrappeTestCase

CANVAS_DIR = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule"))
CANVAS = CANVAS_DIR / "transportation_schedule.js"


class TestTheSeatRuleSelfCheckPasses(FrappeTestCase):
	def test_the_node_self_check_passes(self):
		check = CANVAS_DIR / "test_seat_rule.js"
		self.assertTrue(check.exists(), "the seat-rule self-check is missing")
		try:
			result = subprocess.run(
				["node", str(check)], capture_output=True, text=True, timeout=60
			)
		except FileNotFoundError:
			self.skipTest("node is not available on this machine")
		self.assertEqual(
			result.returncode, 0,
			f"node {check.name} failed:\n{result.stdout}\n{result.stderr}",
		)


class TestCapacityIsJudgedPerRun(FrappeTestCase):
	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_daily_window_is_read_in_the_sites_own_clock(self):
		# The DATE half of a lane stamp is the multi-day lock lifespan, not the day the
		# bus runs, so runs are compared by the hour they are on the road. Comparing raw
		# epochs made a run whose lock began last month invisible to the check.
		self.assertIn("_dayWindow(start, end)", self.source)
		self.assertIn("timeZone: 'Asia/Kuwait'", self.source)
		self.assertIn("if (to <= from) to += DAY;", self.source)

	def test_overlap_is_circular_over_the_day(self):
		# So a run past midnight still meets an early-morning one, and two runs that
		# merely touch do not - a bus can turn straight around.
		self.assertIn("_sharesTheRoad(a, b)", self.source)
		self.assertIn("[-DAY, 0, DAY].some(shift => a.from < b.to + shift && b.from + shift < a.to)",
					  self.source)

	def test_the_run_being_joined_is_not_counted_twice(self):
		self.assertIn("seatLoad(vehicleId, occupancy, { joining, window } = {})", self.source)
		self.assertIn("t !== target && this._sharesTheRoad(road, t.window)", self.source)

	def test_a_drop_is_not_refused_before_the_run_is_chosen(self):
		# handleDrop offers a picker and, for a merge, the Trip Builder. Judging the drop
		# against a pooled load first refused it before the operator could choose and
		# pre-empted the modal (issue 3 on the ticket).
		self.assertIn("// No seat check here.", self.source)
		self.assertNotIn("tripsDuringCardWindows", self.source)
		self.assertNotIn("peakLoadDuringCardWindows", self.source)
		self.assertNotIn("cardLegWindow", self.source)

	def test_a_card_too_big_for_the_seats_it_can_have_is_split_not_refused(self):
		# Sized on the seats the drop can actually have, at each of handleDrop's three
		# endings rather than once up front on the whole bus (WI-002401 item 1) - see
		# test_overcapacity_card_split for the flow.
		self.assertIn("_splitIfOver(card, vehicle, joining, next) {", self.source)
		self.assertIn("if (card.headcount <= free) return false;", self.source)
		self.assertNotIn("if (card.headcount > this.passengerSeats(vehicle)) {", self.source)

	def test_a_chain_is_judged_on_the_run_it_joins(self):
		self.assertIn("this.mergedOccupancy(existingItems, newCard)", self.source)
		self.assertIn("{ joining: existingItems }", self.source)

	def test_a_cross_direction_merge_is_walked_leg_by_leg(self):
		# A return card boards the seats the outward load has just left, so adding the
		# two refused a merge the bus can make.
		self.assertIn("mergedOccupancy(stops, card)", self.source)
		self.assertIn("direction: this.runDirection(merged)", self.source)

	def test_the_lane_colours_each_run_on_its_own_load(self):
		self.assertIn("o !== t && this._sharesTheRoad(t.window, o.window)", self.source)
		self.assertIn("if (load > seats) t.stops.forEach(s => over.add(s.id));", self.source)

	def test_a_cross_lane_drag_is_judged_before_the_block_moves(self):
		# Setting vehicleId first counted the block against itself on the target lane.
		self.assertIn("{ window: this._dayWindow(item.start, item.end) }", self.source)
		self.assertIn("item.vehicleId = targetVehicleId;", self.source)

	def test_the_refusal_says_why_each_run_was_counted(self):
		self.assertIn("Counted for this drop: {0}.", self.source)
		self.assertIn("is not counted against it", self.source)


class TestTheDrawerActions(FrappeTestCase):
	def setUp(self):
		self.source = CANVAS.read_text()

	def test_a_run_can_be_re_timed_without_taking_it_apart(self):
		# AC6: the Trip Builder is also the run's own editor.
		self.assertIn("editSelectedTrip()", self.source)
		self.assertIn("Edit Trip Timings", self.source)
		self.assertIn("this._openMergeTripModal(null, stops, item.vehicleId)", self.source)

	def test_editing_a_run_adds_no_stop(self):
		self.assertIn("if (newCard) ids.push(newCard.id);", self.source)
		self.assertIn("if (newCard) self.assignedCards.add(newCard.id);", self.source)

	def test_a_run_that_loses_a_leg_stops_being_mixed(self):
		# AC3: the block colour, the prefix arrow and the drawer badge all read
		# item.direction, and the merge stamped MIXED on every stop.
		self.assertIn("_resyncTripDirection(tripId)", self.source)
		self.assertIn("this._resyncTripDirection(tripId);", self.source)

	def test_a_mixed_run_is_never_guessed_back_to_outbound(self):
		# A stop whose card has left the board has no own heading to read.
		self.assertIn("if (!stops.length || !stops.every(i => i.direction === 'MIXED')) return;",
					  self.source)
		self.assertIn("if (headings.some(h => h !== headings[0])) return;", self.source)


class TestTheRunIsDrawnEndToEnd(FrappeTestCase):
	def setUp(self):
		self.source = CANVAS.read_text()

	def test_a_trip_block_spans_the_whole_journey(self):
		# AC2 / AC4: the bus leaves the camp before any block starts and gets back after
		# the last one ends, and the drawer header already read it that way. Clamped to
		# the stops, and only comparable with them because the plan load rebases the leg
		# timings onto the run's own day - see test_lane_day_rebase.
		self.assertIn("stated(held.departure) ?? Infinity, spanStart.getTime()", self.source)
		self.assertIn("stated(held.arrival) ?? -Infinity, spanEnd.getTime()", self.source)
		self.assertIn("start: runStart,", self.source)
		self.assertIn("end: runEnd,", self.source)

	def test_the_drawer_header_reads_the_same_two_ends(self):
		self.assertIn("const stored = this.selectedTripLegs.departure;", self.source)
		self.assertIn("return this.selectedTripLegs.arrival || this.lastStopEndsAt();", self.source)

	def test_the_existing_trips_list_shows_every_run_on_the_lane(self):
		# AC1: filtering to OUTBOUND hid the return runs the new trip has to fit around,
		# which is what the list is there to show.
		self.assertIn("const existingOnVehicle = this.swimItems.filter(i => i.vehicleId === vehicleId);",
					  self.source)

	def test_a_camp_is_the_front_or_the_back_of_a_run_not_a_stop_between_sites(self):
		# Reading each card as its own camp -> site pair printed the camp once per card:
		# "Mahboula 13 -> Xcite -> Mahboula 13 -> Aramex -> Mahboula 13 -> Stockyard" for
		# a bus that loads at Mahboula 13 once and then makes three drops.
		self.assertIn("const boardsAt = [];", self.source)
		self.assertIn("const deliversTo = [];", self.source)
		self.assertIn("const route = [...boardsAt, ...sites, ...deliversTo];", self.source)
		# The old shape, which stitched a camp in beside every site.
		self.assertNotIn("? [site, camp]", self.source)
		self.assertNotIn(": [camp, site];", self.source)

	def test_a_second_visit_to_one_place_is_still_two_visits(self):
		# Collapsing repeats anywhere would hide a run that genuinely calls at a site
		# twice, which the lane does record.
		self.assertIn("if (sites[sites.length - 1] !== site) sites.push(site);", self.source)

	def test_a_mixed_run_closes_the_loop(self):
		# It both drops off and picks up, so it always comes home - even when no stop
		# could be read as a delivery because its cards have left the pool.
		self.assertIn("if (runDir === 'MIXED' && !deliversTo.length) {", self.source)

	def test_a_placed_card_that_left_the_pool_still_names_its_camp(self):
		# Without this the summary printed the literal word "camp" and the raw card id.
		self.assertIn("accommodation: item._accommodation || '',", self.source)
		self.assertIn("const c = self.bcard(s);", self.source)


class TestATripNameIsUniqueOnItsLane(FrappeTestCase):
	"""WI-002401 item 7. The board's own guard, and the backstop behind it."""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_board_mints_the_next_free_number_not_a_count(self):
		# Counting re-issued a name the moment any run but the last was removed
		# (WI-002160): a lane holding S-201, S-202, S-204, S-205 counted four and
		# offered S-205 again.
		self.assertIn("while (taken.has(name(seq))) seq++;", self.source)
		self.assertNotIn("const nextSeq = existingTripIds.size + 1;", self.source)

	def test_joining_a_run_inherits_its_name_rather_than_minting_one(self):
		# A new number is only ever minted for a NEW run; every chain, merge and
		# reassignment takes the name of the run it joins.
		for inherit in (
			"tripName: existingItems.find((i) => i.tripName)?.tripName || null,",
			"tripId, tripName: existingTripName, stopIndex: totalStops + 1",
		):
			self.assertIn(inherit, self.source)

	def test_the_board_takes_back_the_name_the_save_actually_stored(self):
		# The save is silent, so a server-side repair would otherwise not show until
		# the next reload and would then look like the run renaming itself.
		self.assertIn("_applyStoredTripNames(result)", self.source)
		self.assertIn("callback: (r) => { this._applyStoredTripNames(r.message); },", self.source)
		self.assertIn("already in use on this vehicle", self.source)


class TestTheTripNamePatchIsRegistered(FrappeTestCase):
	def test_the_patch_is_in_patches_txt(self):
		listed = pathlib.Path(frappe.get_app_path("one_fm", "patches.txt")).read_text()
		self.assertIn("one_fm.patches.v15_0.rename_duplicate_trip_names", listed)

	def test_the_patch_reuses_the_rule_the_save_applies(self):
		# Not a second implementation: the patch and the live rule must never disagree
		# about what a correct lane looks like.
		patch = pathlib.Path(frappe.get_app_path(
			"one_fm", "patches", "v15_0", "rename_duplicate_trip_names.py")).read_text()
		self.assertIn("doc._rename_duplicate_trip_names()", patch)
		# Saving the plan would re-run capacity validation on months-old lanes.
		self.assertIn("frappe.db.set_value(", patch)
		self.assertNotIn("doc.save(", patch)


class TestTheItineraryNamesBothMovements(FrappeTestCase):
	"""The Trip Builder card for a handover stop (WI-002401 item 4)."""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_both_counts_are_rendered_not_one_collapsed_number(self):
		self.assertIn("if (s.drop_off_count) {", self.source)
		self.assertIn("if (s.boarding_count) {", self.source)
		# The collapsed field is gone, so nothing can print one movement's label
		# against the other's count.
		self.assertNotIn("esc(s.headcount)", self.source)
		self.assertNotIn("const boarding = s.action === 'Boarding';", self.source)

	def test_drop_off_is_listed_before_boarding(self):
		# The order the bus does it, and the order walk_occupancy measures it in, so the
		# running total below reads straight down from the two numbers.
		self.assertLess(
			self.source.index("__('DROPPING OFF EMPLOYEES')"),
			self.source.index("__('EMPLOYEES BOARDING')"),
		)

	def test_a_stop_where_nothing_happens_still_says_so(self):
		self.assertIn("NOBODY BOARDS OR LEAVES", self.source)


class TestTheBoardStatesTheCapacityItValidates(FrappeTestCase):
	"""Max Passenger Capacity is what every seat check applies (WI-002401 item 3).

	The raw seat count is one higher on a bus whose count includes the driver, so a
	lane advertising the seat count promises a seat the save will refuse. On this site
	that is 22/32135, the RAIZE: 4 seats, driver included, 3 passengers.
	"""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_lane_label_states_the_passenger_capacity(self):
		self.assertIn("{{ passengerSeats(vehicle) }} seats", self.source)
		self.assertNotIn("{{ vehicle.seats }} seats", self.source)

	def test_the_reassign_picker_states_it_too(self):
		self.assertIn("`${v.label} (${this.passengerSeats(v)} seats)`", self.source)
		self.assertNotIn("`${v.label} (${v.seats} seats)`", self.source)

	def test_the_picker_still_parses_its_own_label_back(self):
		# The option text is split on " (" to recover the vehicle, so the number inside
		# the brackets is free to change but the separator is not.
		self.assertIn("vals.target_vehicle.split(' (')[0]", self.source)


class TestASplitCardKeepsItsName(FrappeTestCase):
	"""Three badges that refuse to shrink left "Kuwait Airways - T4" as "K.".

	.rp-card-site is the only flexible item in the header and carries min-width: 0, so
	it absorbs the whole squeeze; SPLIT OVERFLOW is also the longest of the three.
	"""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_split_badge_is_on_its_own_line(self):
		self.assertIn('<div v-if="card.is_split_overflow" class="rp-card-split-row">', self.source)
		self.assertIn(".rp-card-split-row { display: flex; margin-bottom: 4px; }", self.source)

	def test_the_header_keeps_only_the_two_short_badges(self):
		start = self.source.index('<div class="rp-card-header">')
		header = self.source[start:self.source.index("</div>", start)]
		self.assertIn("rp-card-dir", header)
		self.assertIn("rp-card-type", header)
		self.assertNotIn("SPLIT OVERFLOW", header)

	def test_the_name_is_still_the_flexible_one(self):
		# Unchanged: the fix is which badges share the row, not how the name behaves.
		self.assertIn(".rp-card-site   { font-size: 14px; font-weight: 600;", self.source)
		self.assertIn("flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis;",
					  self.source)
