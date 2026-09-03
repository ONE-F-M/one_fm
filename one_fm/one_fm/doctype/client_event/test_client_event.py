# Copyright (c) 2025, ONE FM and Contributors
# See license.txt

import frappe
import unittest
from frappe.utils import now_datetime, add_to_date

class TestClientEvent(unittest.TestCase):
	def setUp(self):
		self.clear_test_events()
		self.clear_test_dependencies()
		self.create_test_dependencies()


	def tearDown(self):
		self.clear_test_events()

	def clear_test_events(self):
		events = frappe.get_all("Client Event", filters={"event_name": "Test Event"})
		for event in events:
			frappe.delete_doc("Client Event", event.name, force=1)

	def create_test_dependencies(self):
		if not frappe.db.exists("Location", "Test Location"):
			# Location has required coordinates and a geofence radius, so a name alone
			# cannot be saved - this fixture has been failing on every test in the file.
			frappe.get_doc({
				"doctype": "Location",
				"location_name": "Test Location",
				"latitude": 29.3759,
				"longitude": 47.9774,
				"geofence_radius": 100,
			}).insert()
		if not frappe.db.exists("Project", "Test Project"):
			frappe.get_doc({"doctype": "Project", "project_name": "Test Project"}).insert()

	def clear_test_dependencies(self):
		if frappe.db.exists("Location", "Test Location"):
			frappe.delete_doc("Location", "Test Location")
		if frappe.db.exists("Project", "Test Project"):
			frappe.delete_doc("Project", "Test Project")


	def test_start_date_in_past(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			create_client_event(start_date=add_to_date(now_datetime(), days=-1))
		self.assertEqual(str(cm.exception), "The scheduled event time must be a future date/time. Please adjust the event details.")

	def test_event_start_datetime_in_past(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			create_client_event(event_start_datetime=add_to_date(now_datetime(), days=-1))
		self.assertEqual(str(cm.exception), "The scheduled event time must be a future date/time. Please adjust the event details.")

	def test_end_date_in_past(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			create_client_event(end_date=add_to_date(now_datetime(), days=-1))
		self.assertEqual(str(cm.exception), "The scheduled end date/time must be a future date/time. Please adjust the event details.")

	def test_event_end_datetime_in_past(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			create_client_event(event_end_datetime=add_to_date(now_datetime(), days=-1))
		self.assertEqual(str(cm.exception), "The scheduled end date/time must be a future date/time. Please adjust the event details.")

	def test_end_date_before_start_date(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			create_client_event(start_date=add_to_date(now_datetime(), days=2), end_date=add_to_date(now_datetime(), days=1))
		self.assertEqual(str(cm.exception), "The scheduled end date/time must be later than Start Date or Start Datetime. Please adjust the event details.")

	def test_event_end_datetime_before_event_start_datetime(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			create_client_event(event_start_datetime=add_to_date(now_datetime(), days=2), event_end_datetime=add_to_date(now_datetime(), days=1))
		self.assertEqual(str(cm.exception), "The scheduled end date/time must be later than Start Date or Start Datetime. Please adjust the event details.")

	def test_valid_dates(self):
		try:
			create_client_event()
			# If no exception is raised, the test passes.
			self.assertTrue(True)
		except frappe.ValidationError as e:
			self.fail(f"Validation error raised for valid dates: {e}")

	def test_no_end_date(self):
		try:
			create_client_event(end_date=None, event_end_datetime=None)
			self.assertTrue(True)
		except frappe.ValidationError as e:
			self.fail(f"Validation error raised when no end date is provided: {e}")


def create_client_event(**kwargs):
	args = {
		"doctype": "Client Event",
		"event_name": "Test Event",
		"start_date": add_to_date(now_datetime(), days=1),
		"event_start_datetime": add_to_date(now_datetime(), days=1),
		"end_date": add_to_date(now_datetime(), days=2),
		"event_end_datetime": add_to_date(now_datetime(), days=2),
		"event_location": "Test Location",
		"project": "Test Project",
	}
	args.update(kwargs)
	doc = frappe.get_doc(args)
	doc.insert()
	return doc
