# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002077: what a Route Plan Assignment row stores for a merged trip."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	_assignment_direction,
	_with_stop_indexes,
)


class TestAssignmentSchema(FrappeTestCase):
	def test_direction_offers_mixed(self):
		options = frappe.get_meta("Route Plan Assignment").get_field("direction").options

		self.assertEqual(options.split("\n"), ["", "OUTBOUND", "RETURN", "MIXED"])

	def test_the_row_can_hold_the_shared_group_key(self):
		self.assertIsNotNone(frappe.get_meta("Route Plan Assignment").get_field("trip_group"))

	def test_the_row_can_hold_an_explicit_stop_position(self):
		field = frappe.get_meta("Route Plan Assignment").get_field("stop_index")

		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Int")

	def test_the_modal_s_timings_have_somewhere_to_live(self):
		meta = frappe.get_meta("Route Plan Assignment")

		for fieldname in ("transit_minutes", "buffer_minutes"):
			with self.subTest(fieldname=fieldname):
				field = meta.get_field(fieldname)
				self.assertIsNotNone(field, f"{fieldname} is missing")
				self.assertEqual(field.fieldtype, "Int")


class TestDirectionComesFromTheShipment(FrappeTestCase):
	"""The row's direction is the card's own, not whatever the canvas sent."""

	def test_a_merged_card_writes_mixed(self):
		self.assertEqual(_assignment_direction({"direction": "OUTBOUND"}, "MIXED"), "MIXED")

	def test_the_shipment_wins_over_the_canvas(self):
		# A card dropped in the wrong lane must not be recorded travelling the wrong way.
		self.assertEqual(_assignment_direction({"direction": "OUTBOUND"}, "RETURN"), "RETURN")

	def test_the_two_original_directions_still_map(self):
		self.assertEqual(_assignment_direction({}, "OUTBOUND"), "OUTBOUND")
		self.assertEqual(_assignment_direction({}, "RETURN"), "RETURN")

	def test_a_row_with_no_shipment_keeps_the_canvas_direction(self):
		self.assertEqual(_assignment_direction({"direction": "RETURN"}, None), "RETURN")
		self.assertEqual(_assignment_direction({"direction": "MIXED"}, None), "MIXED")

	def test_a_row_with_neither_falls_back_to_outbound(self):
		self.assertEqual(_assignment_direction({}, None), "OUTBOUND")

	def test_the_shipment_vocabulary_is_translated_not_copied(self):
		# "Outward" is not a value the assignment Select offers; writing it would be
		# rejected. The mapping is why this is not a fetch_from.
		options = frappe.get_meta("Route Plan Assignment").get_field("direction").options.split("\n")

		self.assertNotIn("Outward", options)
		self.assertIn("OUTBOUND", options)


class TestStopIndexing(FrappeTestCase):
	def _item(self, card, group, start, stop_index=0):
		return {"cardId": card, "tripId": group, "start": start, "stopIndex": stop_index}

	def test_merged_rows_are_numbered_in_chronological_order(self):
		items = [
			self._item("c-2", "MIX-1", "2026-08-20 14:00:00"),
			self._item("c-1", "MIX-1", "2026-08-20 06:00:00"),
			self._item("c-3", "MIX-1", "2026-08-20 18:00:00"),
		]

		by_card = {i["cardId"]: i["stopIndex"] for i in _with_stop_indexes(items)}

		self.assertEqual(by_card, {"c-1": 1, "c-2": 2, "c-3": 3})

	def test_the_positions_are_contiguous_from_one(self):
		items = [self._item(f"c-{n}", "MIX-1", f"2026-08-20 0{n}:00:00") for n in range(1, 5)]

		indexes = sorted(i["stopIndex"] for i in _with_stop_indexes(items))

		self.assertEqual(indexes, [1, 2, 3, 4])

	def test_every_row_of_one_trip_shares_the_group_key(self):
		items = [
			self._item("c-1", "MIX-1", "2026-08-20 06:00:00"),
			self._item("c-2", "MIX-1", "2026-08-20 14:00:00"),
		]

		self.assertEqual({i["tripId"] for i in _with_stop_indexes(items)}, {"MIX-1"})

	def test_two_trips_are_numbered_independently(self):
		items = [
			self._item("a-1", "MIX-A", "2026-08-20 06:00:00"),
			self._item("a-2", "MIX-A", "2026-08-20 14:00:00"),
			self._item("b-1", "MIX-B", "2026-08-20 07:00:00"),
			self._item("b-2", "MIX-B", "2026-08-20 15:00:00"),
		]

		by_card = {i["cardId"]: i["stopIndex"] for i in _with_stop_indexes(items)}

		self.assertEqual(by_card, {"a-1": 1, "a-2": 2, "b-1": 1, "b-2": 2})

	def test_a_standalone_card_keeps_the_index_the_canvas_sent(self):
		# One card is its own trip; the canvas already sequences multi-stop runs.
		items = [self._item("solo", "MIX-solo", "2026-08-20 06:00:00", stop_index=7)]

		self.assertEqual(_with_stop_indexes(items)[0]["stopIndex"], 7)

	def test_an_ungrouped_card_is_left_alone(self):
		items = [{"cardId": "loose", "tripId": "", "start": "2026-08-20 06:00:00", "stopIndex": 4}]

		self.assertEqual(_with_stop_indexes(items)[0]["stopIndex"], 4)

	def test_a_member_with_no_start_sorts_last(self):
		items = [
			self._item("c-late", "MIX-1", None),
			self._item("c-first", "MIX-1", "2026-08-20 06:00:00"),
		]

		by_card = {i["cardId"]: i["stopIndex"] for i in _with_stop_indexes(items)}

		self.assertEqual(by_card, {"c-first": 1, "c-late": 2})

	def test_the_order_is_stable_when_two_stops_share_a_time(self):
		items = [
			self._item("c-b", "MIX-1", "2026-08-20 06:00:00"),
			self._item("c-a", "MIX-1", "2026-08-20 06:00:00"),
		]

		by_card = {i["cardId"]: i["stopIndex"] for i in _with_stop_indexes(items)}

		self.assertEqual(by_card, {"c-a": 1, "c-b": 2})
