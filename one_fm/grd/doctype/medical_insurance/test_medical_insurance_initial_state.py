# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The state a Medical Insurance policy opens in."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.grd.doctype.preparation.preparation import (
	category_for_action,
	create_documents_for_row,
)

DRAFT = "Draft"
APPLY_ONLINE_BY_GR_OPERATOR = "Apply Online by GR Operator"


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
			"category": category_for_action(action),
			"preparation_record": [
				{"employee": _an_active_employee(), "renewal_or_extend": action}
			],
		}
	).insert(ignore_permissions=True)

	create_documents_for_row(preparation.preparation_record[0], preparation.name)

	return frappe.get_last_doc("Medical Insurance", filters={"preparation": preparation.name})


class TestMedicalInsuranceInitialState(FrappeTestCase):
	def test_a_preparation_opens_an_overseas_policy_in_draft(self):
		self.assertEqual(_opened_by_a_preparation("Overseas").workflow_state, DRAFT)

	def test_a_preparation_opens_a_renewal_policy_in_draft(self):
		"""Draft is the workflow's first state, and nothing writes past it behind the
		workflow's back."""
		self.assertEqual(_opened_by_a_preparation("Renewal Expat").workflow_state, DRAFT)

	def test_a_local_transfer_policy_opens_in_draft(self):
		self.assertEqual(_opened_by_a_preparation("Local Transfer").workflow_state, DRAFT)

	def test_the_workflow_offers_a_way_out_of_draft(self):
		workflow = frappe.get_doc("Workflow", "Medical Insurance")
		self.assertIn(DRAFT, {state.state for state in workflow.states})
		self.assertIn(
			(DRAFT, "Submit", APPLY_ONLINE_BY_GR_OPERATOR),
			{(t.state, t.action, t.next_state) for t in workflow.transitions},
		)

	def test_the_move_patch_is_idempotent(self):
		from one_fm.patches.v15_0 import move_medical_insurance_drafts_to_gr_operator as patch

		policy = _opened_by_a_preparation("Local Transfer")
		frappe.db.set_value(
			"Medical Insurance", policy.name, "workflow_state", patch.OLD_STATE, update_modified=False
		)
		modified = frappe.db.get_value("Medical Insurance", policy.name, "modified")

		patch.execute()
		self.assertEqual(
			frappe.db.get_value("Medical Insurance", policy.name, "workflow_state"),
			APPLY_ONLINE_BY_GR_OPERATOR,
		)
		self.assertEqual(frappe.db.get_value("Medical Insurance", policy.name, "modified"), modified)

		patch.execute()
		self.assertEqual(
			frappe.db.get_value("Medical Insurance", policy.name, "workflow_state"),
			APPLY_ONLINE_BY_GR_OPERATOR,
		)
