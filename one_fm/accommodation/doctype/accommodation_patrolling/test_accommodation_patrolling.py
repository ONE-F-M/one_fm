# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


def make_patrolling(floor_number="1", checklist=None):
	doc = frappe.get_doc({
		"doctype": "Accommodation Patrolling",
		"floor_number": floor_number,
	})
	for row in checklist if checklist is not None else [{"number_of_incidents": "No"}]:
		doc.append("accommodation_patrolling_checklist", row)
	return doc


class TestAccommodationPatrolling(FrappeTestCase):
	def test_insert_and_submit(self):
		doc = make_patrolling()
		doc.insert()
		doc.submit()
		self.assertEqual(doc.docstatus, 1)

	def test_missing_floor_number_raises(self):
		doc = make_patrolling(floor_number=None)
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_incidents_yes_requires_observations(self):
		doc = make_patrolling(checklist=[{"number_of_incidents": "Yes"}])
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_doctypes_are_not_custom(self):
		for name in ("Accommodation Patrolling", "Accommodation Patrolling Checklist"):
			self.assertEqual(frappe.get_meta(name).custom, 0)
