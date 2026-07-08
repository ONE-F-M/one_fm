# Copyright (c) 2025, ONE FM and Contributors
# See license.txt

import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.operations.doctype.contract_compliance_checker.contract_compliance_checker import (
	_determine_issue_type,
	get_take_action_data,
)


class TestContractComplianceChecker(FrappeTestCase):
	def test_determine_issue_type(self):
		cases = {
			"No operations roles created with sale item X in project P": "operations_role",
			"More operations post created, expected: 2, created: 5 for roles ['A', 'B']": "operations_post",
			"No operations posts created with sale item X in project P": "operations_post",
			"Less employee schedules created from A to B, expected 10, created 3 for roles ['A']": "employee_schedule",
			"No post schedules created for Post (OPR-POST-001) from A to B": "post_schedule",
			"Everything looks fine": "",
		}
		for comment, expected in cases.items():
			self.assertEqual(_determine_issue_type(comment), expected)

	def test_get_take_action_data_no_comment(self):
		self.assertEqual(
			get_take_action_data(project="P", item="I", comment="", from_date="2026-01-01", to_date="2026-01-31"),
			{},
		)

	def test_get_take_action_data_operations_role(self):
		result = get_take_action_data(
			project="P",
			item="I",
			comment="No operations roles created with sale item I in project P",
			from_date="2026-01-01",
			to_date="2026-01-31",
		)
		self.assertEqual(result["path"], "/app/operations-role")
		self.assertEqual(result["params"], {"project": "P", "sale_item": "I"})

	def test_operations_post_uses_in_filter_with_all_roles(self):
		"""Operations Post routing must pass every active role as an "in" filter,
		not just the first role, and must not pin a single site_shift."""
		role_names = ["OPR-ROLE-001", "OPR-ROLE-002", "OPR-ROLE-003"]
		with patch.object(
			frappe.db, "get_value", return_value=frappe._dict(name="OPR-ROLE-001", shift="S", site="ST")
		), patch.object(frappe, "get_list", return_value=role_names) as mocked_get_list:
			result = get_take_action_data(
				project="P",
				item="I",
				comment="More operations post created, expected: 2, created: 5 for roles ['OPR-ROLE-001']",
				from_date="2026-01-01",
				to_date="2026-01-31",
			)

		self.assertEqual(result["path"], "/app/operations-post")
		# Value must be the canonical Frappe "in" filter the list view parses
		self.assertEqual(result["params"]["post_template"], json.dumps(["in", role_names]))
		self.assertEqual(result["params"]["project"], "P")
		# site_shift must be dropped so posts of roles on other shifts are not hidden
		self.assertNotIn("site_shift", result["params"])
		# roles must be re-queried for the exact sale item / project / active status
		mocked_get_list.assert_called_once()
		_, kwargs = mocked_get_list.call_args
		self.assertEqual(kwargs["filters"], {"project": "P", "sale_item": "I", "status": "Active"})
		self.assertEqual(kwargs["pluck"], "name")
