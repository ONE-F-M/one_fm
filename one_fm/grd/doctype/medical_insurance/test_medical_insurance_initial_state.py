# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002098: the state a Medical Insurance policy opens in."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.grd.doctype.medical_insurance.medical_insurance import (
	APPLY_ONLINE_BY_PRO,
	DRAFT,
	initial_workflow_state,
)
from one_fm.grd.doctype.preparation.preparation import create_documents_for_row


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


def _opened_by_a_preparation(action):
	"""The Medical Insurance a one-row Preparation with this Action opens."""
	preparation = frappe.get_doc(
		{
			"doctype": "Preparation",
			"posting_date": nowdate(),
			"preparation_record": [
				{"employee": _an_active_employee(), "renewal_or_extend": action}
			],
		}
	).insert(ignore_permissions=True)

	create_documents_for_row(preparation.preparation_record[0], preparation.name)

	return frappe.get_last_doc("Medical Insurance", filters={"preparation": preparation.name})


class TestMedicalInsuranceInitialState(FrappeTestCase):
	def test_an_overseas_permit_opens_its_policy_in_draft(self):
		for work_permit_type in ("Overseas", "Overseas (Government)"):
			with self.subTest(work_permit_type=work_permit_type):
				self.assertEqual(initial_workflow_state(work_permit_type), DRAFT)

	def test_every_other_permit_goes_straight_to_the_pro(self):
		"""Draft is the workflow's first state now, so this is what stops it becoming the
		default for a renewal or a transfer."""
		for work_permit_type in ("Renewal Non Kuwaiti", "Local Transfer"):
			with self.subTest(work_permit_type=work_permit_type):
				self.assertEqual(initial_workflow_state(work_permit_type), APPLY_ONLINE_BY_PRO)

	def test_the_workflow_offers_a_way_out_of_draft(self):
		workflow = frappe.get_doc("Workflow", "Medical Insurance")
		self.assertIn(DRAFT, {state.state for state in workflow.states})
		self.assertIn(
			(DRAFT, "Submit", APPLY_ONLINE_BY_PRO),
			{(t.state, t.action, t.next_state) for t in workflow.transitions},
		)

	def test_a_preparation_opens_an_overseas_policy_in_draft(self):
		self.assertEqual(_opened_by_a_preparation("Overseas").workflow_state, DRAFT)

	def test_a_local_transfer_policy_still_opens_with_the_pro(self):
		self.assertEqual(
			_opened_by_a_preparation("Local Transfer").workflow_state, APPLY_ONLINE_BY_PRO
		)
