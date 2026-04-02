# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, add_days, nowdate, add_months
from unittest.mock import patch
from one_fm.operations.doctype.contracts.contracts import send_contract_reminders

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
		frappe.db.delete("Customer", {"name": ("like", "TEST-CLIENT-%")})
		frappe.db.delete("Project", {"name": ("like", "Test Project%")})

		frappe.db.sql("""
			DELETE FROM `tabAction User`
			WHERE parent = 'ONEFM General Setting' AND user IN ('test_notify1@example.com', 'test_notify2@example.com')
		""")

		frappe.set_user("Administrator")
		frappe.db.rollback()


	@patch('one_fm.operations.doctype.contracts.contracts.sendemail')
	def test_send_contract_reminders_grouped_email_delivery(self, mock_sendemail):
		"""
		Verifies that multiple contracts expiring today generate a single grouped email
		sent to the configurable 'notify_contract_expiry_users' Action Users in ONEFM General Setting.
		"""

		# Setup two test contracts that match the internal notification logic
		# The update_contract_dates() method calculates:
		# 1. contract_termination_decision_period_date = add_months(end_date, -contract_termination_decision_period)
		# 2. contract_end_internal_notification_date = add_months(contract_termination_decision_period_date, -contract_end_internal_notification)

		# So to get contract_end_internal_notification_date = today:
		# end_date = add_months(today, contract_termination_decision_period + contract_end_internal_notification)

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

		# Verify: Determine if sendemail patch was called exactly ONCE
		self.assertEqual(
			mock_sendemail.call_count, 1,
			"sendemail should only be called once, grouping all contracts into a single email."
		)

		call_kwargs = mock_sendemail.call_args[1]

		# Verify Recipients mapping
		self.assertIn(
			"test_notify1@example.com", call_kwargs.get("recipients", []),
			"Recipients from ONEFM General Setting action users must be included."
		)
		self.assertIn(
			"test_notify2@example.com", call_kwargs.get("recipients", []),
			"Recipients from ONEFM General Setting action users must be included."
		)

		# Verify Content Grouping (Should include both clients from the contracts)
		email_content = call_kwargs.get("content", "")
		self.assertIn("TEST-CLIENT-1", email_content, "First contract data missing from grouped email")
		self.assertIn("TEST-CLIENT-2", email_content, "Second contract data missing from grouped email")
		self.assertEqual(call_kwargs.get("subject"), "Contract Internal Notification Period for Expiring Contracts")
