# -*- coding: utf-8 -*-
# Copyright (c) 2021, ONE FM and Contributors
# See license.txt
import frappe
from frappe.tests.utils import FrappeTestCase

# The sub-documents a submitted Preparation generates. Each one stores the parent's
# name in `preparation`, set by the create_* functions in their own controllers.
SUB_DOCUMENTS = ("Work Permit", "Medical Insurance", "Residency", "PACI")


class TestPreparationLinkOnSubDocuments(FrappeTestCase):
	"""WI-001973: a generated sub-document has to show which Preparation it came from.

	Asserted through get_meta rather than the doctype JSON, because get_meta is what
	the form renders from - so this also fails if a Property Setter hides the field
	again from Customize Form, which is how it came to be hidden in the first place.
	"""

	def test_preparation_link_is_visible_and_read_only(self):
		for doctype in SUB_DOCUMENTS:
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("preparation")

				self.assertIsNotNone(field, f"{doctype} has no Preparation field")
				self.assertFalse(field.hidden, f"{doctype}: Preparation is hidden")
				# Read only, not just visible: the link records which batch created the
				# document, so it is history and must not be re-pointed by hand.
				self.assertTrue(field.read_only, f"{doctype}: Preparation is editable")
				self.assertEqual(field.options, "Preparation")
