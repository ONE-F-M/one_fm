# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002307: cards for work that has been switched off stay off the board.

A dispatcher's time goes on planning active shifts. An Inactive shipment, or one whose
Operations Shift has been switched off, is not work anybody is going to do.
"""

from datetime import timedelta

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	_build_transportation_shipment_cards,
	_serves_only_inactive_shifts,
	_shifts_served,
)


def _fmt(dt):
	return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_utc(dt_str):
	return frappe.utils.get_datetime(f"{frappe.utils.today()} {dt_str}")


def _no_coords(doctype, name):
	return None


def _card_shipments():
	return {c["shipment"] for c in _build_transportation_shipment_cards(
		_fmt, _to_utc, _no_coords, timedelta
	)}


class TestWhichShiftsACardServes(FrappeTestCase):
	"""An OLM card names its shifts in aggregated_shifts and leaves the Link blank."""

	def test_a_single_shift_card(self):
		card = frappe._dict(operations_shift="SHIFT-A", aggregated_shifts="SHIFT-A")
		self.assertEqual(_shifts_served(card), ["SHIFT-A"])

	def test_an_aggregated_card_with_no_link_set(self):
		card = frappe._dict(operations_shift=None, aggregated_shifts="SHIFT-A, SHIFT-B")
		self.assertEqual(_shifts_served(card), ["SHIFT-A", "SHIFT-B"])

	def test_the_link_is_included_when_it_is_not_already_listed(self):
		card = frappe._dict(operations_shift="SHIFT-C", aggregated_shifts="SHIFT-A")
		self.assertEqual(_shifts_served(card), ["SHIFT-A", "SHIFT-C"])

	def test_a_shift_is_never_counted_twice(self):
		card = frappe._dict(operations_shift="SHIFT-A", aggregated_shifts="SHIFT-A, SHIFT-B")
		self.assertEqual(_shifts_served(card), ["SHIFT-A", "SHIFT-B"])

	def test_an_adhoc_card_serves_none(self):
		card = frappe._dict(operations_shift=None, aggregated_shifts=None)
		self.assertEqual(_shifts_served(card), [])


class TestWhichCardsAreSuppressed(FrappeTestCase):
	def test_a_card_whose_only_shift_is_off(self):
		card = frappe._dict(operations_shift="SHIFT-A", aggregated_shifts="SHIFT-A")
		self.assertTrue(_serves_only_inactive_shifts(card, {"SHIFT-A"}))

	def test_a_card_still_serving_a_live_shift_stays(self):
		"""The rule is every shift, not any: an OLM card carrying three still has to run
		for the two that are live."""
		card = frappe._dict(operations_shift=None, aggregated_shifts="SHIFT-A, SHIFT-B")
		self.assertFalse(_serves_only_inactive_shifts(card, {"SHIFT-A"}))

	def test_a_card_with_every_shift_off_goes(self):
		card = frappe._dict(operations_shift=None, aggregated_shifts="SHIFT-A, SHIFT-B")
		self.assertTrue(_serves_only_inactive_shifts(card, {"SHIFT-A", "SHIFT-B"}))

	def test_an_adhoc_card_is_never_suppressed(self):
		"""There is no shift to have been switched off."""
		card = frappe._dict(operations_shift=None, aggregated_shifts=None)
		self.assertFalse(_serves_only_inactive_shifts(card, {"SHIFT-A"}))


class TestTheBoardDoesNotOfferThem(FrappeTestCase):
	"""Driven through the real card builder, not asserted against its source."""

	def _a_shipment(self, status="Unassigned", operations_shift=None, aggregated=None):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = status
		doc.trip_direction = "Outward"
		doc.start_time = "06:00:00"
		doc.end_time = "18:00:00"
		doc.operations_shift = operations_shift
		doc.aggregated_shifts = aggregated or (operations_shift or "")
		doc.source_doctype = "Operations Shift" if operations_shift else None
		doc.insert(ignore_permissions=True)
		return doc.name

	def _a_shift(self, status):
		shift = frappe.db.get_value("Operations Shift", {"status": status}, "name")
		if not shift:
			self.skipTest(f"no {status} Operations Shift on this site")
		return shift

	def test_an_inactive_shipment_is_not_offered(self):
		"""AC1. The expiry engine sets this status; the board has never rendered it."""
		name = self._a_shipment(status="Inactive", operations_shift=self._a_shift("Active"))

		self.assertNotIn(name, _card_shipments())

	def test_a_card_on_an_inactive_shift_is_not_offered(self):
		"""AC2, and the part generation alone does not cover - it runs daily, and an
		Assigned card is never pruned."""
		name = self._a_shipment(operations_shift=self._a_shift("Inactive"))

		self.assertNotIn(name, _card_shipments())

	def test_a_card_on_an_active_shift_is_still_offered(self):
		name = self._a_shipment(operations_shift=self._a_shift("Active"))

		self.assertIn(name, _card_shipments())

	def test_a_card_naming_no_shift_is_still_offered(self):
		"""An ad-hoc Trip Request journey has no shift to be switched off."""
		name = self._a_shipment()

		self.assertIn(name, _card_shipments())
