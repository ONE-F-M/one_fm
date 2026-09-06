# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002306: drivers are working the run, not riding it.

A driver on a passenger card is a seat counted twice and a dispatcher scheduling
somebody who is already committed to that vehicle.
"""

from datetime import datetime, timedelta

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	_build_transportation_shipment_cards,
)


def _fmt(dt):
	return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_utc(dt_str):
	return frappe.utils.get_datetime(f"{frappe.utils.today()} {dt_str}")


def _no_coords(doctype, name):
	"""Coordinates are irrelevant to which cards are offered, and a lookup per card is
	the slowest part of the builder."""
	return None

from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
	_without_drivers,
	build_demand_descriptors,
)
from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
	DRIVER_DESIGNATIONS,
	driver_employees,
)


def _an_employee(designation):
	"""An active employee holding this designation, or None if the site has none."""
	return frappe.db.get_value(
		"Employee", {"status": "Active", "designation": designation}, "name"
	)


class TestDriverDesignations(FrappeTestCase):
	def test_every_driver_designation_is_a_real_one(self):
		"""A designation renamed away silently stops excluding anybody."""
		for designation in DRIVER_DESIGNATIONS:
			with self.subTest(designation=designation):
				self.assertTrue(
					frappe.db.exists("Designation", designation),
					f"{designation!r} is not a Designation on this site",
				)

	def test_it_covers_the_designations_the_drivers_actually_hold(self):
		"""The story says "Driver", which no active employee holds - the real ones are
		Bus, Heavy and Light. Agreed with the process owner."""
		for designation in ("Bus Driver", "Heavy Driver", "Light Driver"):
			self.assertIn(designation, DRIVER_DESIGNATIONS)


class TestDriverLookup(FrappeTestCase):
	def test_it_finds_a_driver(self):
		driver = _an_employee("Heavy Driver") or _an_employee("Light Driver")
		if not driver:
			self.skipTest("no active driver on this site")

		self.assertEqual(driver_employees([driver]), {driver})

	def test_it_leaves_a_non_driver_alone(self):
		rider = frappe.db.get_value(
			"Employee",
			{"status": "Active", "designation": ["not in", DRIVER_DESIGNATIONS]},
			"name",
		)
		if not rider:
			self.skipTest("no active non-driver on this site")

		self.assertEqual(driver_employees([rider]), set())

	def test_an_empty_roster_asks_the_database_nothing(self):
		self.assertEqual(driver_employees([]), set())
		self.assertEqual(driver_employees(None), set())


class TestTheDemandMapDropsDrivers(FrappeTestCase):
	"""AC1: no shipment is generated with a driver on it."""

	def setUp(self):
		self.driver = _an_employee("Heavy Driver") or _an_employee("Light Driver")
		self.rider = frappe.db.get_value(
			"Employee",
			{"status": "Active", "designation": ["not in", DRIVER_DESIGNATIONS]},
			"name",
		)
		if not self.driver or not self.rider:
			self.skipTest("this site has no active driver and non-driver to contrast")

	def _map(self, roster):
		return {"Camp A": {"lookup_id": "ACC-01", "shifts": {"SHIFT-01": list(roster)}}}

	def test_a_driver_is_taken_off_a_mixed_roster(self):
		trimmed = _without_drivers(self._map([self.rider, self.driver]))

		self.assertEqual(trimmed["Camp A"]["shifts"]["SHIFT-01"], [self.rider])

	def test_a_shift_of_only_drivers_is_dropped_entirely(self):
		"""An empty roster produces no shipment anyway - carrying it through only leaves
		the prune pass to clean up after it."""
		self.assertEqual(_without_drivers(self._map([self.driver])), {})

	def test_a_roster_with_no_driver_is_returned_untouched(self):
		original = self._map([self.rider])

		self.assertIs(_without_drivers(original), original)

	def test_nothing_is_generated_for_a_driver_only_shift(self):
		"""The whole point: the demand descriptor never reaches the writer."""
		self.assertEqual(build_demand_descriptors(self._map([self.driver])), [])


class TestTheCanvasRefusesDriverCards(FrappeTestCase):
	"""AC2/AC3: records made before the fix, and Assigned ones that cannot be pruned.

	Driven through the real card builder rather than asserted against its source: a
	source check passes just as happily when the filter is there but never reached.
	"""

	def setUp(self):
		self.driver = _an_employee("Heavy Driver") or _an_employee("Light Driver")
		self.rider = frappe.db.get_value(
			"Employee",
			{"status": "Active", "designation": ["not in", DRIVER_DESIGNATIONS]},
			"name",
		)
		if not self.driver or not self.rider:
			self.skipTest("this site has no active driver and non-driver to contrast")

	def _a_shipment(self, riders):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = "Unassigned"
		doc.trip_direction = "Outward"
		doc.start_time = "06:00:00"
		doc.end_time = "18:00:00"
		doc.headcount = len(riders)
		doc.source_doctype = "Operations Shift"
		for emp in riders:
			doc.append("transportation_shipment_employee", {"employee_id": emp})
		doc.insert(ignore_permissions=True)
		return doc.name

	def _card_ids(self):
		return {c["shipment"] for c in _build_transportation_shipment_cards(
			_fmt, _to_utc, _no_coords, timedelta
		)}

	def test_a_driver_only_card_is_not_offered(self):
		name = self._a_shipment([self.driver])

		self.assertNotIn(name, self._card_ids())

	def test_a_card_carrying_a_passenger_is_still_offered(self):
		"""The filter has to be "all of them", not "any of them" - a card with real riders
		on it is real demand whoever else is listed."""
		name = self._a_shipment([self.rider, self.driver])

		self.assertIn(name, self._card_ids())

	def test_an_ordinary_card_is_untouched(self):
		name = self._a_shipment([self.rider])

		self.assertIn(name, self._card_ids())
