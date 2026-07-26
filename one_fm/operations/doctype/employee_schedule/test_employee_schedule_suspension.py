# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.workflow.workflow import get_workflow_json_file
from one_fm.patches.v15_0.add_employee_schedule_suspension_workflow import (
	APPROVER_ROLES,
	WORKFLOW_NAME,
)


class TestEmployeeScheduleSuspensionWorkflow(FrappeTestCase):
	"""
	WI-001694: the suspension workflow definition and the patch that installs it.

	These exist because the workflow silently failed to install: it referenced the role
	"Operations Admin", which did not exist, so the Workflow insert failed link
	validation - and create_workflow() logs and swallows that, leaving bench migrate
	looking clean while the roster raised "Unknown column 'workflow_state'".
	"""

	def setUp(self):
		self.workflow = get_workflow_json_file("employee_schedule.json")

	def test_every_role_the_workflow_references_is_created_by_the_patch(self):
		# The regression guard. A Workflow Transition or state referencing a role that
		# does not exist fails the whole insert, so the patch must create every role the
		# definition names.
		referenced = {t["allowed"] for t in self.workflow["transitions"] if t.get("allowed")}
		referenced |= {s["allow_edit"] for s in self.workflow["states"] if s.get("allow_edit")}

		missing = referenced - set(APPROVER_ROLES)
		self.assertEqual(
			missing,
			set(),
			msg=f"workflow references roles the patch does not create: {sorted(missing)}",
		)

	def test_approver_roles_match_the_acceptance_criteria(self):
		# AC: Approve/Reject are available to exactly these four roles.
		self.assertEqual(
			set(APPROVER_ROLES),
			{"Operations Manager", "Operations Admin", "General Manager", "System Manager"},
		)

	def test_approve_and_reject_are_open_to_all_four_approver_roles(self):
		for action in ("Approve", "Reject"):
			allowed = {
				t["allowed"]
				for t in self.workflow["transitions"]
				if t["action"] == action and t["state"] == "Pending Suspension"
			}
			self.assertEqual(set(APPROVER_ROLES), allowed, msg=action)

	def test_workflow_shape_matches_the_story(self):
		# Active -> Pending Suspension -> Suspended (Approve) / Active (Reject)
		self.assertEqual(self.workflow["document_type"], "Employee Schedule")
		self.assertEqual(self.workflow["workflow_state_field"], "workflow_state")
		self.assertEqual(
			{s["state"] for s in self.workflow["states"]},
			{"Active", "Pending Suspension", "Suspended"},
		)

		transitions = {(t["state"], t["action"], t["next_state"]) for t in self.workflow["transitions"]}
		self.assertIn(("Active", "Request Suspension", "Pending Suspension"), transitions)
		self.assertIn(("Pending Suspension", "Approve", "Suspended"), transitions)
		self.assertIn(("Pending Suspension", "Reject", "Active"), transitions)

	def test_no_workflow_state_is_left_submittable(self):
		# Employee Schedule is not submittable; a non-zero doc_status would make the
		# workflow un-runnable against it.
		for state in self.workflow["states"]:
			self.assertEqual(str(state.get("doc_status", "0")), "0", msg=state["state"])

	def test_installed_workflow_name_is_what_the_patch_verifies(self):
		# The patch throws if this name is absent after install, so a typo here would
		# turn a working install into a failing patch.
		self.assertEqual(self.workflow["workflow_name"], WORKFLOW_NAME)
