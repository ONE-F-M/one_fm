# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Attendance in the Event Staff Connections section (WI-001686).

A Connection is a Link field on the other doctype pointing back at this one, so
Attendance carries Event Staff and Event Staff lists Attendance among its links. The
first attempt at this work item added a toolbar button instead, which is not the
Connections dashboard the criteria ask for.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

ATTENDANCE = "Attendance"
EVENT_STAFF = "Event Staff"
FIELD = "custom_event_staff"


class TestAttendanceCarriesEventStaff(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.meta = frappe.get_meta(ATTENDANCE)

	def test_the_field_links_to_event_staff(self):
		field = self.meta.get_field(FIELD)
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, EVENT_STAFF)

	def test_it_is_read_only(self):
		self.assertTrue(self.meta.get_field(FIELD).read_only)

	def test_it_is_fetched_rather_than_typed(self):
		# The Shift Assignment is the same hop Client Event takes; Client Event itself
		# has nothing to fetch, being the far end of a one-to-many from Event Staff.
		self.assertEqual(self.meta.get_field(FIELD).fetch_from, "shift_assignment.event_staff")
		self.assertTrue(frappe.get_meta("Shift Assignment").has_field("event_staff"))

	def test_it_sits_below_the_client_event_field(self):
		order = [f.fieldname for f in self.meta.fields]
		self.assertLess(order.index("custom_client_event"), order.index(FIELD))


class TestEventStaffListsAttendance(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.links = frappe.get_meta(EVENT_STAFF).get("links") or []

	def _link(self, doctype):
		return next((l for l in self.links if l.link_doctype == doctype), None)

	def test_attendance_is_one_of_the_connections(self):
		self.assertIsNotNone(self._link(ATTENDANCE))

	def test_it_is_filtered_by_the_event_staff_field(self):
		# This is what makes the Connection show only this record's attendance rather
		# than every attendance for the whole event.
		self.assertEqual(self._link(ATTENDANCE).link_fieldname, FIELD)

	def test_the_field_it_filters_on_exists_on_attendance(self):
		# A connection pointing at a missing field silently shows nothing.
		self.assertTrue(frappe.get_meta(ATTENDANCE).has_field(self._link(ATTENDANCE).link_fieldname))

	def test_the_existing_connections_are_left_alone(self):
		self.assertEqual(
			[(l.link_doctype, l.link_fieldname) for l in self.links],
			[
				("Employee Schedule", "event_staff"),
				("Shift Assignment", "event_staff"),
				("Attendance", FIELD),
			],
		)

	def test_the_dashboard_resolves_the_connection(self):
		# What the form actually reads when it draws the Connections section.
		data = frappe.get_meta(EVENT_STAFF).get_dashboard_data()
		listed = {item for group in data.get("transactions", []) for item in group.get("items", [])}
		self.assertIn(ATTENDANCE, listed)
		self.assertEqual(data.get("non_standard_fieldnames", {}).get(ATTENDANCE), FIELD)


class TestTheRejectedButtonIsGone(FrappeTestCase):
	def test_the_form_no_longer_adds_an_attendance_button(self):
		# The first attempt put a button in the toolbar filtered by Client Event, which
		# is the whole event rather than this staff record, and is not the Connections
		# section the criteria name.
		source = frappe.read_file(
			frappe.get_app_path("one_fm", "one_fm", "doctype", "event_staff", "event_staff.js")
		)
		self.assertNotIn('add_custom_button(__("Attendance")', source)
