# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

CHILDREN = {
	"kitchen_cleaning_checklist": "Kitchen Cleaning Checklist",
	"room_cleaning_checklist": "Room Cleaning Checklist",
	"bathroom_cleaning_checklist": "Bathroom Cleaning Checklist",
}


def make_row(doctype):
	"""Fill every mandatory field of a checklist row."""
	row = {}
	for df in frappe.get_meta(doctype).fields:
		if df.fieldtype == "Select":
			row[df.fieldname] = "Yes"
		elif df.fieldtype == "Attach":
			row[df.fieldname] = "/files/inspection-test.png"
		else:
			row[df.fieldname] = "None"
	return row


class TestAccommodationInspections(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.unit = frappe.db.get_value(
			"Accommodation Unit",
			{"owner_reference_number": ["is", "set"], "accommodation_name": ["is", "set"]},
			["name", "accommodation", "accommodation_name", "owner_reference_number"],
			as_dict=True,
		)

	def setUp(self):
		if not self.unit:
			self.skipTest("No Accommodation Unit with an owner reference number on this site")

	def make_inspection(self, **kwargs):
		doc = frappe.get_doc(
			{
				"doctype": "Accommodation Inspections",
				"accommodation": self.unit.accommodation,
				"accommodation_unit": self.unit.name,
				"is_the_flat_passage_clean": "Yes",
			}
		)
		doc.update(kwargs)
		for fieldname, child in CHILDREN.items():
			doc.append(fieldname, make_row(child))
		return doc

	def test_insert_and_submit_fetches_unit_details(self):
		doc = self.make_inspection()
		doc.insert()
		doc.submit()
		self.assertEqual(doc.docstatus, 1)
		self.assertEqual(doc.accommodation_name, self.unit.accommodation_name)
		self.assertEqual(doc.owner_reference_number, self.unit.owner_reference_number)
		for fieldname in CHILDREN:
			self.assertEqual(len(doc.get(fieldname)), 1)

	def test_missing_flat_passage_answer_raises(self):
		doc = self.make_inspection(is_the_flat_passage_clean=None)
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_doctypes_are_standard_and_linked(self):
		meta = frappe.get_meta("Accommodation Inspections")
		self.assertEqual(meta.custom, 0)
		self.assertTrue(meta.is_submittable)
		for fieldname, child in CHILDREN.items():
			self.assertEqual(meta.get_field(fieldname).options, child)
			self.assertEqual(frappe.get_meta(child).custom, 0)
			self.assertTrue(frappe.get_meta(child).istable)
