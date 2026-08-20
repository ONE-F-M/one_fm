# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002136: completing a civil ID PACI charged nothing for, and the two Save routes."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.paci.paci import (
	COMPLETED,
	NEW_APPLICATION,
	PENDING_GR_OPERATOR,
	create_PACI,
)

NO_PAYMENT_TRANSITION = (PENDING_GR_OPERATOR, "No Payment Required", COMPLETED)


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"], "residency_expiry_date": ["is", "set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return frappe.get_doc("Employee", name)


class TestPACINoPayment(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()

	def _with_the_operator(self, category="Renewal", **kwargs):
		"""A PACI sitting on the GR Operator's desk, ready to be completed."""
		paci = create_PACI(self.employee, category)
		paci.db_set("workflow_state", PENDING_GR_OPERATOR)
		for fieldname, value in kwargs.items():
			paci.db_set(fieldname, value)
		paci.reload()
		return paci

	def _complete(self, paci):
		paci.workflow_state = COMPLETED
		paci.save(ignore_permissions=True)

	# ── The payment invoice ───────────────────────────────────────────────────────

	def test_completing_without_the_invoice_is_refused(self):
		paci = self._with_the_operator()

		with self.assertRaises(frappe.ValidationError):
			self._complete(paci)

	def test_completing_with_the_invoice_goes_through(self):
		paci = self._with_the_operator(upload_civil_id_payment="/files/receipt.pdf")

		self._complete(paci)

		self.assertEqual(paci.workflow_state, COMPLETED)

	def test_no_payment_required_completes_without_one(self):
		paci = self._with_the_operator(no_payment_required=1)

		self._complete(paci)

		self.assertEqual(paci.workflow_state, COMPLETED)

	def test_the_invoice_is_only_owed_on_the_way_out_of_the_operator(self):
		"""A save that is not the completion must not demand it."""
		paci = self._with_the_operator()

		paci.workflow_state = "Pending Address Update"
		paci.save(ignore_permissions=True)

		self.assertEqual(paci.workflow_state, "Pending Address Update")

	# ── The workflow ──────────────────────────────────────────────────────────────

	def test_the_workflow_offers_a_no_payment_action(self):
		transitions = self._transitions()

		self.assertIn(NO_PAYMENT_TRANSITION, transitions)
		# Offered only once the operator has said no fee applies, so the button and the
		# checkbox cannot disagree.
		self.assertEqual(transitions[NO_PAYMENT_TRANSITION], "doc.no_payment_required")

	def test_saving_routes_on_the_category_not_the_role(self):
		transitions = self._transitions()

		self.assertEqual(
			transitions[("Draft", "Save", PENDING_GR_OPERATOR)],
			'doc.category in ("Renewal", "Transfer")',
		)
		self.assertEqual(
			transitions[("Draft", "Save", "Pending PRO")],
			'doc.category == "New Application"',
		)

	def test_a_rejection_has_to_say_why(self):
		field = frappe.get_meta("PACI").get_field("paci_rejection_reason")
		self.assertEqual(field.mandatory_depends_on, 'eval:doc.workflow_state == "Rejected"')

	def test_a_first_application_still_opens_with_the_pro(self):
		"""The Save conditions must not disturb what WI-001830 put in place."""
		create_PACI(self.employee, NEW_APPLICATION)

		paci = frappe.get_last_doc("PACI", filters={"employee": self.employee.name})
		self.assertEqual(paci.workflow_state, "Pending PRO")

	def _transitions(self):
		workflow = frappe.get_doc("Workflow", "PACI")
		return {(t.state, t.action, t.next_state): (t.condition or "") for t in workflow.transitions}


class TestPACIProSubmission(FrappeTestCase):
	"""WI-002136: what the PRO owes before handing a first application back."""

	def setUp(self):
		self.employee = _an_active_employee()

	def _with_the_pro(self, **kwargs):
		paci = create_PACI(self.employee, NEW_APPLICATION)
		# create_PACI already hands a first application to the PRO (WI-001830), with
		# neither of these known - which is the case this rule must not break.
		self.assertEqual(paci.workflow_state, "Pending PRO")
		for fieldname, value in kwargs.items():
			paci.db_set(fieldname, value)
		paci.reload()
		return paci

	def _submit(self, paci):
		paci.workflow_state = "Pending by PACI"
		paci.save(ignore_permissions=True)

	def test_the_record_carries_a_pro_user(self):
		field = frappe.get_meta("PACI").get_field("pro_user")
		self.assertIsNotNone(field, "PACI has no PRO User field")
		self.assertEqual(field.options, "User")

	def test_submitting_without_the_reference_is_refused(self):
		paci = self._with_the_pro(pro_user="Administrator")

		with self.assertRaises(frappe.ValidationError):
			self._submit(paci)

	def test_submitting_without_a_pro_user_is_refused(self):
		paci = self._with_the_pro(paci_reference_number="PACI-REF-1")

		with self.assertRaises(frappe.ValidationError):
			self._submit(paci)

	def test_submitting_with_both_goes_through(self):
		paci = self._with_the_pro(pro_user="Administrator", paci_reference_number="PACI-REF-1")

		self._submit(paci)

		self.assertEqual(paci.workflow_state, "Pending by PACI")

	def test_opening_the_application_does_not_demand_them(self):
		"""A Preparation opens a first application knowing neither."""
		paci = self._with_the_pro()

		self.assertFalse(paci.pro_user)
		self.assertFalse(paci.paci_reference_number)

	def test_the_decision_after_it_belongs_to_the_gr_operator(self):
		workflow = frappe.get_doc("Workflow", "PACI")
		allowed = {
			(t.state, t.action): t.allowed
			for t in workflow.transitions
			if t.state == "Pending by PACI"
		}
		self.assertEqual(allowed[("Pending by PACI", "Approve")], "Government Relations Operator")
		self.assertEqual(allowed[("Pending by PACI", "Reject")], "Government Relations Operator")
