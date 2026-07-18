# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.trip_request.trip_request import resolve_destination_location
from one_fm.tests.utils import make_employee


class TestTripRequest(FrappeTestCase):
	def setUp(self):
		# Destination Location is free text (copied from the source document).
		self.location = "Office A, Kuwait City"

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

	def test_resolver_returns_none_for_unmapped_source(self):
		"""AC2: a source doctype with no location mapping (e.g. Client Interview
		Shortlist) resolves to no destination, leaving the field empty."""
		self.assertIsNone(
			resolve_destination_location("Client Interview Shortlist", "any-name")
		)

	def test_resolver_returns_none_without_source(self):
		"""No source selected → nothing to resolve."""
		self.assertIsNone(resolve_destination_location(None, None))

	def test_validate_does_not_overwrite_existing_destination(self):
		"""A destination already entered by the dispatcher is preserved."""
		doc = self.make_trip_request(1)
		doc.source_doctype = "Fingerprint Appointment"
		doc.destination_location = "Manually Entered Destination"
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.destination_location, "Manually Entered Destination")
