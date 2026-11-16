# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

DOCTYPE = "Manpower Request Reason"


def make_reason(reason: str):
	return frappe.get_doc({"doctype": DOCTYPE, "manpower_request_reason": reason}).insert()


class TestManpowerRequestReason(FrappeTestCase):
	def test_named_by_the_reason(self):
		"""The record name is the reason itself, which is what Project Manpower
		Request stores in its Reason link field."""
		doc = make_reason("Test Reason")

		self.assertEqual(doc.name, "Test Reason")

	def test_reason_is_unique(self):
		"""Two records with the same reason would give the Reason link two entries
		that read identically, with no way for a recruiter to tell them apart."""
		make_reason("Test Duplicate Reason")

		with self.assertRaises(frappe.DuplicateEntryError):
			make_reason("Test Duplicate Reason")

	def test_reason_is_mandatory(self):
		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc({"doctype": DOCTYPE}).insert()
