# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A completed PACI opens a Draft salary Bank Account, assigned to HR onboarding."""

from unittest.mock import patch

import frappe
from erpnext.accounts.doctype.bank_account.bank_account import BankAccount
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from one_fm.grd.doctype.paci.paci import DEFAULT_SALARY_BANK
from one_fm.patches.v15_0 import add_bank_account_draft_assignment_rule as rule_patch

GR_OPERATOR = "Government Relations Operator"
GR_OPERATOR_USER = "paci-bank-account-gro@example.com"


def _ensure_bank():
	if not frappe.db.exists("Bank", DEFAULT_SALARY_BANK):
		frappe.get_doc({"doctype": "Bank", "bank_name": DEFAULT_SALARY_BANK}).insert(ignore_permissions=True)


def _employees_with_an_account():
	return set(frappe.get_all("Bank Account", filters={"party_type": "Employee"}, pluck="party"))


def _an_employee_without_an_account(exclude=()):
	taken = _employees_with_an_account() | set(exclude)
	for name in frappe.get_all(
		"Employee",
		filters={"status": "Active", "relieving_date": ["is", "not set"]},
		pluck="name",
		order_by="creation asc",
	):
		if name not in taken:
			return name
	raise frappe.DoesNotExistError("No active employee without a Bank Account on this site")


def _accounts_for(employee):
	return frappe.get_all(
		"Bank Account",
		filters={"party_type": "Employee", "party": employee},
		fields=["name", "account_name", "bank", "workflow_state", "onboard_employee"],
	)


def _bank_account_workflow_active():
	return bool(frappe.db.exists("Workflow", {"document_type": "Bank Account", "is_active": 1}))


def _complete_paci(employee, user=None):
	paci = frappe.get_doc({
		"doctype": "PACI",
		"employee": employee,
		"category": "Renewal",
		"date_of_application": nowdate(),
	})
	paci.flags.ignore_permissions = True
	paci.insert()
	# validate() overwrites the expiry from Employee.work_permit_expiry_date on insert,
	# which is empty for most employees; on_submit requires it.
	paci.db_set({"workflow_state": "Completed", "new_civil_id_expiry_date": add_days(nowdate(), 365)})
	paci.reload()
	if user:
		frappe.set_user(user)
	try:
		paci.submit()
	finally:
		frappe.set_user("Administrator")
	return paci


def _messages(msgprint):
	return [str(call.args[0]) for call in msgprint.call_args_list if call.args]


class TestDraftBankAccountOnPACICompletion(FrappeTestCase):
	def setUp(self):
		_ensure_bank()
		self.employee = _an_employee_without_an_account()
		self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")

	def test_an_employee_without_an_account_gets_a_draft_one(self):
		_complete_paci(self.employee)

		accounts = _accounts_for(self.employee)
		self.assertEqual(len(accounts), 1)
		self.assertEqual(accounts[0].account_name, self.employee_name)
		self.assertEqual(accounts[0].bank, DEFAULT_SALARY_BANK)
		if _bank_account_workflow_active():
			self.assertEqual(accounts[0].workflow_state, "Draft")

	def test_an_existing_account_in_any_state_is_not_duplicated(self):
		_complete_paci(self.employee)
		frappe.db.set_value("Bank Account", _accounts_for(self.employee)[0].name, "workflow_state", "Inactive Account")

		with patch("frappe.msgprint") as msgprint:
			_complete_paci(self.employee)

		self.assertEqual(len(_accounts_for(self.employee)), 1)
		self.assertIn(
			f"Bank account already exists for Employee ID {self.employee}. Skipping duplicate creation.",
			_messages(msgprint),
		)

	def test_a_name_taken_by_another_employee_gets_the_employee_id_suffix(self):
		frappe.get_doc({
			"doctype": "Bank Account",
			"account_name": self.employee_name,
			"bank": DEFAULT_SALARY_BANK,
			"civil_id": "TEST-CID",
		}).insert(ignore_permissions=True)

		_complete_paci(self.employee)

		accounts = _accounts_for(self.employee)
		self.assertEqual(len(accounts), 1)
		self.assertEqual(accounts[0].name, f"{self.employee_name} - {DEFAULT_SALARY_BANK} - {self.employee}")
		self.assertEqual(accounts[0].account_name, self.employee_name)

	def test_a_failed_insert_does_not_block_the_completion(self):
		with patch.object(BankAccount, "validate", side_effect=frappe.ValidationError("forced")):
			paci = _complete_paci(self.employee)

		paci.reload()
		self.assertEqual(paci.docstatus, 1)
		self.assertEqual(paci.workflow_state, "Completed")
		self.assertEqual(paci.paci_status, "Completed")
		self.assertEqual(_accounts_for(self.employee), [])
		self.assertTrue(frappe.db.exists("Error Log", {"reference_doctype": "PACI", "reference_name": paci.name}))

	def test_an_employee_without_a_civil_id_still_gets_one_draft_account(self):
		frappe.db.set_value("Employee", self.employee, "one_fm_civil_id", "")

		_complete_paci(self.employee)

		accounts = _accounts_for(self.employee)
		self.assertEqual(len(accounts), 1)
		if _bank_account_workflow_active():
			self.assertEqual(accounts[0].workflow_state, "Draft")
		self.assertFalse(frappe.db.get_value("Bank Account", accounts[0].name, "civil_id"))

	def test_an_employee_with_a_civil_id_passes_it_to_the_account(self):
		frappe.db.set_value("Employee", self.employee, "one_fm_civil_id", "TEST-CID-123")

		_complete_paci(self.employee)

		accounts = _accounts_for(self.employee)
		self.assertEqual(len(accounts), 1)
		self.assertEqual(frappe.db.get_value("Bank Account", accounts[0].name, "civil_id"), "TEST-CID-123")


class TestOnboardEmployeeAdvancesForAGROperator(FrappeTestCase):
	"""The move out of Duty Commencement must not depend on the completer's roles."""

	def setUp(self):
		if not frappe.db.exists("Role", GR_OPERATOR):
			self.skipTest(f"No {GR_OPERATOR} role on this site")
		_ensure_bank()
		self.onboard_employee, self.employee = self._an_onboarding_waiting_for_a_bank_account()
		self.user = self._a_gr_operator_only()

	def _an_onboarding_waiting_for_a_bank_account(self):
		with_account = _employees_with_an_account()
		for row in frappe.get_all(
			"Onboard Employee",
			filters={
				"workflow_state": "Duty Commencement",
				"salary_mode": "Bank",
				"docstatus": 1,
				"employee": ["is", "set"],
				"duty_commencement": ["is", "set"],
				"first_name_in_arabic": ["is", "set"],
				"last_name_in_arabic": ["is", "set"],
			},
			fields=["name", "employee"],
		):
			if row.employee not in with_account:
				return row.name, row.employee
		self.skipTest("No Onboard Employee in Duty Commencement without a Bank Account")

	def _a_gr_operator_only(self):
		if not frappe.db.exists("User", GR_OPERATOR_USER):
			frappe.get_doc({
				"doctype": "User",
				"email": GR_OPERATOR_USER,
				"first_name": "PACI GR Operator",
				"send_welcome_email": 0,
				"roles": [{"role": GR_OPERATOR}],
			}).insert(ignore_permissions=True)
		self.assertNotIn("Onboarding Officer", frappe.get_roles(GR_OPERATOR_USER))
		return GR_OPERATOR_USER

	def test_completion_moves_the_onboarding_to_bank_account(self):
		_complete_paci(self.employee, user=self.user)

		accounts = _accounts_for(self.employee)
		self.assertEqual(len(accounts), 1)
		self.assertEqual(accounts[0].onboard_employee, self.onboard_employee)
		state, bank_account = frappe.db.get_value(
			"Onboard Employee", self.onboard_employee, ["workflow_state", "bank_account"]
		)
		self.assertEqual(state, "Bank Account")
		self.assertEqual(bank_account, accounts[0].name)


class TestDraftAssignmentRule(FrappeTestCase):
	def setUp(self):
		if not _bank_account_workflow_active():
			self.skipTest("No active Bank Account workflow on this site")
		_ensure_bank()
		self.assignee_employee, self.assignee = self._an_employee_with_a_user()
		# The patch names the production employee; point it at one this site has.
		with patch.object(rule_patch, "EMPLOYEE", self.assignee_employee):
			rule_patch.execute()
		self.rule = frappe.get_doc("Assignment Rule", rule_patch.RULE_NAME)

	def _an_employee_with_a_user(self):
		row = frappe.db.get_value(
			"Employee",
			[["status", "=", "Active"], ["user_id", "is", "set"], ["user_id", "!=", "Administrator"]],
			["name", "user_id"],
			order_by="creation asc",
		)
		if not row:
			self.skipTest("No active employee with a user on this site")
		return row

	def test_the_rule_is_enabled_with_corrected_conditions(self):
		self.assertFalse(self.rule.disabled)
		self.assertTrue(self.rule.custom_routine_task)
		for field in ("assign_condition", "unassign_condition", "close_condition"):
			self.assertNotIn("doc.", self.rule.get(field) or "", msg=field)
		self.assertFalse(self.rule.close_condition)
		self.assertFalse(self.rule.unassign_condition)

	def _open_todos(self, bank_account, user):
		return frappe.get_all(
			"ToDo",
			filters={
				"reference_type": "Bank Account",
				"reference_name": bank_account,
				"allocated_to": user,
				"status": "Open",
			},
			pluck="name",
		)

	def test_a_draft_account_is_assigned_and_the_payroll_officer_keeps_theirs(self):
		employee = _an_employee_without_an_account(exclude=[self.assignee_employee])
		_complete_paci(employee)
		bank_account = frappe.get_doc("Bank Account", _accounts_for(employee)[0].name)

		self.assertTrue(self._open_todos(bank_account.name, self.assignee))

		payroll_officer = frappe.db.get_single_value("HR and Payroll Additional Settings", "payroll_officer")
		if not payroll_officer or payroll_officer == self.assignee:
			return
		# Draft -> Open Request requires new_account, checked on the saved document.
		bank_account.db_set("new_account", 1)
		bank_account.reload()
		bank_account.workflow_state = "Open Request"
		# The PACI bypass only covers the insert; the first manual save needs a Civil ID.
		bank_account.civil_id = bank_account.civil_id or "TEST-CID"
		bank_account.save(ignore_permissions=True)

		self.assertTrue(self._open_todos(bank_account.name, payroll_officer))
		self.assertFalse(self._open_todos(bank_account.name, self.assignee))
