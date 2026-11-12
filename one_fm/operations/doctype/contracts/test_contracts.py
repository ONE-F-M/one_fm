# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, add_days, nowdate, add_months
from unittest.mock import patch
from one_fm.operations.doctype.contracts.contracts import (
	send_contract_reminders,
	set_contract_inactive,
	set_contract_active,
	auto_deactivate_contracts,
	purge_future_schedules,
	rebuild_post_schedules,
	ContractDeactivationBlocked,
)
from one_fm.operations.doctype.employee_schedule.employee_schedule import has_workflow_state_column

class TestContracts(FrappeTestCase):
	"""Test Suite for Contracts DocType, focusing on contract reminders grouping logic."""

	def setUp(self):
		"""
		Preparation Phase:
		1. Set user to Administrator.
		2. Clean up data from previous test runs.
		3. Setup common master data (e.g. ONEFM General Setting).
		"""
		frappe.set_user("Administrator")

		# Clean up older test data
		frappe.db.delete("Contracts", {"name": ("like", "TEST-CONTRACT-%")})
		frappe.db.delete("Contracts", {"name": ("like", "TEST-CLIENT-%")})
		frappe.db.delete("Customer", {"name": ("like", "TEST-CLIENT-%")})
		frappe.db.delete("Project", {"name": ("like", "Test Project%")})

		# Create Test Customers and Projects
		for i in [1, 2]:
			if not frappe.db.exists("Customer", f"TEST-CLIENT-{i}"):
				frappe.get_doc({
					"doctype": "Customer",
					"customer_name": f"TEST-CLIENT-{i}",
					"customer_group": "Commercial",
					"territory": "All Territories"
				}).insert(ignore_permissions=True)

			project_name = "Test Project Alpha" if i == 1 else "Test Project Beta"
			if not frappe.db.exists("Project", project_name):
				frappe.get_doc({
					"doctype": "Project",
					"project_name": project_name
				}).insert(ignore_permissions=True)

		# Clear existing notify users if any to avoid test interference
		settings = frappe.get_doc("ONEFM General Setting")
		settings.set("notify_contract_expiry_users", [])

		# Create test users if they don't exist
		for email in ["test_notify1@example.com", "test_notify2@example.com"]:
			if not frappe.db.exists("User", email):
				user = frappe.get_doc({
					"doctype": "User",
					"email": email,
					"first_name": "Test Notify",
					"send_welcome_email": 0
				}).insert(ignore_permissions=True)

			settings.append("notify_contract_expiry_users", {"user": email})

		settings.save(ignore_permissions=True)

	def tearDown(self):
		"""
		Reset Phase:
		1. Clean up transactional records.
		2. Restore common master data to default.
		"""
		frappe.db.delete("Contracts", {"name": ("like", "TEST-CONTRACT-%")})
		frappe.db.delete("Contracts", {"name": ("like", "TEST-CLIENT-%")})
		frappe.db.delete("Customer", {"name": ("like", "TEST-CLIENT-%")})
		frappe.db.delete("Project", {"name": ("like", "Test Project%")})

		frappe.db.sql("""
			DELETE FROM `tabAction User`
			WHERE parent = 'ONEFM General Setting' AND user IN ('test_notify1@example.com', 'test_notify2@example.com')
		""")

		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _make_active_contract(self, suffix="1"):
		"""Helper: create a contract and set it directly to Active state."""
		client = f"TEST-CLIENT-{suffix}"
		project = "Test Project Alpha" if suffix == "1" else "Test Project Beta"
		contract = frappe.get_doc({
			"doctype": "Contracts",
			"client": client,
			"project": project,
			"start_date": add_days(nowdate(), -60),
			"end_date": add_months(getdate(), 6),
			"workflow_state": "Draft",
		}).insert(ignore_permissions=True)
		contract.db_set("workflow_state", "Active")
		frappe.db.commit()
		return contract

	# ------------------------------------------------------------------
	# Test: send_contract_reminders — one separate email per expiring contract
	# ------------------------------------------------------------------
	@patch('one_fm.operations.doctype.contracts.contracts.sendemail')
	def test_send_contract_reminders_separate_email_per_contract(self, mock_sendemail):
		"""
		Verifies that multiple contracts sharing the same internal notification date
		each generate a separate, individual email (NOT grouped into a single email),
		sent to the configurable Action Users in ONEFM General Setting.
		"""

		contract1 = frappe.get_doc({
			"doctype": "Contracts",
			"contract": "TEST-CONTRACT-001",
			"client": "TEST-CLIENT-1",
			"project": "Test Project Alpha",
			"start_date": add_days(nowdate(), -60),
			"end_date": add_months(getdate(), 4),  # 3 (decision period) + 1 (notification) = 4 months
			"contract_end_internal_notification": 1,
			"contract_termination_decision_period": 3,
			"workflow_state": "Draft"
		}).insert(ignore_permissions=True)
		contract1.db_set("workflow_state", "Active")

		contract2 = frappe.get_doc({
			"doctype": "Contracts",
			"contract": "TEST-CONTRACT-002",
			"client": "TEST-CLIENT-2",
			"project": "Test Project Beta",
			"start_date": add_days(nowdate(), -120),
			"end_date": add_months(getdate(), 3),  # 1 (decision period) + 2 (notification) = 3 months
			"contract_end_internal_notification": 2,
			"contract_termination_decision_period": 1,
			"workflow_state": "Draft"
		}).insert(ignore_permissions=True)
		contract2.db_set("workflow_state", "Active")

		# Commit to ensure contracts are saved to database before the send_contract_reminders query
		frappe.db.commit()

		# Action: Trigger the scheduled event
		send_contract_reminders(is_scheduled_event=False)

		# Verify: one separate email per expiring contract (NOT grouped)
		self.assertEqual(
			mock_sendemail.call_count, 2,
			"sendemail should be called once per expiring contract — no grouping."
		)

		# Index each call by the emailed contract name (appended to the subject)
		calls_by_contract = {}
		for call in mock_sendemail.call_args_list:
			kwargs = call[1]
			subject = kwargs.get("subject", "")
			# Subject keeps the current structure, with the contract id appended
			self.assertTrue(
				subject.startswith("Contract Internal Notification Period for Expiring Contracts"),
				"Subject must keep the current structure."
			)
			if contract1.name in subject:
				calls_by_contract["contract1"] = kwargs
			elif contract2.name in subject:
				calls_by_contract["contract2"] = kwargs

		self.assertIn("contract1", calls_by_contract, "Missing individual email for contract 1.")
		self.assertIn("contract2", calls_by_contract, "Missing individual email for contract 2.")

		action_users = {"test_notify1@example.com", "test_notify2@example.com"}
		for key, contract in (("contract1", contract1), ("contract2", contract2)):
			kwargs = calls_by_contract[key]

			# One action user is the primary recipient; the remaining users go to CC.
			# The production code derives users via set(), so which one is primary is
			# not deterministic — assert on membership rather than a fixed order.
			recipients = kwargs.get("recipients", [])
			self.assertEqual(len(recipients), 1, "Each email must have a single primary recipient.")
			recipient = recipients[0]
			self.assertIn(recipient, action_users, "Primary recipient must be a configured action user.")

			cc = kwargs.get("cc", [])
			# The other action user (not the primary recipient) must be CC'd
			self.assertIn(
				(action_users - {recipient}).pop(), cc,
				"The remaining action user must be in CC."
			)
			# Finance and Legal group mailboxes must always be CC'd (User Story)
			self.assertIn("finance@one-fm.com", cc, "Finance must be CC'd on contract reminders.")
			self.assertIn("legal@one-fm.com", cc, "Legal must be CC'd on contract reminders.")

			# The subject must carry this contract's id for individual tracking
			self.assertIn(contract.name, kwargs.get("subject", ""))

		# Each email must contain only its own contract's data — not the other's
		self.assertIn("TEST-CLIENT-1", calls_by_contract["contract1"].get("content", ""))
		self.assertNotIn("TEST-CLIENT-2", calls_by_contract["contract1"].get("content", ""))
		self.assertIn("TEST-CLIENT-2", calls_by_contract["contract2"].get("content", ""))
		self.assertNotIn("TEST-CLIENT-1", calls_by_contract["contract2"].get("content", ""))

	# ------------------------------------------------------------------
	# Test: set_contract_inactive — immediate path
	# ------------------------------------------------------------------
	@patch('one_fm.operations.doctype.contracts.contracts.sendemail')
	def test_set_contract_inactive_immediate(self, mock_sendemail):
		"""
		When end_date <= today, set_contract_inactive must immediately
		transition the contract to Inactive and trigger the inactivation email.
		"""
		contract = self._make_active_contract("1")
		contract.append("notification_members", {"user": "test_notify1@example.com"})
		contract.flags.ignore_validate = True
		contract.flags.ignore_workflow = True
		contract.save(ignore_permissions=True)
		frappe.db.commit()

		# Call with an end date that is today (immediate transition)
		set_contract_inactive(contract.name, nowdate())

		# Reload and verify state
		contract.reload()
		self.assertEqual(contract.workflow_state, "Inactive")
		self.assertEqual(str(contract.end_date), nowdate())
		self.assertEqual(contract.is_auto_renewal, 0)

		# Verify inactivation email was triggered (called from on_update)
		self.assertTrue(
			mock_sendemail.called,
			"Inactivation email must be sent on immediate transition."
		)

	# ------------------------------------------------------------------
	# Test: set_contract_inactive — deferred path
	# ------------------------------------------------------------------
	@patch('one_fm.operations.doctype.contracts.contracts.sendemail')
	def test_set_contract_inactive_deferred(self, mock_sendemail):
		"""
		When end_date is in the future, the contract must stay Active.
		No inactivation email should be sent yet.
		"""
		contract = self._make_active_contract("1")
		future_date = add_days(nowdate(), 30)

		set_contract_inactive(contract.name, future_date)

		# Reload and verify — should still be Active
		contract.reload()
		self.assertEqual(contract.workflow_state, "Active")
		self.assertEqual(str(contract.end_date), future_date)
		self.assertEqual(contract.is_auto_renewal, 0)

		# No inactivation email should be sent for deferred path
		self.assertFalse(
			mock_sendemail.called,
			"Inactivation email must NOT be sent for deferred transition."
		)

	# ------------------------------------------------------------------
	# Test: auto_deactivate_contracts
	# ------------------------------------------------------------------
	@patch('one_fm.operations.doctype.contracts.contracts.sendemail')
	def test_auto_deactivate_contracts(self, mock_sendemail):
		"""
		Contracts with end_date in the past and workflow_state='Active'
		must be automatically transitioned to Inactive by the scheduler.
		"""
		contract = self._make_active_contract("1")
		contract.append("notification_members", {"user": "test_notify1@example.com"})
		contract.flags.ignore_validate = True
		contract.flags.ignore_workflow = True
		contract.save(ignore_permissions=True)

		# Set end_date to yesterday so it qualifies for auto-deactivation
		yesterday = add_days(nowdate(), -1)
		frappe.db.set_value("Contracts", contract.name, "end_date", yesterday)
		frappe.db.commit()

		auto_deactivate_contracts()

		contract.reload()
		self.assertEqual(
			contract.workflow_state, "Inactive",
			"Expired Active contracts must be auto-deactivated."
		)

		# Verify inactivation email was triggered
		self.assertTrue(
			mock_sendemail.called,
			"Inactivation email must be sent when auto-deactivating."
		)

	# ------------------------------------------------------------------
	# Test: send_inactivation_email — recipient selection & rendering
	# ------------------------------------------------------------------
	@patch('one_fm.operations.doctype.contracts.contracts.sendemail')
	def test_send_inactivation_email_recipients_and_content(self, mock_sendemail):
		"""
		send_inactivation_email must:
		1. Fetch recipients from notification_members child table.
		2. Exclude Administrator.
		3. Render the template with contract_id, client_name, end_date.
		"""
		contract = self._make_active_contract("1")
		contract.append("notification_members", {"user": "test_notify1@example.com"})
		contract.append("notification_members", {"user": "test_notify2@example.com"})
		contract.flags.ignore_validate = True
		contract.flags.ignore_workflow = True
		contract.save(ignore_permissions=True)
		frappe.db.commit()

		# Directly call the email method
		contract.send_inactivation_email()

		self.assertTrue(mock_sendemail.called, "sendemail must be called.")

		call_kwargs = mock_sendemail.call_args[1]

		# Check recipients
		recipients = call_kwargs.get("recipients", [])
		self.assertIn("test_notify1@example.com", recipients)
		self.assertIn("test_notify2@example.com", recipients)
		self.assertNotIn("Administrator", recipients)

		# Check subject contains contract name
		subject = call_kwargs.get("subject", "")
		self.assertIn(contract.name, subject)

		# Check content contains the required dynamic variables
		content = call_kwargs.get("content", "")
		self.assertIn(contract.name, content, "Contract ID must be in email body.")
		self.assertIn("TEST-CLIENT-1", content, "Client name must be in email body.")

	# ------------------------------------------------------------------
	# Test: send_inactivation_email — no members configured
	# ------------------------------------------------------------------
	@patch('one_fm.operations.doctype.contracts.contracts.sendemail')
	def test_send_inactivation_email_no_members_logs_warning(self, mock_sendemail):
		"""
		If no notification members are configured, send_inactivation_email
		must log a warning and not call sendemail.
		"""
		contract = self._make_active_contract("1")
		# No notification_members added

		contract.send_inactivation_email()

		self.assertFalse(
			mock_sendemail.called,
			"sendemail must NOT be called when no notification members are configured."
		)

	# ------------------------------------------------------------------
	# Test: send_inactivation_email — error does not block save
	# ------------------------------------------------------------------
	@patch('one_fm.operations.doctype.contracts.contracts.sendemail', side_effect=Exception("SMTP Error"))
	def test_inactivation_email_error_does_not_block_save(self, mock_sendemail):
		"""
		If sendemail raises an exception during on_update, the contract
		must still be saved successfully (error is logged, not raised).
		"""
		contract = self._make_active_contract("1")
		contract.append("notification_members", {"user": "test_notify1@example.com"})
		contract.flags.ignore_validate = True
		contract.flags.ignore_workflow = True
		contract.save(ignore_permissions=True)
		frappe.db.commit()

		# Simulate the Set Inactive transition — should not raise
		set_contract_inactive(contract.name, nowdate())

		# Contract must still be Inactive despite email failure
		contract.reload()
		self.assertEqual(
			contract.workflow_state, "Inactive",
			"Contract must transition to Inactive even if email sending fails."
		)


CASCADE_PROJECT = "Test Cascade Project"
CASCADE_CLIENT = "TEST-CLIENT-CASCADE"
CASCADE_USER = "test_cascade_notify@example.com"
JOB_KWARGS = ("queue", "timeout", "enqueue_after_commit", "job_id", "deduplicate", "is_async", "now")


def run_job_inline(method, **kwargs):
	method = frappe.get_attr(method) if isinstance(method, str) else method
	return method(**{k: v for k, v in kwargs.items() if k not in JOB_KWARGS})


@patch("frappe.enqueue", side_effect=run_job_inline)
@patch("one_fm.operations.doctype.contracts.contracts.sendemail")
class TestContractDeactivationCascade(FrappeTestCase):
	"""Inactivation guard, cascade, schedule purge and reactivation. The code under test
	commits, so fixtures are inserted raw and removed with a commit in tearDown."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.cleanup()
		if not frappe.db.exists("Customer", CASCADE_CLIENT):
			frappe.get_doc({
				"doctype": "Customer", "customer_name": CASCADE_CLIENT,
				"customer_group": "Commercial", "territory": "All Territories",
			}).insert(ignore_permissions=True)
		if not frappe.db.exists("User", CASCADE_USER):
			frappe.get_doc({
				"doctype": "User", "email": CASCADE_USER, "first_name": "Cascade", "send_welcome_email": 0,
			}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Project", "project_name": CASCADE_PROJECT}).insert(ignore_permissions=True)

		frappe.get_doc({
			"doctype": "Action User", "user": CASCADE_USER, "parent": "Operation Settings",
			"parenttype": "Operation Settings", "parentfield": "contract_inactivation_recipients",
		}).db_insert()

		self.insert("Operations Site", "TCASC Site", status="Active")
		self.insert("Operations Site", "TCASC Site Off", status="Inactive")
		self.insert("Operations Shift", "TCASC Shift", site="TCASC Site", status="Active")
		self.insert("Operations Role", "TCASC Role", shift="TCASC Shift", site="TCASC Site", post_abbrv="TC", status="Active")
		self.insert(
			"Operations Post", "TCASC Post", post_name="TCASC Post", post_template="TCASC Role",
			site_shift="TCASC Shift", site="TCASC Site", status="Active",
			start_date=add_days(nowdate(), -60), end_date=add_days(nowdate(), -30),
		)

		self.contract = frappe.get_doc({
			"doctype": "Contracts",
			"client": CASCADE_CLIENT,
			"project": CASCADE_PROJECT,
			"start_date": add_days(nowdate(), -60),
			"end_date": add_days(nowdate(), 10),
			"workflow_state": "Draft",
		}).insert(ignore_permissions=True)
		self.contract.db_set("workflow_state", "Active")
		self.contract.reload()

	def tearDown(self):
		self.cleanup()
		frappe.db.commit()

	def cleanup(self):
		frappe.db.rollback()
		for doctype in ("Employee Schedule", "Post Schedule", "Operations Post", "Operations Role", "Operations Shift", "Operations Site", "Task"):
			frappe.db.delete(doctype, {"project": CASCADE_PROJECT})
		for doctype in ("Employee Schedule", "Post Schedule", "Employee"):
			frappe.db.delete(doctype, {"name": ("like", "TCASC-%")})
		frappe.db.delete("ToDo", {"reference_type": "Employee Schedule", "reference_name": ("like", "TCASC-%")})
		frappe.db.delete("Contract Deactivated Record", {"parent": ("like", f"{CASCADE_CLIENT}-%")})
		frappe.db.delete("Contracts", {"client": CASCADE_CLIENT})
		frappe.db.delete("Project", {"name": CASCADE_PROJECT})
		frappe.db.delete("Action User", {"parent": "Operation Settings", "parentfield": "contract_inactivation_recipients"})
		frappe.db.commit()

	def insert(self, doctype, name, **fields):
		doc = frappe.get_doc({"doctype": doctype, "name": name, "project": CASCADE_PROJECT, **fields})
		doc.db_insert()
		return doc

	def set_state(self, state):
		self.contract.reload()
		self.contract.workflow_state = state
		self.contract.flags.ignore_validate = True
		self.contract.flags.ignore_workflow = True
		self.contract.save(ignore_permissions=True)

	def status(self, doctype, name):
		return frappe.db.get_value(doctype, name, "status")

	def test_guard_blocks_active_employee_on_site_then_passes(self, mock_sendemail, mock_enqueue):
		self.insert("Employee", "TCASC-EMP-1", employee_name="Cascade Guard", status="Active", site="TCASC Site")
		frappe.db.commit()
		with self.assertRaises(ContractDeactivationBlocked) as ctx:
			self.set_state("Inactive")
		self.assertIn("1 Active employee", str(ctx.exception))
		self.assertIn("TCASC-EMP-1", str(ctx.exception))

		frappe.db.rollback()
		frappe.db.set_value("Employee", "TCASC-EMP-1", "site", None)
		self.set_state("Inactive")
		self.assertEqual(self.status("Operations Site", "TCASC Site"), "Inactive")

	def test_guard_blocks_active_employee_on_shift(self, mock_sendemail, mock_enqueue):
		self.insert("Employee", "TCASC-EMP-2", employee_name="Cascade Shift", status="Active", shift="TCASC Shift")
		with self.assertRaises(ContractDeactivationBlocked):
			self.set_state("Inactive")

	def test_guard_blocks_shared_project(self, mock_sendemail, mock_enqueue):
		other = frappe.get_doc({
			"doctype": "Contracts", "client": CASCADE_CLIENT, "project": CASCADE_PROJECT,
			"start_date": add_days(nowdate(), -5), "end_date": add_days(nowdate(), 30), "workflow_state": "Draft",
		}).insert(ignore_permissions=True)
		other.db_set("workflow_state", "Active")
		with self.assertRaises(ContractDeactivationBlocked) as ctx:
			self.set_state("Inactive")
		self.assertIn(other.name, str(ctx.exception))

	def test_inactivation_flips_records_and_emails(self, mock_sendemail, mock_enqueue):
		self.set_state("Inactive")

		project = frappe.db.get_value("Project", CASCADE_PROJECT, ["status", "percent_complete_method"], as_dict=True)
		self.assertEqual(project.status, "Completed")
		self.assertEqual(project.percent_complete_method, "Manual")
		for doctype, name in (
			("Operations Site", "TCASC Site"), ("Operations Shift", "TCASC Shift"),
			("Operations Role", "TCASC Role"), ("Operations Post", "TCASC Post"),
		):
			self.assertEqual(self.status(doctype, name), "Inactive", doctype)

		recorded = {d.reference_name for d in frappe.get_doc("Contracts", self.contract.name).deactivated_records}
		self.assertEqual(recorded, {CASCADE_PROJECT, "TCASC Site", "TCASC Shift", "TCASC Role", "TCASC Post"})

		frappe.get_doc({"doctype": "Task", "subject": "TCASC task", "project": CASCADE_PROJECT}).insert(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Project", CASCADE_PROJECT, "status"), "Completed")

		mock_sendemail.assert_called_once()
		self.assertIn(CASCADE_USER, mock_sendemail.call_args.kwargs["recipients"])
		self.assertIn("TCASC Post", mock_sendemail.call_args.kwargs["content"])

	def test_purge_keeps_today_and_past(self, mock_sendemail, mock_enqueue):
		dates = {"past": add_days(nowdate(), -1), "today": nowdate(), "tomorrow": add_days(nowdate(), 1)}
		for key, date in dates.items():
			self.insert("Employee Schedule", f"TCASC-ES-{key}", employee="TCASC-EMP-X", shift="TCASC Shift", date=date)
			self.insert("Post Schedule", f"TCASC-PS-{key}", post="TCASC Post", date=date)
		# Shift match alone (different project on the row) is still purged.
		frappe.get_doc({
			"doctype": "Employee Schedule", "name": "TCASC-ES-shift", "shift": "TCASC Shift", "date": dates["tomorrow"],
		}).db_insert()

		purge_future_schedules(self.contract.name)

		self.assertTrue(frappe.db.exists("Employee Schedule", "TCASC-ES-past"))
		self.assertTrue(frappe.db.exists("Employee Schedule", "TCASC-ES-today"))
		self.assertFalse(frappe.db.exists("Employee Schedule", "TCASC-ES-tomorrow"))
		self.assertFalse(frappe.db.exists("Employee Schedule", "TCASC-ES-shift"))
		self.assertTrue(frappe.db.exists("Post Schedule", "TCASC-PS-today"))
		self.assertFalse(frappe.db.exists("Post Schedule", "TCASC-PS-tomorrow"))

	def test_purge_closes_pending_approvals(self, mock_sendemail, mock_enqueue):
		if not has_workflow_state_column():
			self.skipTest("Employee Schedule workflow is not installed")
		for state in ("Pending DSOT Approval", "Pending Suspension"):
			name = f"TCASC-ES-{state[8:12]}"
			self.insert("Employee Schedule", name, shift="TCASC Shift", date=add_days(nowdate(), 2), workflow_state=state)
			frappe.get_doc({
				"doctype": "ToDo", "allocated_to": "Administrator", "description": "TCASC approval",
				"reference_type": "Employee Schedule", "reference_name": name, "status": "Open",
			}).insert(ignore_permissions=True)

		purge_future_schedules(self.contract.name)

		self.assertFalse(frappe.db.exists("ToDo", {
			"reference_type": "Employee Schedule", "reference_name": ("like", "TCASC-%"), "status": "Open",
		}))
		self.assertFalse(frappe.db.exists("Employee Schedule", {"name": ("like", "TCASC-ES-%")}))

	def test_reactivation_restores_only_recorded(self, mock_sendemail, mock_enqueue):
		self.set_state("Inactive")
		self.set_state("Active")

		project = frappe.db.get_value("Project", CASCADE_PROJECT, ["status", "percent_complete_method"], as_dict=True)
		self.assertEqual(project.status, "Open")
		self.assertEqual(project.percent_complete_method, "Task Completion")
		for doctype, name in (
			("Operations Site", "TCASC Site"), ("Operations Shift", "TCASC Shift"),
			("Operations Role", "TCASC Role"), ("Operations Post", "TCASC Post"),
		):
			self.assertEqual(self.status(doctype, name), "Active", doctype)
		self.assertEqual(self.status("Operations Site", "TCASC Site Off"), "Inactive")
		self.assertTrue(all(d.restored_on for d in frappe.get_doc("Contracts", self.contract.name).deactivated_records))

		# The post's end date had expired; it is reset to the contract window and scheduled.
		self.assertEqual(str(frappe.db.get_value("Operations Post", "TCASC Post", "end_date")), str(self.contract.end_date))
		count = frappe.db.count("Post Schedule", {"post": "TCASC Post"})
		self.assertEqual(count, 11)

		rebuild_post_schedules(["TCASC Post"])
		self.assertEqual(frappe.db.count("Post Schedule", {"post": "TCASC Post"}), count)

	def test_auto_deactivate_runs_cascade(self, mock_sendemail, mock_enqueue):
		self.contract.db_set("end_date", add_days(nowdate(), -1))
		self.run_auto_deactivate()
		self.assertEqual(frappe.db.get_value("Contracts", self.contract.name, "workflow_state"), "Inactive")
		self.assertEqual(self.status("Operations Post", "TCASC Post"), "Inactive")

	def test_auto_deactivate_blocked_stays_active_and_emails(self, mock_sendemail, mock_enqueue):
		self.insert("Employee", "TCASC-EMP-3", employee_name="Cascade Auto", status="Active", site="TCASC Site")
		self.contract.db_set("end_date", add_days(nowdate(), -1))
		frappe.db.commit()

		self.run_auto_deactivate()

		self.assertEqual(frappe.db.get_value("Contracts", self.contract.name, "workflow_state"), "Active")
		self.assertEqual(self.status("Operations Site", "TCASC Site"), "Active")
		mock_sendemail.assert_called_once()
		self.assertEqual(mock_sendemail.call_args.kwargs["recipients"], [CASCADE_USER])
		self.assertIn("TCASC-EMP-3", mock_sendemail.call_args.kwargs["content"])

	def run_auto_deactivate(self):
		"""Limit the daily job to this test's contract so other site data is never touched."""
		get_all = frappe.get_all

		def only_this_contract(doctype, *args, **kwargs):
			if doctype == "Contracts" and kwargs.get("pluck") == "name":
				kwargs["filters"] = {**kwargs["filters"], "name": self.contract.name}
			return get_all(doctype, *args, **kwargs)

		with patch("frappe.get_all", side_effect=only_this_contract):
			auto_deactivate_contracts()
