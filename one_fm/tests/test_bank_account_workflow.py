# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for who can set an Active Bank Account inactive."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides.workflow import get_transitions


def _user(email, *roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": roles[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	user = frappe.get_doc("User", email)
	user.set("roles", [])
	user.add_roles(*roles)
	return email


def _actions(user, state):
	doc = {"doctype": "Bank Account", "name": "BA-WF-TEST", "workflow_state": state}
	return [t.action for t in get_transitions(doc, user=user)]


class TestBankAccountSetInactive(FrappeTestCase):
	def test_onboarding_officer_can_set_an_active_account_inactive(self):
		user = _user("ba-wf-onboarding@example.com", "Onboarding Officer", "HR User")
		self.assertIn("Set Inactive", _actions(user, "Active Account"))

	def test_onboarding_officer_cannot_reactivate(self):
		user = _user("ba-wf-onboarding@example.com", "Onboarding Officer", "HR User")
		self.assertNotIn("Set as Active", _actions(user, "Inactive Account"))

	def test_payroll_operator_keeps_set_inactive(self):
		user = _user("ba-wf-payroll@example.com", "Payroll Operator")
		self.assertIn("Set Inactive", _actions(user, "Active Account"))

	def test_hr_user_alone_cannot_set_inactive(self):
		user = _user("ba-wf-hr@example.com", "HR User")
		self.assertNotIn("Set Inactive", _actions(user, "Active Account"))
