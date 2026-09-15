# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002096: no step completes before the one in front of it."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.grd.doctype.preparation.preparation import (
	SEQUENCED_CLASSIFICATIONS,
	SUB_DOCUMENT_SEQUENCE,
	create_documents_for_row,
	is_sequenced,
	upstream_of,
	validate_sequence,
)


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestTheSequence(FrappeTestCase):
	def test_the_order_is_the_legal_one(self):
		self.assertEqual(SUB_DOCUMENT_SEQUENCE, ("Work Permit", "Medical Insurance", "Residency", "PACI"))

	def test_each_step_knows_the_one_before_it(self):
		self.assertIsNone(upstream_of(frappe._dict(doctype="Work Permit")))
		self.assertEqual(upstream_of(frappe._dict(doctype="Medical Insurance")), "Work Permit")
		self.assertEqual(upstream_of(frappe._dict(doctype="Residency")), "Medical Insurance")
		self.assertEqual(upstream_of(frappe._dict(doctype="PACI")), "Residency")

	def test_a_document_outside_the_sequence_has_no_predecessor(self):
		self.assertIsNone(upstream_of(frappe._dict(doctype="Medical Appointment")))

	def test_a_kuwaiti_permit_is_outside_the_sequence(self):
		"""A Kuwaiti has no insurance, no residency and no civil ID process to follow."""
		for work_permit_type in ("New Kuwaiti", "Renewal Kuwaiti"):
			with self.subTest(work_permit_type=work_permit_type):
				self.assertFalse(
					is_sequenced(frappe._dict(doctype="Work Permit", work_permit_type=work_permit_type))
				)

	def test_an_extension_is_outside_the_sequence(self):
		"""A single document on its own."""
		self.assertFalse(is_sequenced(frappe._dict(doctype="Residency", category="Extend")))

	def test_the_four_sequenced_actions_are_inside_it(self):
		for doctype, (fieldname, values) in SEQUENCED_CLASSIFICATIONS.items():
			for value in values:
				with self.subTest(doctype=doctype, value=value):
					self.assertTrue(is_sequenced(frappe._dict(doctype=doctype, **{fieldname: value})))


class TestSequenceIsEnforced(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.preparation = self._a_preparation()

	def _a_preparation(self):
		preparation = frappe.get_doc({
			"doctype": "Preparation",
			"category": "Onboarding",
			"posting_date": nowdate(),
			"preparation_record": [{"employee": self.employee, "renewal_or_extend": "Overseas"}],
		})
		preparation.flags.ignore_permissions = True
		preparation.insert()
		create_documents_for_row(preparation.preparation_record[0], preparation.name)
		return preparation

	def _linked(self, doctype):
		return frappe.get_last_doc(doctype, filters={"preparation": self.preparation.name})

	def _complete(self, doctype):
		frappe.db.set_value(
			doctype, self._linked(doctype).name, "workflow_state", "Completed", update_modified=False
		)

	def test_the_insurance_cannot_complete_before_the_permit(self):
		insurance = self._linked("Medical Insurance")
		insurance.workflow_state = "Completed"

		with self.assertRaises(frappe.ValidationError) as caught:
			validate_sequence(insurance)

		self.assertIn("Work Permit", str(caught.exception))

	def test_it_can_once_the_permit_is_done(self):
		self._complete("Work Permit")

		insurance = self._linked("Medical Insurance")
		insurance.workflow_state = "Completed"
		validate_sequence(insurance)

	def test_the_civil_id_cannot_complete_before_the_residency(self):
		self._complete("Work Permit")
		self._complete("Medical Insurance")

		paci = self._linked("PACI")
		paci.workflow_state = "Completed"

		with self.assertRaises(frappe.ValidationError) as caught:
			validate_sequence(paci)

		self.assertIn("Residency", str(caught.exception))

	def test_only_the_step_immediately_before_is_checked(self):
		"""Each step's own completion was gated the same way, so the chain holds without every
		document querying all of them."""
		self._complete("Medical Insurance")

		residency = self._linked("Residency")
		residency.workflow_state = "Completed"
		validate_sequence(residency)

	def test_the_first_step_waits_for_nothing(self):
		work_permit = self._linked("Work Permit")
		work_permit.workflow_state = "Completed"
		validate_sequence(work_permit)

	def test_a_state_that_is_not_completion_is_not_gated(self):
		"""The operator has to be able to work on a document before finishing it."""
		insurance = self._linked("Medical Insurance")
		insurance.workflow_state = "Apply Online by PRO"
		validate_sequence(insurance)

	def test_a_document_with_no_preparation_is_not_gated(self):
		"""A transfer paper or a cancellation has no batch to be sequenced within."""
		insurance = self._linked("Medical Insurance")
		insurance.preparation = None
		insurance.workflow_state = "Completed"
		validate_sequence(insurance)

	def test_a_step_that_was_never_opened_is_not_waiting(self):
		"""The Action decides which documents a candidate gets."""
		frappe.delete_doc(
			"Medical Insurance", self._linked("Medical Insurance").name,
			force=True, ignore_permissions=True,
		)

		residency = self._linked("Residency")
		residency.workflow_state = "Completed"
		validate_sequence(residency)
