# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The run as the driver drives it, rather than as the cards describe it.

A card is "these people, from this camp, to this site" - one record, but two things the
bus does. A run printed from cards therefore shows half its stops: every drop-off is
missing, two cards from one camp read as two visits, and the ride home belongs to no
card at all. The process owner's sample sheet is written in stops, and so is a manifest.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
	build_itinerary,
	walk_occupancy,
)


def _card(camp, site, headcount, direction="Outward"):
	return frappe._dict({
		"name": frappe.generate_hash("TS", 6),
		"accommodation": camp,
		"accommodation_name": camp,
		"stop_location": site,
		"headcount": headcount,
		"trip_direction": direction,
		"pre_merge_trip_direction": None,
	})


def _places(stops):
	return [(s["place"], s["action_type"], s["boarding_count"], s["drop_off_count"]) for s in stops]


class TestOneCardIsTwoStops(FrappeTestCase):
	def test_a_single_card_is_a_pickup_a_drop_and_the_ride_home(self):
		stops = build_itinerary([_card("Camp 1", "Site A", 18)])

		self.assertEqual(_places(stops), [
			("Camp 1", "Boarding", 18, 0),
			("Site A", "Dropping Off", 0, 18),
			("Camp 1", "Dropping Off", 0, 0),
		])

	def test_two_cards_from_one_camp_are_one_visit(self):
		# The bus calls at the camp once, however many cards board there.
		stops = build_itinerary([
			_card("Camp 1", "Site A", 6),
			_card("Camp 1", "Site B", 4),
		])

		self.assertEqual(stops[0]["place"], "Camp 1")
		self.assertEqual(stops[0]["boarding_count"], 10)
		self.assertEqual(len([s for s in stops if s["place"] == "Camp 1"]), 2)  # load, then home


class TestTheProcessOwnersSecondScenario(FrappeTestCase):
	"""Transport.xlsx scenario 2: three camps, two sites, a collection, then home."""

	def _run(self):
		return build_itinerary([
			_card("Accommodation 1", "Grand Hayat", 6),
			_card("Accommodation 2", "Grand Hayat", 4),
			_card("Accommodation 3", "360 Car Park", 8),
			_card("Accommodation 1", "Khaldiya", 7, direction="Return"),
		])

	def test_it_reads_as_seven_stops(self):
		self.assertEqual(len(self._run()), 7)

	def test_the_camps_come_first_each_once(self):
		self.assertEqual(
			[s["place"] for s in self._run()[:3]],
			["Accommodation 1", "Accommodation 2", "Accommodation 3"],
		)

	def test_riders_from_two_camps_get_off_together(self):
		# The sheet drops 10 at Grand Hayat against pickups of 6 and 4 - a total that
		# belongs to no single card, which is why the card model could not print it.
		grand_hayat = next(s for s in self._run() if s["place"] == "Grand Hayat")

		self.assertEqual(grand_hayat["drop_off_count"], 10)

	def test_the_run_ends_at_the_base_camp(self):
		# AC 1.5, literally: the final stop IS the accommodation.
		last = self._run()[-1]

		self.assertEqual(last["place"], "Accommodation 1")
		self.assertEqual(last["drop_off_count"], 7)

	def test_the_bus_fills_up_and_empties_again(self):
		peak, _worst, per_stop = walk_occupancy(self._run())

		self.assertEqual(per_stop, [6, 10, 18, 8, 0, 7, 0])
		self.assertEqual(peak, 18)


class TestAHandoverIsOneStop(FrappeTestCase):
	def test_riders_off_and_on_at_one_place_is_a_combined_stop(self):
		stops = build_itinerary([
			_card("Camp 1", "Site A", 4),
			_card("Camp 1", "Site A", 4, direction="Return"),
		])
		handover = next(s for s in stops if s["place"] == "Site A")

		self.assertEqual(handover["action_type"], "Combined")
		self.assertEqual((handover["drop_off_count"], handover["boarding_count"]), (4, 4))

	def test_the_seats_vacated_are_the_ones_boarded_into(self):
		# 4 off before 4 on, so the bus never holds 8.
		peak, _worst, _per = walk_occupancy(build_itinerary([
			_card("Camp 1", "Site A", 4),
			_card("Camp 1", "Site A", 4, direction="Return"),
		]))

		self.assertEqual(peak, 4)
