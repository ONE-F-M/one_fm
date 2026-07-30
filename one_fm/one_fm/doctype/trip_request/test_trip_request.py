# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.trip_request.trip_request import (
	SOURCE_DESTINATION_FIELD_MAP,
	resolve_destination_location,
)
from one_fm.tests.utils import make_employee


def _get_or_create_location(location_name):
	"""A Location to point an event at, inserted raw.

	The Location controller enforces latitude/longitude and maintains a nested set;
	a plain link target needs neither.
	"""
	if frappe.db.exists("Location", location_name):
		return location_name

	location = frappe.new_doc("Location")
	location.location_name = location_name
	location.name = location_name
	location.db_insert()
	return location_name


def _make_event_staff(location):
	"""Insert a minimal Event Staff row, bypassing its controller.

	The controller validates client-event staffing requirements, employee days off
	and overlapping assignments, and writes roster side effects on submit - none of
	which the destination resolver touches, and all of which would need a full
	Client Event fixture.
	"""
	name = f"_TEST-ES-{location or 'NO-LOCATION'}"
	frappe.db.delete("Event Staff", {"name": name})

	event_staff = frappe.new_doc("Event Staff")
	event_staff.name = name
	event_staff.event_location = location
	event_staff.db_insert()
	return name


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


class TestEventStaffDestination(FrappeTestCase):
	"""WI-001806: selecting an Event Staff source resolves the destination from the
	event's Location, so the dispatcher does not re-key data the system already has."""

	def setUp(self):
		self.location = _get_or_create_location("_Test Trip Event Location")

	def test_event_staff_is_mapped_to_its_event_location(self):
		self.assertEqual(SOURCE_DESTINATION_FIELD_MAP["Event Staff"], "event_location")

	def test_the_mapped_field_exists_on_event_staff(self):
		# resolve_destination_location guards on this, so a rename would silently
		# stop resolving rather than error.
		self.assertTrue(frappe.get_meta("Event Staff").has_field("event_location"))

	def test_the_mapped_field_links_to_location(self):
		# Transportation Shipment copies the resolved value into its `stop_location`
		# Link field, so anything but a Location docname would fail link validation
		# downstream.
		df = frappe.get_meta("Event Staff").get_field("event_location")
		self.assertEqual(df.fieldtype, "Link")
		self.assertEqual(df.options, "Location")

	def test_a_location_docname_is_its_location_name(self):
		# Location autonames from location_name, which is why storing the docname
		# satisfies the AC's "pull the Location address".
		self.assertEqual(
			frappe.db.get_value("Location", self.location, "location_name"), self.location
		)

	def test_resolver_returns_the_event_location(self):
		event_staff = _make_event_staff(self.location)
		self.assertEqual(
			resolve_destination_location("Event Staff", event_staff), self.location
		)

	def test_resolver_returns_none_when_the_event_has_no_location(self):
		event_staff = _make_event_staff(None)
		self.assertIsNone(resolve_destination_location("Event Staff", event_staff))

	def test_the_destination_is_filled_on_save(self):
		doc = frappe.get_doc({
			"doctype": "Trip Request",
			"from_date": "2026-08-01",
			"to_date": "2026-08-02",
			"departure_time": "08:00:00",
			"return_time": "11:00:00",
			"transportation_method": "Company Fleet",
			"source_doctype": "Event Staff",
			"source_reference": _make_event_staff(self.location),
			"transport_request_passenger": [
				{"employee_id": make_employee("test_trip_es1@example.com").name}
			],
		})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.destination_location, self.location)
