# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002071: merging cards into a Mixed trip, and holding every leg to the seats."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
	MIXED,
	arrival_order,
	arrival_time,
	merge_key,
)
from one_fm.operations.doctype.route_plan.route_plan import (
	MIXED_DIRECTION,
	RoutePlan,
	_card_direction,
	_normalize_shipment_direction,
	_peak_concurrent_headcount,
	_row_direction,
	_trip_occupancy,
)
from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	_normalize_direction,
)


class TestMergeKey(FrappeTestCase):
	def test_the_key_is_shared_by_every_member(self):
		self.assertEqual(merge_key(["TS-0001", "TS-0002"]), merge_key(["TS-0001", "TS-0002"]))

	def test_the_key_does_not_depend_on_the_order_cards_were_dropped(self):
		# Merging the same set twice must not leave two halves pointing at different groups.
		self.assertEqual(merge_key(["TS-0002", "TS-0001"]), merge_key(["TS-0001", "TS-0002"]))

	def test_a_different_set_gets_a_different_key(self):
		self.assertNotEqual(merge_key(["TS-0001", "TS-0002"]), merge_key(["TS-0001", "TS-0003"]))

	def test_the_key_fits_a_data_field(self):
		many = [f"TS-{n:04d}" for n in range(50)]

		self.assertLessEqual(len(merge_key(many)), 140)


class TestArrivalOrder(FrappeTestCase):
	def _card(self, name, start_time, trip_direction=None, end_time=None):
		return frappe._dict(
			name=name, start_time=start_time, end_time=end_time, trip_direction=trip_direction
		)

	def test_a_return_card_is_reached_when_its_shift_ends(self):
		# The reported bug: a 06:00-14:00 return shipment is a 14:00 collection, but sorting
		# on start_time put it at the head of the run. The modal then walked "board 5, then
		# drop 2", peaked at 7 on a 6-seat van and refused a merge that fits.
		self.assertEqual(
			arrival_time(self._card("TS-0306", 6 * 3600, "Return", 14 * 3600)), 14 * 3600
		)

	def test_an_outward_card_is_reached_by_its_shift_start(self):
		self.assertEqual(
			arrival_time(self._card("TS-0659", 14 * 3600, "Outward", 0)), 14 * 3600
		)

	def test_the_drop_off_comes_before_the_collection_it_shares_a_time_with(self):
		cards = [
			self._card("TS-0306", 6 * 3600, "Return", 14 * 3600),
			self._card("TS-0659", 14 * 3600, "Outward", 0),
		]

		self.assertEqual(
			[c.name for c in sorted(cards, key=arrival_order)], ["TS-0659", "TS-0306"]
		)

	def test_an_overnight_collection_falls_the_next_morning(self):
		# A 22:00-06:00 return is collected at 06:00 the following day, not before the
		# shift it is collecting from ever started.
		self.assertEqual(
			arrival_time(self._card("TS-0048", 22 * 3600, "Return", 6 * 3600)), 30 * 3600
		)

	def test_a_return_with_no_end_time_falls_back_to_its_start(self):
		self.assertEqual(arrival_time(self._card("TS-x", 9 * 3600, "Return", None)), 9 * 3600)

	def test_cards_order_by_scheduled_arrival(self):
		cards = [self._card("TS-2", 8 * 3600), self._card("TS-1", 5 * 3600)]

		self.assertEqual([c.name for c in sorted(cards, key=arrival_order)], ["TS-1", "TS-2"])

	def test_a_card_with_no_time_sorts_last_not_first(self):
		# An unscheduled card must not silently claim the head of the itinerary.
		cards = [self._card("TS-2", None), self._card("TS-1", 9 * 3600)]

		self.assertEqual([c.name for c in sorted(cards, key=arrival_order)], ["TS-1", "TS-2"])

	def test_ties_break_on_name_so_the_order_is_stable(self):
		cards = [self._card("TS-9", 6 * 3600), self._card("TS-3", 6 * 3600)]

		self.assertEqual([c.name for c in sorted(cards, key=arrival_order)], ["TS-3", "TS-9"])


class TestDirectionVocabularies(FrappeTestCase):
	"""MIXED has to be recognised, not defaulted."""

	def test_the_canvas_helper_knows_mixed(self):
		self.assertEqual(_normalize_direction("Mixed"), "MIXED")
		self.assertEqual(_normalize_direction("MIXED"), "MIXED")

	def test_the_canvas_helper_still_maps_the_original_two(self):
		self.assertEqual(_normalize_direction("Outward"), "OUTBOUND")
		self.assertEqual(_normalize_direction("OUTBOUND"), "OUTBOUND")
		self.assertEqual(_normalize_direction("Return"), "RETURN")
		self.assertEqual(_normalize_direction("RETURN"), "RETURN")

	def test_a_blank_direction_is_still_treated_as_outbound(self):
		self.assertEqual(_normalize_direction(""), "OUTBOUND")
		self.assertEqual(_normalize_direction(None), "OUTBOUND")

	def test_mixed_no_longer_falls_through_to_outbound(self):
		# The regression this fixes: the old two-way test answered "not a return, so
		# outbound", which drew a merged card orange and mismatched the status sync.
		self.assertNotEqual(_normalize_direction("Mixed"), "OUTBOUND")

	def test_the_route_plan_helper_agrees_with_the_canvas_one(self):
		for value in ("Outward", "Return", "Mixed", "", None):
			with self.subTest(value=value):
				self.assertEqual(_normalize_shipment_direction(value), _normalize_direction(value))

	def test_mixed_is_the_shipment_option_the_doctype_offers(self):
		options = frappe.get_meta("Transportation Shipment").get_field("trip_direction").options
		self.assertIn(MIXED, options.split("\n"))

	def test_the_shipment_carries_the_shared_group_key(self):
		field = frappe.get_meta("Transportation Shipment").get_field("trip_group")
		self.assertIsNotNone(field, "Transportation Shipment has no trip_group field")
		self.assertTrue(field.read_only)


class TestTheAssignmentRowSpeaksMixed(FrappeTestCase):
	"""The regression the reporter hit on Confirm & Merge Trip.

	`_row_direction` collapsed anything that was not a return to OUTBOUND, so a merged
	trip keyed as an outbound one, took the summing branch instead of the leg walk, and
	the save answered "the outbound run on VHL-L-0004 carries 7 passengers but the
	vehicle takes 6" for a run that never carries more than 5 at once.
	"""

	def _row(self, direction):
		return frappe._dict(direction=direction)

	def test_a_merged_row_keeps_its_own_direction(self):
		self.assertEqual(_row_direction(self._row("MIXED")), MIXED_DIRECTION)

	def test_mixed_no_longer_falls_through_to_outbound(self):
		self.assertNotEqual(_row_direction(self._row("MIXED")), "OUTBOUND")

	def test_the_two_original_directions_still_map(self):
		self.assertEqual(_row_direction(self._row("OUTBOUND")), "OUTBOUND")
		self.assertEqual(_row_direction(self._row("RETURN")), "RETURN")

	def test_a_blank_row_is_still_treated_as_outbound(self):
		# A stray or missing value must not drop a leg out of the capacity cluster.
		self.assertEqual(_row_direction(self._row("")), "OUTBOUND")
		self.assertEqual(_row_direction(self._row(None)), "OUTBOUND")

	def test_the_row_and_the_shipment_agree(self):
		for value in ("OUTBOUND", "RETURN", "MIXED", "", None):
			with self.subTest(value=value):
				self.assertEqual(_row_direction(self._row(value)), _normalize_shipment_direction(value))


class TestWhichWayAMergedCardsRidersTravel(FrappeTestCase):
	"""The leg walk needs each card's own direction, which merging overwrites."""

	def test_an_unmerged_card_answers_for_itself(self):
		self.assertEqual(_card_direction("Outward", None), "OUTBOUND")
		self.assertEqual(_card_direction("Return", None), "RETURN")

	def test_a_merged_card_answers_from_what_the_merge_recorded(self):
		# Without this every card on a merged trip read as OUTBOUND, so the walk put
		# all of them aboard at the camp and peaked at the full total again.
		self.assertEqual(_card_direction("Mixed", "Return"), "RETURN")
		self.assertEqual(_card_direction("Mixed", "Outward"), "OUTBOUND")

	def test_a_merged_card_with_no_record_is_counted_conservatively(self):
		# Aboard from the camp over-reports rather than passing a run that cannot fit.
		self.assertEqual(_card_direction("Mixed", None), "OUTBOUND")

	def test_the_live_direction_wins_once_a_card_is_unmerged(self):
		# unmerge_trip_shipment clears the record; a stale one must not outrank the card.
		self.assertEqual(_card_direction("Outward", "Return"), "OUTBOUND")


class TestOverlappingTripsMeasureAMergedRunByItsPeak(FrappeTestCase):
	"""The second half of the reporter's block.

	Once the per-trip check took the leg walk, the save still refused with "Total
	overlapping passengers (7) exceeds vehicle limit (6)" - the concurrency check was
	still adding `headcount`, which for a merged trip is the total it ever carried and
	not a number the bus is ever asked to hold.
	"""

	def _trip(self, direction, headcount, occupancy=None, start=0, end=3600):
		return frappe._dict(
			key=(direction, headcount), vehicle="V-1", direction=direction,
			headcount=headcount, occupancy=occupancy, start=start, end=end,
			live_from=None, live_to=None, rows=[],
		)

	def test_a_single_direction_trip_is_its_headcount(self):
		self.assertEqual(_trip_occupancy(self._trip("OUTBOUND", 12)), 12)

	def test_a_merged_trip_is_its_busiest_leg(self):
		self.assertEqual(_trip_occupancy(self._trip(MIXED_DIRECTION, 24, occupancy=12)), 12)

	def test_a_trip_that_was_never_measured_falls_back_to_its_headcount(self):
		self.assertEqual(_trip_occupancy(self._trip("RETURN", 9, occupancy=None)), 9)

	def test_an_empty_merged_trip_is_not_mistaken_for_unmeasured(self):
		# occupancy 0 is a measurement, not a missing one - `or headcount` would have
		# quietly substituted the total here.
		self.assertEqual(_trip_occupancy(self._trip(MIXED_DIRECTION, 7, occupancy=0)), 0)

	def test_the_merged_run_from_the_report_fits_alongside_nothing_else(self):
		trip = self._trip(MIXED_DIRECTION, 7, occupancy=5)

		self.assertEqual(_peak_concurrent_headcount([trip]), 5)

	def test_two_overlapping_trips_still_add_up(self):
		# The leg walk must not turn a genuine double-booking into a pass.
		trips = [self._trip("OUTBOUND", 4), self._trip("RETURN", 5)]

		self.assertEqual(_peak_concurrent_headcount(trips), 9)

	def test_a_merged_trip_overlapping_another_adds_its_peak_not_its_total(self):
		trips = [self._trip(MIXED_DIRECTION, 24, occupancy=12), self._trip("OUTBOUND", 3)]

		self.assertEqual(_peak_concurrent_headcount(trips), 15)


class TestMixedLegCapacity(FrappeTestCase):
	"""The peak on any one leg is what has to fit, not everyone the trip ever carried."""

	def _plan(self, rows):
		plan = frappe.new_doc("Route Plan")
		plan.assignments = []
		for index, (shipment, headcount) in enumerate(rows, start=1):
			plan.append("assignments", {
				"transportation_shipment": shipment,
				"vehicle": "V-1",
				"direction": MIXED_DIRECTION,
				"trip_group": "MIX-test",
				"stop_index": index,
				"headcount": headcount,
			})
		return plan

	def _trip(self, plan, directions):
		rows = list(plan.assignments)
		trip = frappe._dict(
			key=("V-1", "MIX-test", MIXED_DIRECTION), vehicle="V-1",
			direction=MIXED_DIRECTION,
			headcount=sum(r.headcount for r in rows), rows=rows,
		)
		self._directions = directions
		return trip

	def _check(self, plan, trip, limit):
		"""Run the leg walk with the shipment directions stubbed."""
		import one_fm.operations.doctype.route_plan.route_plan as mod

		real = mod._shipment_directions
		mod._shipment_directions = lambda names: self._directions
		try:
			RoutePlan._validate_mixed_trip_legs(plan, trip, limit)
		finally:
			mod._shipment_directions = real

	def test_a_drop_then_a_pick_up_never_ride_together(self):
		# 12 out, dropped at stop 1; 12 boarded at stop 2. Summed that is 24 and would be
		# refused; the bus never carries more than 12 at once.
		plan = self._plan([("TS-A", 12), ("TS-B", 12)])
		trip = self._trip(plan, {"TS-A": "OUTBOUND", "TS-B": "RETURN"})

		self._check(plan, trip, limit=12)

	def test_the_busiest_leg_is_what_is_refused(self):
		plan = self._plan([("TS-A", 12), ("TS-B", 12)])
		trip = self._trip(plan, {"TS-A": "OUTBOUND", "TS-B": "RETURN"})

		with self.assertRaises(frappe.ValidationError):
			self._check(plan, trip, limit=11)

	def test_disembarking_is_applied_before_boarding_at_a_shared_stop(self):
		# Both cards stop at the same place: 10 off, then 10 on. Adding first would peak
		# at 20 and refuse a run that never exceeds 10.
		plan = self._plan([("TS-A", 10), ("TS-B", 10)])
		for row in plan.assignments:
			row.stop_index = 1
		trip = self._trip(plan, {"TS-A": "OUTBOUND", "TS-B": "RETURN"})

		self._check(plan, trip, limit=10)

	def test_two_outward_cards_still_ride_together(self):
		# Both loads leave the camp on the same bus, so they do sum - the leg walk must
		# not turn a genuine overload into a pass.
		plan = self._plan([("TS-A", 10), ("TS-B", 10)])
		trip = self._trip(plan, {"TS-A": "OUTBOUND", "TS-B": "OUTBOUND"})

		with self.assertRaises(frappe.ValidationError):
			self._check(plan, trip, limit=15)

	def test_two_return_cards_peak_when_the_last_one_boards(self):
		plan = self._plan([("TS-A", 8), ("TS-B", 8)])
		trip = self._trip(plan, {"TS-A": "RETURN", "TS-B": "RETURN"})

		self._check(plan, trip, limit=16)
		with self.assertRaises(frappe.ValidationError):
			self._check(plan, trip, limit=15)

	def test_a_loop_that_revisits_a_stop_is_measured_leg_by_leg(self):
		# Camp -> Stop1 drop 10 -> Stop2 drop 12 -> Stop1 board 10 -> Camp.
		# Total carried is 32; the peak leg is the 22 that leave the camp.
		plan = self._plan([("TS-A", 10), ("TS-B", 12), ("TS-C", 10)])
		trip = self._trip(plan, {"TS-A": "OUTBOUND", "TS-B": "OUTBOUND", "TS-C": "RETURN"})

		self._check(plan, trip, limit=22)
		with self.assertRaises(frappe.ValidationError):
			self._check(plan, trip, limit=21)

	def test_the_error_names_the_failing_leg(self):
		plan = self._plan([("TS-A", 10), ("TS-B", 12), ("TS-C", 10)])
		trip = self._trip(plan, {"TS-A": "OUTBOUND", "TS-B": "OUTBOUND", "TS-C": "RETURN"})

		with self.assertRaises(frappe.ValidationError) as caught:
			self._check(plan, trip, limit=21)

		self.assertIn("leg", str(caught.exception).lower())

	def test_rows_are_walked_in_stop_order_not_table_order(self):
		plan = self._plan([("TS-A", 20), ("TS-B", 20)])
		plan.assignments[0].stop_index = 2   # the board
		plan.assignments[1].stop_index = 1   # the drop
		trip = self._trip(plan, {"TS-A": "RETURN", "TS-B": "OUTBOUND"})

		# Drop 20 first, then board 20: never more than 20 aboard.
		self._check(plan, trip, limit=20)


class TestAMergeCanBeUndone(FrappeTestCase):
	"""The regression the reporter hit: an Outward card merged once stayed Mixed for good.

	It came back to the unassigned pool describing a journey it no longer had, and no amount
	of re-planning restored it.
	"""

	def test_the_shipment_remembers_the_way_it_travelled(self):
		field = frappe.get_meta("Transportation Shipment").get_field("pre_merge_trip_direction")

		self.assertIsNotNone(field, "nothing records the pre-merge direction")
		self.assertEqual(field.options.split("\n"), ["", "Outward", "Return"])
		self.assertTrue(field.read_only)
		self.assertTrue(field.hidden)

	def test_leaving_a_merged_trip_restores_the_original(self):
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			unmerge_trip_shipment,
		)

		name = frappe.db.get_value("Transportation Shipment", {}, "name")
		if not name:
			self.skipTest("No Transportation Shipment on this site")
		before = frappe.db.get_value("Transportation Shipment", name, "trip_direction")

		frappe.db.set_value("Transportation Shipment", name, {
			"trip_direction": MIXED, "trip_group": "MIX-test", "pre_merge_trip_direction": "Outward",
		}, update_modified=False)

		self.assertTrue(unmerge_trip_shipment(name))
		restored = frappe.db.get_value(
			"Transportation Shipment", name,
			["trip_direction", "trip_group", "pre_merge_trip_direction"], as_dict=True,
		)

		self.assertEqual(restored.trip_direction, "Outward")
		self.assertFalse(restored.trip_group)
		self.assertFalse(restored.pre_merge_trip_direction)

		frappe.db.set_value("Transportation Shipment", name, "trip_direction", before,
		                    update_modified=False)

	def test_a_card_that_was_never_merged_is_left_alone(self):
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			unmerge_trip_shipment,
		)

		# Has to be a card that is actually unmerged: a merged one left on the site by a
		# real plan would otherwise decide this test's result.
		name = frappe.db.get_value(
			"Transportation Shipment", {"pre_merge_trip_direction": ["is", "not set"]}, "name"
		)
		if not name:
			self.skipTest("No unmerged Transportation Shipment on this site")
		before = frappe.db.get_value("Transportation Shipment", name, "trip_direction")

		# Safe to call for every shipment a plan drops, merged or not.
		self.assertFalse(unmerge_trip_shipment(name))
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "trip_direction"), before
		)

	def test_a_refused_save_can_roll_the_merge_back_from_the_canvas(self):
		"""The window the reporter fell into.

		Confirm & Merge Trip writes the shipments, then the plan saves - and the save can
		still be refused. The merge is already committed by then, so without this the
		cards sit Mixed with no plan holding them.
		"""
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			undo_merge,
		)

		frappe.is_whitelisted(undo_merge)

		name = frappe.db.get_value(
			"Transportation Shipment", {"pre_merge_trip_direction": ["is", "not set"]}, "name"
		)
		if not name:
			self.skipTest("No unmerged Transportation Shipment on this site")

		frappe.db.set_value("Transportation Shipment", name, {
			"trip_direction": MIXED, "trip_group": "MIX-test", "pre_merge_trip_direction": "Return",
		}, update_modified=False)

		# Card ids, because that is what the canvas holds.
		result = undo_merge([f"TSHIP-{name}"])

		self.assertEqual(result["restored"], [name])
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "trip_direction"), "Return"
		)

	def test_rolling_back_a_merge_that_never_happened_changes_nothing(self):
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			undo_merge,
		)

		name = frappe.db.get_value(
			"Transportation Shipment", {"pre_merge_trip_direction": ["is", "not set"]}, "name"
		)
		if not name:
			self.skipTest("No unmerged Transportation Shipment on this site")
		before = frappe.db.get_value("Transportation Shipment", name, "trip_direction")

		self.assertEqual(undo_merge([name])["restored"], [])
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "trip_direction"), before
		)

	def test_a_shipment_that_no_longer_exists_is_skipped(self):
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			undo_merge,
		)

		self.assertEqual(undo_merge(["TSHIP-TS-does-not-exist"])["restored"], [])

	def test_the_generation_key_records_the_original_direction(self):
		"""What the repair patch recovers a stranded record from.

		The generator ends the key with the direction it built the card for, and merging
		never rewrote it.
		"""
		row = frappe.db.get_value(
			"Transportation Shipment",
			{"generation_key": ["is", "set"], "trip_direction": ["in", ["Outward", "Return"]]},
			["generation_key", "trip_direction"], as_dict=True,
		)
		if not row:
			self.skipTest("No generated shipment on this site")

		self.assertEqual(row.generation_key.rsplit("|", 1)[-1].strip(), row.trip_direction)

	def test_no_shipment_is_left_stranded_as_mixed(self):
		# A Mixed shipment on no plan is stale by definition: nothing is scheduling it as a
		# merged trip.
		for row in frappe.get_all(
			"Transportation Shipment", filters={"trip_direction": "Mixed"}, fields=["name"]
		):
			with self.subTest(shipment=row.name):
				self.assertTrue(
					frappe.db.count("Route Plan Assignment", {"transportation_shipment": row.name}),
					f"{row.name} is Mixed but on no Route Plan",
				)
