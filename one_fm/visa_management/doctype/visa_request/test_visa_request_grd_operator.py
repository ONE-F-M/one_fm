# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Assigning the GRD Operator from the Visa Request list view.

That a request is not handed to an unnamed GRD Operator is enforced by the Visa process
map ("Is GRD Operator Set?"), not by the controller.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

class TestTheListViewOffersEditAtAll(FrappeTestCase):
	"""AC 1's first gate, and the one that had the Edit entry missing from the Actions
	menu entirely.

	list_view.js pushes the Edit action only when is_bulk_edit_allowed() agrees, and for a
	doctype carrying a workflow that answer comes from one place - the allow_edit flag on
	its List View Settings row. Visa Request has an active workflow, and the row WI-002426
	brought over from the BA site has the flag off, because bulk editing is what this
	story adds.
	"""

	def test_the_doctype_really_does_carry_a_workflow(self):
		"""If it did not, Frappe would allow bulk edit outright and the flag below would
		be beside the point - so this is what makes the next test meaningful."""
		self.assertTrue(
			frappe.db.exists("Workflow", {"document_type": "Visa Request", "is_active": 1})
		)

	def test_the_list_view_settings_row_allows_editing(self):
		if not frappe.db.exists("List View Settings", "Visa Request"):
			self.skipTest("run bench migrate - the list view patches have not been applied")

		self.assertTrue(
			frappe.db.get_value("List View Settings", "Visa Request", "allow_edit"),
			"the Actions menu will have no Edit entry",
		)


class TestTheFieldCanBeSetInBulk(FrappeTestCase):
	"""AC 1's second gate: once the dialog opens, it offers every writable value field
	(list_view.js::is_field_editable). What that needs is for grd_operator to stay one of
	them, which is what this pins."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.field = frappe.get_meta("Visa Request").get_field("grd_operator")

	def test_the_field_is_there(self):
		self.assertIsNotNone(self.field)
		self.assertEqual(self.field.fieldtype, "Link")
		self.assertEqual(self.field.options, "User")

	def test_nothing_takes_it_out_of_the_bulk_edit_dialog(self):
		"""Each of these would remove it from the list of fields the dialog offers."""
		self.assertFalse(self.field.hidden)
		self.assertFalse(self.field.read_only)
		self.assertFalse(self.field.is_virtual)
		self.assertFalse(self.field.read_only_depends_on)
