# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002170: a shift bigger than the bus is two runs, not a refusal.

72 staff dropped onto a 54-seat coaster fills it to its 53 usable seats and the
remaining 19 become a fresh card in the pool, which can itself be split again onto a
smaller vehicle. The roster is MOVED rather than copied, so the two headcounts still add
up to the shift and nobody is boarded twice.
"""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
	split_shipment_for_capacity,
)
from one_fm.overrides.vehicle import passenger_capacity

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))


class TestUsableSeating(FrappeTestCase):
	"""AC 2.2: usable = physical seats less the driver's, when the count includes it."""

	def test_a_54_seater_including_the_driver_takes_53(self):
		self.assertEqual(passenger_capacity(54, True), 53)

	def test_a_22_seater_including_the_driver_takes_21(self):
		self.assertEqual(passenger_capacity(22, True), 21)

	def test_a_count_that_excludes_the_driver_is_taken_as_it_is(self):
		self.assertEqual(passenger_capacity(54, False), 54)


class TestTheSplit(FrappeTestCase):
	"""AC 2.3 / 2.4 / 2.7: what the split controller does to the two cards."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# NOT reload_doc: it commits, which ends the transaction FrappeTestCase wraps
		# every test in, and everything inserted afterwards is written for real.
		# The columns come from `bench migrate`; a site without them skips.
		if not frappe.get_meta("Transportation Shipment").get_field("split_parent"):
			raise cls.skipTest(cls, "run `bench migrate`: split_parent missing on Transportation Shipment")

	def setUp(self):
		self.location = frappe.get_all("Location", limit=1, pluck="name")
		if not self.location:
			self.skipTest("no Location on this site to hang a stop on")
		self.location = self.location[0]

	def _card(self, headcount, key="OPS|ACC|SHIFT|LOC|Direct|Outward", prefix="EMP"):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = "Unassigned"
		doc.trip_direction = "Outward"
		doc.start_time = "06:00:00"
		doc.end_time = "18:00:00"
		doc.stop_location = self.location
		doc.generation_key = f"{key}|{frappe.generate_hash('K', 6)}"
		doc.headcount = headcount
		for n in range(headcount):
			doc.append("transportation_shipment_employee", {
				"employee_id": f"{prefix}-{n:03d}", "employee_name": f"Worker {n}",
			})
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		return doc

	def test_the_bus_is_filled_and_the_rest_moves(self):
		card = self._card(72)

		result = split_shipment_for_capacity(card.name, 53)

		self.assertEqual(result["primary_headcount"], 53)
		self.assertEqual(result["overflow_headcount"], 19)

	def test_nobody_is_listed_on_both_cards(self):
		# "Replicates the roster" read literally would board 53 people twice.
		card = self._card(72)

		result = split_shipment_for_capacity(card.name, 53)

		stayed = {r.employee_id for r in frappe.get_doc(
			"Transportation Shipment", result["primary"]).transportation_shipment_employee}
		moved = {r.employee_id for r in frappe.get_doc(
			"Transportation Shipment", result["overflow"]).transportation_shipment_employee}

		self.assertEqual(stayed & moved, set())
		self.assertEqual(len(stayed | moved), 72)

	def test_the_overflow_inherits_the_shift_it_belongs_to(self):
		card = self._card(72)

		overflow = frappe.get_doc(
			"Transportation Shipment", split_shipment_for_capacity(card.name, 53)["overflow"])
		# Read the parent back too: the in-memory copy still holds the string it was
		# assigned, while a Time column comes back as a timedelta.
		card.reload()

		self.assertEqual(overflow.start_time, card.start_time)
		self.assertEqual(overflow.end_time, card.end_time)
		self.assertEqual(overflow.stop_location, card.stop_location)
		self.assertEqual(overflow.trip_direction, card.trip_direction)

	def test_the_overflow_lands_in_the_pool_wearing_its_badge(self):
		card = self._card(72)

		overflow = frappe.get_doc(
			"Transportation Shipment", split_shipment_for_capacity(card.name, 53)["overflow"])

		self.assertEqual(overflow.status, "Unassigned")
		self.assertTrue(overflow.is_split_overflow)
		self.assertEqual(overflow.split_parent, card.name)

	def test_the_overflow_takes_its_own_generation_key(self):
		# Sharing the parent's key would make the generator's lookup return an arbitrary
		# one of the two and let the pruner delete the other.
		card = self._card(72)

		overflow = frappe.get_doc(
			"Transportation Shipment", split_shipment_for_capacity(card.name, 53)["overflow"])

		self.assertNotEqual(overflow.generation_key, card.generation_key)
		self.assertTrue(overflow.generation_key.endswith("#2"))

	def test_splitting_an_overflow_keeps_the_lineage_back_to_the_original(self):
		# AC 2.7: 35 staff onto a 22-seat coaster becomes 21 and 14, and the 14 still
		# knows which shift card it ultimately came from.
		card = self._card(72)
		first = split_shipment_for_capacity(card.name, 37)
		overflow = frappe.get_doc("Transportation Shipment", first["overflow"])

		second = split_shipment_for_capacity(overflow.name, 21)
		tail = frappe.get_doc("Transportation Shipment", second["overflow"])

		self.assertEqual(second["primary_headcount"], 21)
		self.assertEqual(second["overflow_headcount"], 14)
		self.assertEqual(tail.split_parent, overflow.name)
		self.assertEqual(tail.split_root, card.name)
		self.assertTrue(tail.generation_key.endswith("#3"))

	def test_a_card_that_fits_is_not_split(self):
		card = self._card(10)

		with self.assertRaises(frappe.ValidationError):
			split_shipment_for_capacity(card.name, 10)

	def test_a_card_with_no_generation_key_yields_an_overflow_with_none(self):
		# Ad-hoc and Trip Request cards are outside the generator entirely, so there is
		# nothing for their overflow to collide with.
		card = self._card(30)
		card.db_set("generation_key", None)

		overflow = frappe.get_doc(
			"Transportation Shipment", split_shipment_for_capacity(card.name, 20)["overflow"])

		self.assertFalse(overflow.generation_key)


class TestTheCanvasOffersTheSplit(FrappeTestCase):
	"""AC 2.1 / 2.5 / 2.6: what the dispatcher sees on the lane."""

	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_drop_is_intercepted_before_the_seat_check(self):
		# The seat gate would throw first and the split would never be offered.
		self.assertIn("if (card.headcount > this.passengerSeats(vehicle)) {", self.source)
		self.assertIn("this._openSplitModal(card, vehicle);", self.source)
		self.assertLess(
			self.source.index("_openSplitModal(card, vehicle);"),
			self.source.index("const blockers = this.tripsDuringCardWindows(card, vehicle.id);"),
		)

	def test_the_modal_states_the_four_numbers(self):
		self.assertIn("Total shift headcount", self.source)
		self.assertIn("Usable vehicle capacity", self.source)
		self.assertIn("Staying on this card", self.source)
		self.assertIn("Moving to a new card", self.source)

	def test_confirming_splits_and_then_places_the_filled_card(self):
		self.assertIn("__('Confirm & Split Remaining')", self.source)
		self.assertIn("split_shipment_for_capacity", self.source)
		self.assertIn("if (placed) self.handleDrop(placed, vehicle);", self.source)

	def test_cancelling_leaves_the_card_alone(self):
		# AC 2.6: nothing split, nothing placed.
		self.assertIn("__('Cancel Assignment')", self.source)

	def test_the_pool_marks_an_overflow_card(self):
		self.assertIn("card.is_split_overflow", self.source)
		self.assertIn("SPLIT OVERFLOW", self.source)
