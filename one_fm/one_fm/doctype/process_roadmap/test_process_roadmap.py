# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.tests.utils import get_test_employee


def make_process_roadmap(**kwargs):
	"""Factory function to create a test Process Roadmap document."""
	employee = get_test_employee()
	defaults = {
		"doctype": "Process Roadmap",
		"date": frappe.utils.today(),
		"meeting_attendee": [
			{
				"doctype": "Meeting Attendee",
				"employee": employee.name,
			}
		],
	}
	defaults.update(kwargs)
	doc = frappe.get_doc(defaults)
	doc.insert(ignore_permissions=True)
	return doc


class TestProcessRoadmap(FrappeTestCase):
	def test_process_roadmap_creation(self):
		"""Test that a Process Roadmap document can be created successfully."""
		doc = make_process_roadmap()
		self.assertIsNotNone(doc.name)
		self.assertTrue(doc.name.startswith("PBR-PR-"))

	def test_meeting_attendee_required(self):
		"""Test that the meeting_attendee child table is mandatory."""
		with self.assertRaises(frappe.exceptions.MandatoryError):
			frappe.get_doc({
				"doctype": "Process Roadmap",
				"date": frappe.utils.today(),
				"meeting_attendee": [],
			}).insert(ignore_permissions=True)
