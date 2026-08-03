# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for Service Location on the appointment doctypes (WI-001807).

Service Location is a Link to Location on both appointment doctypes, so the value a
Trip Request copies into its Destination Location is a docname Transportation Shipment
can resolve as a stop.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.trip_request.trip_request import (
	SOURCE_DESTINATION_FIELD_MAP,
	resolve_destination_location,
)

APPOINTMENT_DOCTYPES = ("Fingerprint Appointment", "Medical Appointment")


class TestServiceLocationIsALink(FrappeTestCase):
	def test_both_appointments_link_service_location_to_location(self):
		for doctype in APPOINTMENT_DOCTYPES:
			field = frappe.get_meta(doctype).get_field("service_location")
			self.assertEqual(field.fieldtype, "Link", msg=doctype)
			self.assertEqual(field.options, "Location", msg=doctype)

	def test_neither_defaults_to_a_location_that_does_not_exist(self):
		# A Link default that is not a docname makes every new appointment unsaveable,
		# so a default is only allowed once its Location exists.
		for doctype in APPOINTMENT_DOCTYPES:
			default = frappe.get_meta(doctype).get_field("service_location").default
			if default:
				self.assertTrue(frappe.db.exists("Location", default), msg=doctype)


class TestTripRequestStillResolvesIt(FrappeTestCase):
	def test_both_appointments_are_mapped_to_service_location(self):
		for doctype in APPOINTMENT_DOCTYPES:
			self.assertEqual(SOURCE_DESTINATION_FIELD_MAP.get(doctype), "service_location")

	def test_the_resolved_destination_is_a_location_docname(self):
		# Transportation Shipment copies Destination Location into its stop_location
		# Link field, so anything that is not a Location docname fails there.
		location = frappe.get_doc(
			{
				"doctype": "Location",
				"location_name": "_Test Appointment Service Location",
				"is_group": 0,
				"geofence_radius": 0,
			}
		).insert(ignore_permissions=True)

		appointment = frappe.get_all("Fingerprint Appointment", limit=1, pluck="name")
		if not appointment:
			self.skipTest("no Fingerprint Appointment to resolve from")

		frappe.db.set_value(
			"Fingerprint Appointment", appointment[0], "service_location", location.name
		)

		self.assertEqual(
			resolve_destination_location("Fingerprint Appointment", appointment[0]),
			location.name,
		)
