# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002097: the renamed supervisor state, the attachment that stopped being demanded, and
what an amended permit owes."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from one_fm.grd.doctype.preparation.preparation import create_documents_for_row

OLD_STATE = "Pending By Supervisor"
NEW_STATE = "Pending GR Manager"


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


class TestWorkPermitEnhancements(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.designation_before = frappe.db.get_value(
			"Employee", self.employee, "one_fm_pam_designation"
		)

	def tearDown(self):
		frappe.db.set_value(
			"Employee", self.employee, "one_fm_pam_designation", self.designation_before,
			update_modified=False,
		)

	def _a_permit(self, action="Local Transfer"):
		preparation = frappe.get_doc({
			"doctype": "Preparation",
			"category": "Onboarding",
			"posting_date": nowdate(),
			"preparation_record": [{"employee": self.employee, "renewal_or_extend": action}],
		})
		preparation.flags.ignore_permissions = True
		preparation.insert()
		permit = create_documents_for_row(preparation.preparation_record[0], preparation.name)

		# Required on the way out of Pending GR Manager for a transfer, and not what any of
		# these cases is about.
		permit.db_set("reference_number_on_pam_registration", "PAM-REG-1")
		permit.db_set("work_permit_expiry_date", add_days(nowdate(), 365))
		permit.reload()
		return permit

	def _with_no_designation(self, permit, amendment_no):
		"""A permit amended `amendment_no` times whose designation is genuinely blank.

		Cleared on the Employee as well: pam_designation is fetched from there on every save,
		so clearing it on the permit alone would be undone before validate saw it.
		"""
		frappe.db.set_value("Employee", self.employee, "one_fm_pam_designation", None, update_modified=False)
		permit.db_set("amendment_no", amendment_no)
		permit.db_set("pam_designation", None)
		permit.db_set("workflow_state", NEW_STATE)
		permit.reload()
		return permit

	# ── the rename ────────────────────────────────────────────────────────────────

	def test_the_workflow_knows_the_new_name_and_not_the_old(self):
		workflow = frappe.get_doc("Workflow", "Work Permit")
		states = {state.state for state in workflow.states}

		self.assertIn(NEW_STATE, states)
		self.assertNotIn(OLD_STATE, states, "two states for the same step split the queue")

	def test_no_permit_is_left_in_the_old_state(self):
		"""A permit in a state the workflow no longer has is unreachable by any action."""
		self.assertEqual(frappe.db.count("Work Permit", {"workflow_state": OLD_STATE}), 0)

	def test_the_supervisor_is_still_assigned_the_state(self):
		rule = frappe.get_doc("Assignment Rule", "Work Permit - GRD Supervisor")
		self.assertIn(NEW_STATE, rule.assign_condition)
		self.assertNotIn(OLD_STATE, rule.assign_condition)

	def test_the_pifss_state_of_the_same_name_is_untouched(self):
		"""A different process happens to use the same words."""
		workflow = frappe.get_doc("Workflow", "PIFSS Monthly Deduction")
		self.assertIn(OLD_STATE, {state.state for state in workflow.states})

	# ── the list view ─────────────────────────────────────────────────────────────

	def test_the_list_shows_who_the_permit_is_for(self):
		field = frappe.get_meta("Work Permit").get_field("employee_name")
		self.assertIsNotNone(field)
		self.assertTrue(field.in_list_view)
		self.assertEqual(field.fetch_from, "employee.employee_name")

	def test_the_name_is_fetched_from_the_employee(self):
		permit = self._a_permit()
		self.assertEqual(
			permit.employee_name,
			frappe.db.get_value("Employee", permit.employee, "employee_name"),
		)

	# ── the attachment that is no longer demanded ─────────────────────────────────

	def test_a_transfer_leaves_the_supervisor_without_its_attachment(self):
		"""The permit arrives from PAM as a reference number, already required a state
		earlier; blocking on the scan of it stalled transfers that were otherwise done."""
		permit = self._a_permit()
		# The state it is actually handed on from - Draft reaches the supervisor only
		# through Apply Online by PRO.
		permit.db_set("workflow_state", "Apply Online by PRO")
		permit.reload()

		permit.workflow_state = NEW_STATE
		permit.save(ignore_permissions=True)

		self.assertEqual(permit.workflow_state, NEW_STATE)
		self.assertFalse(permit.attach_work_permit)

	# ── what an amended permit owes ───────────────────────────────────────────────

	def test_an_amended_permit_needs_a_pam_designation(self):
		permit = self._with_no_designation(self._a_permit(), amendment_no=1)

		permit.workflow_state = "Pending By PAM"
		with self.assertRaises(frappe.ValidationError):
			permit.save(ignore_permissions=True)

	def test_an_amended_permit_with_a_designation_moves_on(self):
		permit = self._a_permit()
		frappe.db.set_value(
			"Employee", self.employee, "one_fm_pam_designation", "_Test PAM Designation",
			update_modified=False,
		)
		permit.db_set("amendment_no", 1)
		permit.db_set("workflow_state", NEW_STATE)
		permit.reload()

		permit.workflow_state = "Pending By PAM"
		permit.save(ignore_permissions=True)

		self.assertEqual(permit.workflow_state, "Pending By PAM")

	def test_a_permit_never_amended_is_not_asked_for_one(self):
		permit = self._with_no_designation(self._a_permit(), amendment_no=0)
		self.assertEqual(permit.amendment_no, 0)

		permit.workflow_state = "Pending By PAM"
		permit.save(ignore_permissions=True)

		self.assertEqual(permit.workflow_state, "Pending By PAM")

	def test_staying_in_the_state_is_not_a_transition(self):
		"""The check is on the way out, so a save that does not move must not fire it."""
		permit = self._with_no_designation(self._a_permit(), amendment_no=2)

		permit.save(ignore_permissions=True)

		self.assertEqual(permit.workflow_state, NEW_STATE)
