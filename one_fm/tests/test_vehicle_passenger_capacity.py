# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002000: a vehicle's passenger capacity is derived from its own seat count.

Whether ``seats`` includes the driver differs from vehicle to vehicle, so the
fleet record answers it and Max Passenger Capacity follows.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides.vehicle import passenger_capacity, set_max_passenger_capacity

FLAG = "custom_includes_driver_seat"
CAPACITY = "custom_max_passenger_capacity"


class TestTheCapacityFormula(FrappeTestCase):
	def test_a_five_seater_that_includes_the_driver_carries_four(self):
		"""AC4, verbatim."""
		self.assertEqual(passenger_capacity(5, 1), 4)

	def test_a_thirty_seater_that_does_not_carries_thirty(self):
		"""AC5, verbatim — and the vehicle AC2's message is written about."""
		self.assertEqual(passenger_capacity(30, 0), 30)

	def test_a_seatless_vehicle_never_goes_negative(self):
		self.assertEqual(passenger_capacity(0, 1), 0)
		self.assertEqual(passenger_capacity(None, 1), 0)

	def test_the_flag_is_read_as_a_checkbox(self):
		"""It arrives as 0/1 from the database and "0"/"1" from a form post."""
		self.assertEqual(passenger_capacity(10, "1"), 9)
		self.assertEqual(passenger_capacity(10, "0"), 10)
		self.assertEqual(passenger_capacity(10, None), 10)


class TestTheFieldsThemselves(FrappeTestCase):
	"""Read through get_meta, so a Property Setter that unlocks the capacity fails."""

	def setUp(self):
		self.meta = frappe.get_meta("Vehicle")

	def test_both_fields_exist(self):
		self.assertEqual(self.meta.get_field(FLAG).fieldtype, "Check")
		self.assertEqual(self.meta.get_field(CAPACITY).fieldtype, "Int")

	def test_the_capacity_is_read_only_for_everyone(self):
		"""AC6: it is derived, so no role may type into it."""
		self.assertTrue(self.meta.get_field(CAPACITY).read_only)

	def test_the_flag_sits_with_the_seat_count(self):
		"""The question it asks is about seats, so it is asked next to them."""
		self.assertEqual(self.meta.get_field(FLAG).insert_after, "seats")


class TestItIsRecalculatedOnSave(FrappeTestCase):
	"""AC6: "calculation shall be updated upon saving of the record"."""

	def test_the_hook_derives_the_capacity(self):
		doc = frappe._dict({"seats": 5, FLAG: 1})
		set_max_passenger_capacity(doc)

		self.assertEqual(doc[CAPACITY], 4)

	def test_unchecking_the_flag_gives_the_seat_back(self):
		doc = frappe._dict({"seats": 30, FLAG: 0})
		set_max_passenger_capacity(doc)

		self.assertEqual(doc[CAPACITY], 30)

	def test_it_overwrites_whatever_was_there(self):
		"""The field is read-only on the form, but a stale value from an import or
		an older save must not survive."""
		doc = frappe._dict({"seats": 12, FLAG: 1, CAPACITY: 999})
		set_max_passenger_capacity(doc)

		self.assertEqual(doc[CAPACITY], 11)

	def test_it_is_wired_into_the_vehicle_save(self):
		from one_fm import hooks

		self.assertIn(
			"one_fm.overrides.vehicle.set_max_passenger_capacity",
			hooks.doc_events["Vehicle"]["validate"],
		)

	def test_a_real_vehicle_save_recalculates(self):
		name = frappe.db.get_value("Vehicle", {"seats": [">", 1]}, "name")
		if not name:
			self.skipTest("no seated Vehicle on this instance")

		doc = frappe.get_doc("Vehicle", name)
		was = (doc.get(FLAG), doc.get(CAPACITY))
		self.addCleanup(
			frappe.db.set_value, "Vehicle", name,
			{FLAG: was[0], CAPACITY: was[1]}, update_modified=False,
		)

		doc.set(FLAG, 0)
		doc.set(CAPACITY, 0)  # as if it had never been derived
		doc.flags.ignore_mandatory = True  # older fleet rows predate later reqd fields
		doc.flags.ignore_links = True
		doc.save(ignore_permissions=True)

		self.assertEqual(doc.get(CAPACITY), doc.seats)

		doc.set(FLAG, 1)
		doc.save(ignore_permissions=True)

		self.assertEqual(doc.get(CAPACITY), doc.seats - 1)


class TestEveryVehicleHasACapacity(FrappeTestCase):
	def test_no_seated_vehicle_is_left_at_zero(self):
		"""The patch backfills, because nobody is going to re-save 35 records by
		hand — and a capacity of 0 would wave every drop through."""
		unset = frappe.get_all(
			"Vehicle",
			filters={CAPACITY: ["in", [0, None]], "seats": [">", 0]},
			pluck="name",
		)

		self.assertEqual(unset, [])
