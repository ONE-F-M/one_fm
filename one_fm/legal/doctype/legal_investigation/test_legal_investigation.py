# Copyright (c) 2020, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.move_legal_investigation_lifecycle_to_processa import (
	execute,
	set_third_party_damage,
)

class TestLegalInvestigation(FrappeTestCase):
	def test_the_controller_no_longer_issues_penalties(self):
		from one_fm.legal.doctype.legal_investigation.legal_investigation import LegalInvestigation

		for method in (
			"after_insert",
			"on_update",
			"notify_supervisor",
			"validate_lead",
			"issue_penalty",
			"create_penalty",
			"create_penalty_issuance",
		):
			self.assertNotIn(method, vars(LegalInvestigation))

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
