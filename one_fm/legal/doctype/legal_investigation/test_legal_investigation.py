# Copyright (c) 2020, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.move_legal_investigation_lifecycle_to_processa import (
	execute,
	set_third_party_damage,
)

MODULE = "one_fm.legal.doctype.legal_investigation.legal_investigation"


def employee_with_user():
	return frappe.db.get_value("Employee", {"user_id": ["is", "set"], "status": "Active"}, ["name", "user_id"])


class TestLegalInvestigation(FrappeTestCase):
	def test_supervisor_of_an_hr_enquiry_is_notified(self):
		row = employee_with_user()
		if not row:
			self.skipTest("No active Employee with a user")
		employee, user = row
		enquiry = frappe.get_doc({"doctype": "HR Enquiry", "issuing_employee": employee}).insert(
			ignore_permissions=True
		)
		investigation = frappe.get_doc(
			{"doctype": "Legal Investigation", "reference_doctype": "HR Enquiry", "reference_docname": enquiry.name}
		)
		with patch(f"{MODULE}.sendemail") as sendemail:
			investigation.notify_supervisor()
		self.assertEqual(sendemail.call_args.args[0], [user])

	def test_no_supervisor_sends_nothing_and_does_not_fail(self):
		enquiry = frappe.get_doc({"doctype": "HR Enquiry"}).insert(ignore_permissions=True)
		for reference_doctype, reference_docname in (
			("HR Enquiry", enquiry.name),
			("PIFSS Monthly Deduction", "anything"),
			(None, None),
		):
			investigation = frappe.get_doc(
				{
					"doctype": "Legal Investigation",
					"reference_doctype": reference_doctype,
					"reference_docname": reference_docname,
				}
			)
			with patch(f"{MODULE}.sendemail") as sendemail:
				investigation.notify_supervisor()
			sendemail.assert_not_called()

	def test_the_controller_no_longer_issues_penalties(self):
		from one_fm.legal.doctype.legal_investigation.legal_investigation import LegalInvestigation

		for method in ("on_update", "issue_penalty", "create_penalty", "create_penalty_issuance"):
			self.assertFalse(hasattr(LegalInvestigation, method), msg=method)

	def test_legacy_damage_flags_become_third_party_damage(self):
		if not frappe.db.has_column("Legal Investigation", "asset_damage"):
			self.skipTest("Legacy damage columns are not on this site")
		flagged = frappe.get_doc({"doctype": "Legal Investigation"}).insert(ignore_permissions=True)
		clean = frappe.get_doc({"doctype": "Legal Investigation"}).insert(ignore_permissions=True)
		table = frappe.qb.DocType("Legal Investigation")
		frappe.qb.update(table).set(table.asset_damage, 1).where(table.name == flagged.name).run()

		set_third_party_damage("Legal Investigation")

		self.assertEqual(frappe.db.get_value("Legal Investigation", flagged.name, "third_party_damage"), 1)
		self.assertEqual(frappe.db.get_value("Legal Investigation", clean.name, "third_party_damage"), 0)

	def test_the_workflow_is_retired_and_penalty_applied_exists(self):
		execute()
		if frappe.db.exists("Workflow", "Legal Investigation"):
			self.assertEqual(frappe.db.get_value("Workflow", "Legal Investigation", "is_active"), 0)
		self.assertEqual(frappe.db.get_value("Workflow State", "Penalty Applied", "style"), "Danger")
