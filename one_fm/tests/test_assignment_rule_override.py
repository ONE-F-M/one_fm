# Copyright (c) 2026, ONE FM and contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides import assignment_rule


def make_rule():
	rule = MagicMock()
	rule.name = "Test Rule"
	rule.is_assignment_rule_with_workflow = False
	rule.description = "Please check"
	rule.due_date_based_on = None
	rule.get_user.return_value = "Administrator"
	return rule


class TestDoAssignmentAcrossFrappeBuilds(FrappeTestCase):
	doc = frappe._dict(doctype="ToDo", name="does-not-matter")

	def test_newer_build_uses_add_underscore_with_ignore_permissions(self):
		# Newer v15: add() takes args only, _add() carries ignore_permissions.
		module = MagicMock(spec=["add", "_add", "set_status"])
		module.add.side_effect = lambda args=None: self.fail("add() has no ignore_permissions here")

		with patch.object(assignment_rule, "assign_to", module):
			self.assertTrue(assignment_rule.do_assignment(make_rule(), self.doc))

		self.assertTrue(module._add.call_args.kwargs["ignore_permissions"])

	def test_older_build_falls_back_to_add(self):
		module = MagicMock(spec=["add", "set_status"])

		with patch.object(assignment_rule, "assign_to", module):
			self.assertTrue(assignment_rule.do_assignment(make_rule(), self.doc))

		self.assertTrue(module.add.call_args.kwargs["ignore_permissions"])
