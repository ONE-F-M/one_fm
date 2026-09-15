# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A shift that ends at midnight says 00:00 on its card (WI-002401 AC9).

A Frappe Time field of 00:00:00 comes back as ``timedelta(0)``, which is falsy. Every
reader that asked ``if not end_time`` therefore read a shift finishing at midnight as
one with no finish recorded at all, and fell through to the literal fallback further
down its ``or`` chain - so a 12:00-00:00 afternoon card advertised an 18:00 finish.
"""

from datetime import timedelta

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import time_is_blank
from one_fm.one_fm.page.transportation_schedule.transportation_schedule import _stated_time


class TestMidnightIsAStatedTime(FrappeTestCase):
	def test_midnight_is_not_blank(self):
		# The whole bug in one line: timedelta(0) is falsy but it is an answer.
		self.assertFalse(bool(timedelta(0)))
		self.assertFalse(time_is_blank(timedelta(0)))

	def test_an_unset_time_is_blank(self):
		self.assertTrue(time_is_blank(None))
		self.assertTrue(time_is_blank(""))

	def test_a_midnight_finish_is_kept_over_the_fallback(self):
		self.assertEqual(
			_stated_time(timedelta(0), None, "18:00:00"),
			timedelta(0),
		)

	def test_an_unset_finish_still_takes_the_next_stated_value(self):
		self.assertEqual(_stated_time(None, "22:30:00", "18:00:00"), "22:30:00")
		self.assertEqual(_stated_time(None, None, "18:00:00"), "18:00:00")

	def test_a_noon_finish_is_unaffected(self):
		noon = timedelta(seconds=12 * 3600)
		self.assertEqual(_stated_time(noon, None, "18:00:00"), noon)


class TestAMidnightCardReportsMidnight(FrappeTestCase):
	"""End to end: the card the board draws carries the shift's real finish."""

	def test_the_card_window_lands_on_midnight_not_on_the_fallback(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			get_route_planner_data,
		)

		midnight = {
			row.name for row in frappe.get_all(
				"Transportation Shipment", filters={"end_time": "00:00:00"}, fields=["name"]
			)
		}
		if not midnight:
			self.skipTest("No shipment on this site finishes at midnight")

		cards = [
			card for card in get_route_planner_data()["shipment_cards"]
			if card.get("shipment") in midnight
		]
		if not cards:
			self.skipTest("No midnight shipment is currently on the board")

		# The stamps are UTC and the site runs at UTC+3, so a Kuwait midnight is 21:00Z
		# on the day before. What must never appear is the 18:00 fallback (15:00Z).
		for card in cards:
			self.assertTrue(
				card["shift_end"].endswith("T21:00:00Z"),
				f"{card['shipment']} finishes at {card['shift_end']}, not midnight",
			)
