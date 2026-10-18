# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002098 / WI-003673: the state a Medical Insurance policy opens in.

Every policy opens in the workflow's own first state, Draft, whatever kind of Work Permit
it was opened against.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.grd.doctype.preparation.preparation import create_documents_for_row

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
