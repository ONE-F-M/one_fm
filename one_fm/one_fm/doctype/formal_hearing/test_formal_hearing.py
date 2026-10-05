# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestFormalHearing(FrappeTestCase):
	def test_assignment_rules_are_removed(self):
		from one_fm.patches.v15_0.remove_formal_hearing_assignment_rules import (
			ASSIGNMENT_RULES,
			execute,
		)

		execute()
		execute()
		for rule in ASSIGNMENT_RULES:
			self.assertFalse(frappe.db.exists("Assignment Rule", rule))
		self.assertFalse(
			frappe.db.exists("Process Task", {"erp_document": "Formal Hearing", "is_active": 1})
		)
