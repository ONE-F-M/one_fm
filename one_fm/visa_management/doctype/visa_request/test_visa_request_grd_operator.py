# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002446: assigning the GRD Operator, and not handing a request over without one."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.visa_management.doctype.visa_request.visa_request import GRD_OPERATOR_STATE

SEEDED = "WI-002446-SEED-"


def _request(workflow_state, grd_operator=None, previous_state="Draft"):
	"""A Visa Request as validate sees it, with a before-state to compare against.

	Built in memory: the rule reads two fields, and inserting one would drag in the
	passport, the age check and half a dozen mandatory fields that have nothing to do
	with it.
	"""
	doc = frappe.new_doc("Visa Request")
	doc.name = SEEDED + "1"
	doc.workflow_state = workflow_state
	doc.grd_operator = grd_operator

	if previous_state is not None:
		before = frappe.new_doc("Visa Request")
		before.name = doc.name
		before.workflow_state = previous_state
		doc._doc_before_save = before
		doc.set("__islocal", False)

	return doc


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


class TestTheStateCannotBeReachedWithoutOne(FrappeTestCase):
	def test_the_state_is_one_the_workflow_has(self):
		"""The whole rule is a string comparison; the wrong case names nothing."""
		workflow = frappe.db.get_value(
			"Workflow", {"document_type": "Visa Request", "is_active": 1}, "name"
		)
		if not workflow:
			self.skipTest("no active Visa Request workflow on this site")

		states = frappe.get_all(
			"Workflow Document State",
			filters={"parent": workflow, "parenttype": "Workflow"},
			pluck="state",
		)
		self.assertIn(GRD_OPERATOR_STATE, states)

	def test_the_transition_is_refused_with_the_field_blank(self):
		with self.assertRaises(frappe.ValidationError) as raised:
			_request(GRD_OPERATOR_STATE).validate_grd_operator_assigned()

		self.assertIn("GRD Operator", str(raised.exception))

	def test_the_transition_goes_through_once_one_is_named(self):
		_request(GRD_OPERATOR_STATE, grd_operator="Administrator").validate_grd_operator_assigned()

	def test_a_new_request_created_straight_into_the_state_is_refused(self):
		"""No before-state at all - what the API does when it posts the state directly."""
		with self.assertRaises(frappe.ValidationError):
			_request(GRD_OPERATOR_STATE, previous_state=None).validate_grd_operator_assigned()

	def test_a_request_already_in_the_state_is_left_alone(self):
		"""Requests were sitting there with the field blank before it existed; re-checking
		on every save would make every one of them unsaveable."""
		_request(
			GRD_OPERATOR_STATE, previous_state=GRD_OPERATOR_STATE
		).validate_grd_operator_assigned()

	def test_every_other_state_is_untouched(self):
		for state in ("Draft", "Pending GRD Manager Approval", "Pending By PAM", "Completed"):
			with self.subTest(state=state):
				_request(state).validate_grd_operator_assigned()

	def test_the_manager_sending_it_back_is_held_to_the_same_rule(self):
		"""Rejecting from the manager's desk also lands in Pending by GRD Operator, and a
		request going back to nobody is the same problem."""
		with self.assertRaises(frappe.ValidationError):
			_request(
				GRD_OPERATOR_STATE, previous_state="Pending GRD Manager Approval"
			).validate_grd_operator_assigned()
