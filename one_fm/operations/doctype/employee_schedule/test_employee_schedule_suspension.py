# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.workflow.workflow import get_workflow_json_file
from one_fm.patches.v15_0.add_employee_schedule_suspension_workflow import WORKFLOW_NAME

# WI-001694 AC wording is "Operations Admin", but the role that exists in this system is
# "Operation Admin" (singular) - the workflow must name the real one or its insert fails.
APPROVER_ROLES = {
	"Operations Manager",
	"Operation Admin",
	"General Manager",
	"System Manager",
}


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

	def test_every_role_the_workflow_references_exists(self):
		"""The regression guard for the original failure.

		A Workflow Transition or state naming a role that does not exist fails the whole
		Workflow insert with LinkValidationError, and create_workflow() swallows it - so
		migrate looks clean and nothing is installed. This catches the typo class of bug
		("Operations Admin" vs the real "Operation Admin") before it ships.
		"""
		referenced = {t["allowed"] for t in self.workflow["transitions"] if t.get("allowed")}
		referenced |= {s["allow_edit"] for s in self.workflow["states"] if s.get("allow_edit")}

		missing = sorted(role for role in referenced if not frappe.db.exists("Role", role))
		self.assertEqual(
			missing, [], msg=f"workflow references roles that do not exist: {missing}"
		)

	def test_approver_roles_are_the_four_from_the_acceptance_criteria(self):
		# AC names Operations Manager, Operations Admin, General Manager and System
		# Manager. "Operations Admin" is the AC's wording for the real "Operation Admin".
		referenced = {
			t["allowed"]
			for t in self.workflow["transitions"]
			if t["state"] == "Pending Suspension" and t.get("allowed")
		}
		self.assertEqual(referenced, APPROVER_ROLES)

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


class TestPendingSuspensionCellDisplay(FrappeTestCase):
	"""
	WI-001694: the Pending Suspension colour/abbreviation on the Roster Matrix, and the
	guard that keeps the roster query working where the workflow is not installed.
	"""

	def setUp(self):
		self.roster_js = frappe.read_file(
			frappe.get_app_path("one_fm", "one_fm", "page", "roster", "roster.js")
		)
		self.roster_html = frappe.read_file(
			frappe.get_app_path("one_fm", "one_fm", "page", "roster", "roster.html")
		)

	def test_pending_suspension_has_its_own_colour_and_abbreviation(self):
		self.assertIn('"Pending Suspension": "pendingsuspensioncolor"', self.roster_js)
		self.assertIn('"Pending Suspension": "PS"', self.roster_js)

	def test_pending_suspension_colour_differs_from_suspended(self):
		# The two states must not be mistakable for one another on the matrix.
		self.assertIn(".pendingsuspensioncolor", self.roster_html)
		self.assertIn("#795548", self.roster_html)
		self.assertNotIn("pendingsuspensioncolor {\n\t\t\tbackground-color: #f55f02", self.roster_html)

	def test_legend_entry_sits_directly_under_on_the_job_training(self):
		# Explicitly requested placement.
		ojt = self.roster_html.index("On-the-job Training</div>")
		ps = self.roster_html.index("Pending Suspension (PS)</div>")
		self.assertLess(ojt, ps, "PS legend must come after On-the-job Training")

		between = self.roster_html[ojt:ps]
		self.assertEqual(
			between.count("cardtitlecolor"),
			1,
			"another legend entry was inserted between On-the-job Training and PS",
		)

	def test_cell_override_applies_after_the_existing_class_chain(self):
		# The override must not sit inside the availability/attendance if-chain, or it
		# would change how existing statuses are coloured.
		self.assertIn('if (workflow_state === "Pending Suspension") {', self.roster_js)
		self.assertIn('bgclass = classmap["Pending Suspension"];', self.roster_js)

	def test_abbreviation_is_prepended_not_replaced(self):
		# A day can also carry a post abbreviation or an OT record; that must survive.
		self.assertIn(
			'abbrv = `${abbr_map["Pending Suspension"]}<br>` + abbrv;', self.roster_js
		)


class TestRosterQueryWorkflowStateGuard(FrappeTestCase):
	def test_column_is_only_selected_when_it_exists(self):
		from unittest.mock import patch

		from one_fm.one_fm.page.roster.employee_map import get_workflow_state_select

		with patch("frappe.db.get_table_columns", return_value=["employee", "date"]):
			# Without the Custom Field, selecting the column would break the whole roster
			# with "Unknown column 'workflow_state'".
			self.assertEqual(get_workflow_state_select(), "NULL as workflow_state")

		with patch(
			"frappe.db.get_table_columns", return_value=["employee", "date", "workflow_state"]
		):
			self.assertEqual(get_workflow_state_select(), "es.workflow_state")

	def test_alias_is_always_present_so_the_client_can_rely_on_it(self):
		from unittest.mock import patch

		from one_fm.one_fm.page.roster.employee_map import get_workflow_state_select

		for columns in ([], ["workflow_state"]):
			with patch("frappe.db.get_table_columns", return_value=columns):
				self.assertIn("workflow_state", get_workflow_state_select())
