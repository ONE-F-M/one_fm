# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Visa Request migration from the BA site (WI-001773).

The doctype, its workflow and its three assignment rules were brought over together, so
these check them as one thing: a state renamed in the workflow has to be renamed in
every condition, every field expression and every line of controller code that names it,
or the part left behind fails silently.
"""

import json
import re
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.assignment_rule.assignment_rule import get_assignment_rule_json_file
from one_fm.custom.workflow.workflow import get_workflow_json_file

DOCTYPE = "Visa Request"
WORKFLOW = "Visa Request"

RULES = {
	"GRD Operator - Visa Request": "grd_operator_visa_request.json",
	"GRD Manager - Visa Request": "grd_manager_visa_request.json",
	"Recruiter - Visa Request": "recruiter_visa_request.json",
}

# Renamed by WI-001773; nothing should still be pointing at the left-hand side.
RETIRED_STATES = (
	"Pending Initial Review",
	"Pending Visa",
	"Pending Visa Request Cancel",
	"Canceled",
)

RETIRED_RULE_NAME = "GROperator - Visa Request"

CONTROLLER = Path(frappe.get_app_path("one_fm", "visa_management", "doctype", "visa_request"))


def workflow_states():
	return [s.state for s in frappe.get_doc("Workflow", WORKFLOW).states]


class TestTheDoctypeMatchesWhatWasSupplied(FrappeTestCase):
	def test_the_fields_the_export_added_are_all_there(self):
		meta = frappe.get_meta(DOCTYPE)
		for fieldname in (
			"date_of_birth",
			"degree_certificate",
			"custom_pam_file",
			"custom_visa_application_date",
			"custom_pam_designation_list",
			"custom_work_permit_number",
			"visa_issue_date",
			"visa_expiry_date",
			"payment_date",
		):
			self.assertTrue(meta.has_field(fieldname), msg=fieldname)

	def test_the_field_the_export_dropped_is_gone(self):
		self.assertFalse(frappe.get_meta(DOCTYPE).has_field("pam_designation"))

	def test_the_candidate_country_process_link_is_kept(self):
		# Deliberately retained against the export: the controller writes it on every
		# save and Candidate Country Process finds its Visa Request through it, so
		# dropping it would break that link in both directions.
		self.assertTrue(frappe.get_meta(DOCTYPE).has_field("candidate_country_process"))

	def test_every_link_field_points_at_a_doctype_that_exists(self):
		# A Link to a missing DocType breaks the form for everyone, and two of the added
		# fields point at masters that only exist if the GRD module came across too.
		for field in frappe.get_meta(DOCTYPE).get_link_fields():
			self.assertTrue(
				frappe.db.exists("DocType", field.options),
				msg=f"{field.fieldname} -> {field.options}",
			)

	def test_the_file_carries_no_ui_export_noise(self):
		# The supplied file was copied out of the UI, so it spelled out every default and
		# every child-row stamp. Frappe's own exporter writes neither.
		on_disk = json.loads((CONTROLLER / "visa_request.json").read_text())
		noise = {"docstatus", "idx", "migration_hash", "translated_doctype", "custom"}
		self.assertEqual(set(on_disk) & noise, set())

		row_noise = {"name", "parent", "parentfield", "parenttype", "creation", "modified",
		             "modified_by", "owner", "doctype", "__islocal", "__unsaved"}
		for row in on_disk["fields"]:
			self.assertEqual(set(row) & row_noise, set(), msg=row.get("fieldname"))

	def test_fields_and_field_order_describe_the_same_set(self):
		on_disk = json.loads((CONTROLLER / "visa_request.json").read_text())
		self.assertEqual(
			sorted(f["fieldname"] for f in on_disk["fields"]),
			sorted(on_disk["field_order"]),
		)


class TestTheWorkflow(FrappeTestCase):
	def test_it_kept_its_name_and_is_the_only_one_on_the_doctype(self):
		# The export was named "Visa Request new Testing". Two active workflows on one
		# doctype is not a thing, and the live one owns the open Workflow Actions.
		self.assertEqual(
			frappe.get_all("Workflow", filters={"document_type": DOCTYPE}, pluck="name"),
			[WORKFLOW],
		)
		self.assertTrue(frappe.db.get_value("Workflow", WORKFLOW, "is_active"))

	def test_it_matches_the_shipped_definition(self):
		supplied = get_workflow_json_file("visa_request.json")
		applied = frappe.get_doc("Workflow", WORKFLOW)

		self.assertEqual(
			[s["state"] for s in supplied["states"]], [s.state for s in applied.states]
		)
		self.assertEqual(
			[(t["state"], t["action"], t["next_state"]) for t in supplied["transitions"]],
			[(t.state, t.action, t.next_state) for t in applied.transitions],
		)

	def test_every_state_has_a_master_spelled_exactly_the_same_way(self):
		"""The trap this migration hit.

		Workflow State is named by its title and MariaDB compares those names
		case-insensitively, so writing a state that differs from an existing master only
		in case creates nothing and Frappe's link validation quietly rewrites the state
		back. Everything then still matches in SQL while every case-sensitive Python
		comparison against the state fails.
		"""
		for state in workflow_states():
			master = frappe.db.exists("Workflow State", state)
			self.assertTrue(master, msg=f"no Workflow State master for {state!r}")
			self.assertEqual(master, state, msg="master casing differs from the workflow")

	def test_every_transition_names_declared_states(self):
		states = set(workflow_states())
		for t in frappe.get_doc("Workflow", WORKFLOW).transitions:
			self.assertIn(t.state, states, msg=f"{t.action}: from")
			self.assertIn(t.next_state, states, msg=f"{t.action}: to")

	def test_every_action_has_a_master(self):
		for t in frappe.get_doc("Workflow", WORKFLOW).transitions:
			self.assertTrue(
				frappe.db.exists("Workflow Action Master", t.action), msg=t.action
			)

	def test_no_document_is_left_in_a_state_the_workflow_dropped(self):
		# Four states were renamed. A document left on an old name has no transitions and
		# cannot be moved by anyone.
		states = set(workflow_states())
		stranded = [
			r.workflow_state
			for r in frappe.get_all(
				DOCTYPE, fields=["distinct workflow_state as workflow_state"]
			)
			if r.workflow_state and r.workflow_state not in states
		]
		self.assertEqual(stranded, [])


class TestNothingStillNamesARetiredState(FrappeTestCase):
	def test_the_workflow_does_not(self):
		states = set(workflow_states())
		for retired in RETIRED_STATES:
			self.assertNotIn(retired, states, msg=retired)

	def test_the_controller_and_its_client_script_do_not(self):
		for filename in ("visa_request.py", "visa_request.js"):
			source = (CONTROLLER / filename).read_text()
			for retired in RETIRED_STATES:
				# "Pending Visa" is a prefix of live states, so match the quoted string.
				for quoted in (f'"{retired}"', f"'{retired}'"):
					self.assertNotIn(quoted, source, msg=f"{filename}: {retired}")

	def test_every_state_the_controller_names_is_a_real_state(self):
		# The other half of the same problem: a renamed state that the controller spells
		# almost right makes its validation unreachable rather than failing loudly.
		states = set(workflow_states())
		source = (CONTROLLER / "visa_request.py").read_text()
		for named in re.findall(r'workflow_state == "([^"]+)"', source):
			self.assertIn(named, states, msg=named)

	def test_every_state_a_field_expression_names_is_a_real_state(self):
		states = set(workflow_states())
		for field in frappe.get_meta(DOCTYPE).fields:
			for key in ("depends_on", "mandatory_depends_on", "read_only_depends_on"):
				expr = field.get(key) or ""
				if "workflow_state" not in expr:
					continue
				for named in re.findall(r'workflow_state\s*==\s*"([^"]+)"', expr):
					self.assertIn(named, states, msg=f"{field.fieldname}.{key}: {named}")


class TestTheAssignmentRules(FrappeTestCase):
	def test_all_three_exist_under_the_names_this_app_uses(self):
		for name in RULES:
			self.assertTrue(frappe.db.exists("Assignment Rule", name), msg=name)

	def test_the_operator_rule_was_renamed_not_replaced(self):
		# ToDo.assignment_rule is a Link, so a replacement would orphan every open
		# assignment raised under the old name.
		self.assertFalse(frappe.db.exists("Assignment Rule", RETIRED_RULE_NAME))
		self.assertEqual(frappe.db.count("ToDo", {"assignment_rule": RETIRED_RULE_NAME}), 0)

	def test_each_rule_is_applied_as_its_fixture_says(self):
		for name, json_file in RULES.items():
			supplied = get_assignment_rule_json_file(json_file)
			applied = frappe.get_doc("Assignment Rule", name)
			for field in ("document_type", "rule", "assign_condition", "unassign_condition",
			              "is_assignment_rule_with_workflow", "disabled"):
				self.assertEqual(
					str(supplied.get(field) or ""),
					str(applied.get(field) or ""),
					msg=f"{name}.{field}",
				)

	def test_every_state_a_condition_names_is_a_real_state(self):
		# Conditions are evaluated in Python, so a state that no longer exists - or that
		# differs only in case - turns the condition into a silent no-op.
		states = set(workflow_states())
		for name in RULES:
			rule = frappe.get_doc("Assignment Rule", name)
			condition = f"{rule.assign_condition} {rule.unassign_condition}"
			named = set(re.findall(r'"([^"]+)"', condition))
			self.assertTrue(named, msg=f"{name}: condition names no state")
			self.assertEqual(named - states, set(), msg=name)

	def test_the_conditions_evaluate_for_every_state(self):
		for name in RULES:
			rule = frappe.get_doc("Assignment Rule", name)
			for condition in (rule.assign_condition, rule.unassign_condition):
				if not condition:
					continue
				self.assertNotIn("doc.", condition, msg=name)
				for state in workflow_states() + [None, ""]:
					try:
						frappe.safe_eval(
							condition, None, frappe._dict(workflow_state=state)
						)
					except Exception as e:
						self.fail(f"{name}: {condition!r} on {state!r} raised {e}")

	def test_each_rule_assigns_on_its_own_states_and_releases_on_the_rest(self):
		for name in RULES:
			rule = frappe.get_doc("Assignment Rule", name)
			mine = set(re.findall(r'"([^"]+)"', rule.assign_condition))
			for state in workflow_states():
				doc = frappe._dict(workflow_state=state)
				assigns = frappe.safe_eval(rule.assign_condition, None, doc)
				releases = frappe.safe_eval(rule.unassign_condition, None, doc)
				self.assertEqual(bool(assigns), state in mine, msg=f"{name} on {state}")
				if state in mine:
					self.assertFalse(releases, msg=f"{name} releases its own {state}")

	def test_the_process_task_rules_resolve_to_a_user(self):
		# get_user_based_on_process_task returns the linked task's employee_user with no
		# fallback, so an unlinked rule assigns nobody.
		for name, json_file in RULES.items():
			rule = frappe.get_doc("Assignment Rule", name)
			if rule.rule != "Based on Process Task":
				continue
			self.assertTrue(rule.custom_routine_task, msg=name)
			user = frappe.db.get_value(
				"Process Task", rule.custom_routine_task, "employee_user"
			)
			self.assertTrue(user, msg=f"{name}: its task names no employee_user")
			self.assertTrue(frappe.db.exists("User", user), msg=f"{name}: {user}")

	def test_no_two_rules_share_a_process_task(self):
		linked = [
			frappe.db.get_value("Assignment Rule", name, "custom_routine_task")
			for name in RULES
		]
		linked = [task for task in linked if task]
		self.assertEqual(len(set(linked)), len(linked), msg=linked)

	def test_every_rule_covers_all_seven_days(self):
		for name in RULES:
			self.assertEqual(
				[d.day for d in frappe.get_doc("Assignment Rule", name).assignment_days],
				["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
				msg=name,
			)
