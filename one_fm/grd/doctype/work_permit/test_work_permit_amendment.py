# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002108: reapplying after a rejection, and counting amendments without duplicating.

The two ways a permit comes back from PAM. A rejection ends the application and a fresh one
is raised from it; an amendment is a correction to the permit PAM is already holding, so it
stays the same record and only the counter moves.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.grd.doctype.preparation.preparation import create_documents_for_row
from one_fm.grd.doctype.work_permit.work_permit import reapply_work_permit

AMEND_TRANSITION = ("Pending By PAM", "Amend", "Pending GR Manager")


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


class TestWorkPermitAmendment(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()

	def _permit_from_a_preparation(self):
		"""A permit with a Preparation behind it, which is what a real one has."""
		preparation = frappe.get_doc(
			{
				"doctype": "Preparation",
				# Ignored until WI-002101 adds the field, mandatory once it does.
				"category": "Onboarding",
				"posting_date": nowdate(),
				"preparation_record": [
					{"employee": self.employee, "renewal_or_extend": "Overseas"}
				],
			}
		).insert(ignore_permissions=True)

		return create_documents_for_row(preparation.preparation_record[0], preparation.name)

	# ── Amendment ─────────────────────────────────────────────────────────────────

	def test_the_workflow_offers_an_amend_action(self):
		workflow = frappe.get_doc("Workflow", "Work Permit")
		self.assertIn(
			AMEND_TRANSITION,
			{(t.state, t.action, t.next_state) for t in workflow.transitions},
		)

	def test_amending_increments_the_counter_on_the_same_record(self):
		permit = self._permit_from_a_preparation()
		self.assertEqual(permit.amendment_no, 0)

		for expected in (1, 2, 3):
			permit.db_set("workflow_state", "Pending By PAM")
			permit.reload()
			permit.workflow_state = "Pending GR Manager"
			permit.save(ignore_permissions=True)

			permit.reload()
			self.assertEqual(permit.amendment_no, expected)

		# One record throughout - the point of the counter.
		self.assertEqual(
			frappe.db.count("Work Permit", {"employee": permit.employee, "amended_from": permit.name}),
			0,
		)

	def test_a_state_change_that_is_not_an_amendment_leaves_the_counter_alone(self):
		permit = self._permit_from_a_preparation()

		permit.db_set("workflow_state", "Pending GR Manager")
		permit.reload()
		permit.workflow_state = "Pending By PAM"
		permit.save(ignore_permissions=True)

		permit.reload()
		self.assertEqual(permit.amendment_no, 0)

	def test_the_counter_is_a_list_view_column(self):
		field = frappe.get_meta("Work Permit").get_field("amendment_no")
		self.assertTrue(field.in_list_view)
		self.assertTrue(field.read_only)

	# ── Reapply ───────────────────────────────────────────────────────────────────

	def test_reapplying_carries_the_candidate_and_the_preparation(self):
		rejected = self._permit_from_a_preparation()
		rejected.db_set("workflow_state", "Rejected")
		rejected.db_set("reference_number_on_pam", "PAM-REJECTED-1")
		rejected.reload()

		reapplication = frappe.get_doc(
			"Work Permit", reapply_work_permit(rejected.name)["name"]
		)

		self.assertEqual(reapplication.docstatus, 0)
		self.assertEqual(reapplication.workflow_state, "Draft")
		self.assertEqual(reapplication.employee, rejected.employee)
		self.assertEqual(reapplication.work_permit_type, rejected.work_permit_type)
		# Linked to the same Preparation, and pointing back at what it replaces.
		self.assertEqual(reapplication.preparation, rejected.preparation)
		self.assertEqual(reapplication.rejected_work_permit, rejected.name)
		# The reference PAM issued for the refused attempt does not come across.
		self.assertFalse(reapplication.reference_number_on_pam)
		self.assertFalse(reapplication.reference_number_on_pam_registration)

	def test_a_reapplication_starts_its_own_amendment_count(self):
		rejected = self._permit_from_a_preparation()
		rejected.db_set("amendment_no", 2)
		rejected.db_set("workflow_state", "Rejected")
		rejected.reload()

		reapplication = frappe.get_doc(
			"Work Permit", reapply_work_permit(rejected.name)["name"]
		)

		self.assertEqual(reapplication.amendment_no, 0)

	def test_only_a_rejected_permit_can_be_reapplied(self):
		permit = self._permit_from_a_preparation()

		with self.assertRaises(frappe.ValidationError):
			reapply_work_permit(permit.name)
