# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002610: the Visa Request is assigned from grd_operator, not from the Process Task.

Migrating the configuration approved on the BA site. Only two values change - rule and
field - and the tests below are mostly about what must NOT have changed with them: both
conditions, all seven days, the empty users table and the second rule on the same doctype.

Converted in place rather than added alongside the old one. The BA site carries it as a
second rule whose name differs by a trailing "s"; confirmed with the requester that one
rule is what we want here.
"""

import inspect

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.assignment_rule.assignment_rule import get_assignment_rule_json_file
from one_fm.patches.v15_0.grd_operator_visa_request_assign_by_field import (
	FIELD,
	RULE,
	RULE_TYPE,
)

MANAGER_RULE = "GRD Manager - Visa Request"


def fixture():
	return get_assignment_rule_json_file("grd_operator_visa_request.json")


class TestHowTheAssigneeIsChosen(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.rule = fixture()

	def test_it_is_based_on_a_field(self):
		self.assertEqual(self.rule["rule"], RULE_TYPE)

	def test_the_field_is_grd_operator(self):
		self.assertEqual(self.rule["field"], FIELD)

	def test_it_no_longer_reads_the_process_task(self):
		self.assertNotEqual(self.rule["rule"], "Based on Process Task")
		self.assertNotEqual(self.rule["field"], "owner")

	def test_grd_operator_is_a_user_link_so_it_can_be_assigned_to(self):
		# Based on Field assigns to whatever the field holds. If it were not a User link,
		# the rule would try to assign to something that is not a person, and fail quietly.
		field = frappe.get_meta("Visa Request").get_field(FIELD)
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "User")

	def test_the_field_is_visible_to_the_person_who_has_to_set_it(self):
		# The criterion is "Given a user is selected in the grd_operator field". A hidden
		# field is one nobody can select into.
		self.assertFalse(frappe.get_meta("Visa Request").get_field(FIELD).hidden)


class TestWhatMustNotHaveChanged(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.rule = fixture()

	def test_the_rule_keeps_its_name(self):
		# Converted in place. A renamed rule would leave the old one still assigning.
		self.assertEqual(self.rule["name"], RULE)

	def test_it_is_still_enabled_on_visa_request(self):
		self.assertEqual(self.rule["disabled"], 0)
		self.assertEqual(self.rule["document_type"], "Visa Request")

	def test_the_assign_condition_is_untouched(self):
		self.assertEqual(
			self.rule["assign_condition"],
			'workflow_state in ("Pending by GRD Operator", "Pending By PAM","Pending Visa Issuance", "Awaiting Visa Cancellation")',
		)

	def test_the_unassign_condition_is_untouched(self):
		self.assertEqual(
			self.rule["unassign_condition"],
			'workflow_state not in ("Awaiting Quota Availability", "Pending By MOI", "Pending Visa Issuance", "Pending Cancel Work Permit", "Pending by GRD Operator", "Pending By PAM", "Awaiting Visa Cancellation")',
		)

	def test_all_seven_days_are_still_there(self):
		# An empty days table does not stop a rule firing - is_rule_not_applicable_today()
		# reads it as "every day" - so losing these would be invisible until someone looked.
		self.assertEqual(
			[row["day"] for row in self.rule["assignment_days"]],
			["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
		)

	def test_the_users_table_is_still_empty(self):
		# Based on Field takes the assignee from the document, not from this list.
		self.assertEqual(self.rule["users"], [])

	def test_it_still_shows_the_workflow_buttons(self):
		self.assertEqual(self.rule["is_assignment_rule_with_workflow"], 1)

	def test_the_notification_body_is_untouched(self):
		self.assertIn("requires your attention/action", self.rule["description"])
		self.assertIn("{{job_applicant}}", self.rule["description"])

	def test_the_grd_manager_rule_is_left_alone(self):
		# Disabled on the BA site, enabled here. Out of this story's scope, and turning it
		# off would stop assignments on Pending GRD Manager Approval. Read off the executable
		# body rather than the file, so the prose explaining the decision cannot fail it.
		from one_fm.patches.v15_0 import grd_operator_visa_request_assign_by_field as patch

		self.assertNotIn(MANAGER_RULE, inspect.getsource(patch.execute))
		self.assertEqual(RULE, "GRD Operator - Visa Request")


class TestThePatch(FrappeTestCase):
	def test_it_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn(
			"one_fm.patches.v15_0.grd_operator_visa_request_assign_by_field", patches
		)

	def test_it_runs_after_the_rule_is_created(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertLess(
			patches.index("add_assignment_rule_groperator_visa_request"),
			patches.index("grd_operator_visa_request_assign_by_field"),
		)

	def test_it_checks_that_the_change_actually_landed(self):
		# create_assignment_rule catches its own exceptions and writes an Error Log, so a
		# failed conversion would otherwise look like a successful migration while the rule
		# carried on assigning to the Process Task's owner.
		from one_fm.patches.v15_0 import grd_operator_visa_request_assign_by_field as patch

		body = inspect.getsource(patch.execute)
		self.assertIn("frappe.db.get_value(", body)
		self.assertIn("frappe.throw(", body)

	def test_it_does_nothing_when_the_rule_is_absent(self):
		from one_fm.patches.v15_0 import grd_operator_visa_request_assign_by_field as patch

		real = frappe.db.exists
		frappe.db.exists = lambda *a, **kw: False
		self.addCleanup(setattr, frappe.db, "exists", real)

		patch.execute()  # must not raise
