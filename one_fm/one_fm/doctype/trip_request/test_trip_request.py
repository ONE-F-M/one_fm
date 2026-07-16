# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.tests.utils import make_employee


class TestTripRequest(FrappeTestCase):
	def setUp(self):
		# Ensure a test Location exists for the mandatory destination field
		if not frappe.db.exists("Location", "Test Location"):
			loc = frappe.get_doc({
				"doctype": "Location",
				"location_name": "Test Location",
				"latitude": 29.3759,
				"longitude": 47.9774,
				"geofence_radius": 100,
			}).insert(ignore_permissions=True)
			self.location = loc.name
		else:
			self.location = "Test Location"

		# Create a pool of test employees to use as passengers
		self.employees = [
			make_employee(f"test_trip_emp{i}@example.com").name
			for i in range(1, 6)
		]

	def make_trip_request(self, passenger_count):
		"""Build (not insert) a Trip Request with the given number of passengers."""
		passengers = [
			{"employee_id": self.employees[i]}
			for i in range(passenger_count)
		]
		return frappe.get_doc({
			"doctype": "Trip Request",
			"from_date": "2026-08-01",
			"to_date": "2026-08-02",
			"departure_time": "08:00:00",
			"return_time": "11:00:00",
			"transportation_method": "Company Fleet",
			"destination_location": self.location,
			"transport_request_passenger": passengers,
		})

	def test_single_passenger_headcount(self):
		"""One employee → single tracking number, headcount of 1."""
		doc = self.make_trip_request(1)
		doc.insert(ignore_permissions=True)

		self.assertTrue(doc.name.startswith("TRQ-"))
		self.assertEqual(doc.total_headcount, 1)

	def test_five_passengers_headcount(self):
		"""Five employees → single tracking number, headcount of 5."""
		doc = self.make_trip_request(5)
		doc.insert(ignore_permissions=True)

		self.assertTrue(doc.name.startswith("TRQ-"))
		self.assertEqual(doc.total_headcount, 5)

	def test_three_passengers_headcount(self):
		"""Story Input/Output: three passengers → Total Headcount of 3."""
		doc = self.make_trip_request(3)
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.total_headcount, 3)

	def test_empty_passenger_list_blocks_save(self):
		"""An empty passenger list must block the save (validate hook)."""
		doc = self.make_trip_request(0)
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)
