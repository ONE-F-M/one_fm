# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002161: the shift window a Transportation Shipment card advertises.

Security-Sawaber Credit Office-Night-1 runs 19:00 to 07:00, and its card said
19:00-20:00. A night shift finishes the morning after it starts, so its end time is
legitimately earlier on the clock than its start; reading that as a broken window and
replacing it with "start plus an hour" is what invented the 20:00.
"""

from datetime import timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime, today

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	_build_transportation_shipment_cards,
)


def _cards_for(shipment_name):
	"""Run the real card builder and pick out one shipment's card.

	``to_utc`` is handed in naive rather than timezone-aware: what is under test is
	whether an end time earlier on the clock than its start is read as "the next
	morning" or as "broken", and that comparison is the same in any timezone.
	"""
	cards = _build_transportation_shipment_cards(
		fmt=lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
		to_utc=lambda value: get_datetime(f"{today()} {value}"),
		get_coords_cached=lambda *args: None,
		timedelta=timedelta,
	)
	return next(c for c in cards if c["shipment"] == shipment_name)


def _shipment(start, end, direction="Outward"):
	doc = frappe.new_doc("Transportation Shipment")
	doc.status = "Unassigned"
	doc.trip_direction = direction
	doc.start_time = start
	doc.end_time = end
	doc.headcount = 1
	doc.generation_key = frappe.generate_hash("TS-WINDOW", 10)
	doc.insert(ignore_permissions=True)
	return doc.name


class TestNightShiftCardWindow(FrappeTestCase):
	def _times(self, card):
		return card["shift_start"][11:16], card["shift_end"][11:16]

	def test_a_night_shift_card_shows_the_shift_it_covers(self):
		# The reported card: 19:00-07:00 was drawn as 19:00-20:00.
		card = _cards_for(_shipment("19:00:00", "07:00:00"))

		self.assertEqual(self._times(card), ("19:00", "07:00"))

	def test_a_day_shift_is_unchanged(self):
		card = _cards_for(_shipment("07:00:00", "19:00:00"))

		self.assertEqual(self._times(card), ("07:00", "19:00"))

	def test_a_shift_with_no_length_recorded_still_gets_an_hour(self):
		# The one case the old guard was right about: identical start and end says
		# nothing about how long the shift is, so the card keeps a nominal hour
		# rather than collapsing to a zero-width window.
		card = _cards_for(_shipment("08:00:00", "08:00:00"))

		self.assertEqual(self._times(card), ("08:00", "09:00"))

	def test_the_return_leg_is_collected_when_the_night_shift_ends(self):
		# The pickup window is what the placement reads, so it has to move with the
		# corrected end time and not stay pinned an hour after the drop.
		card = _cards_for(_shipment("19:00:00", "07:00:00", direction="Return"))

		self.assertEqual(card["return_window_start"][11:16], "07:00")
