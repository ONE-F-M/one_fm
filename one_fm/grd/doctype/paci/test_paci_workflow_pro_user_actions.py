# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""In "Pending by GR Operator" the PRO User field decides which update actions show."""

import frappe
from frappe.model.workflow import is_transition_condition_satisfied
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.workflow.workflow import get_workflow_json_file
from one_fm.grd.doctype.paci.paci import PENDING_GR_OPERATOR
from one_fm.patches.v15_0 import paci_update_actions_follow_pro_user

DIRECT = ("Update Address", "Update Photo")
BY_PRO = ("Update Address By PRO", "Update Photo by PRO")


def _actions_shown(pro_user):
	doc = frappe.new_doc("PACI")
	doc.workflow_state = PENDING_GR_OPERATOR
	doc.pro_user = pro_user
	return {
		t["action"]
		for t in get_workflow_json_file("paci.json")["transitions"]
		if t["state"] == PENDING_GR_OPERATOR
		and t["action"] in DIRECT + BY_PRO
		and is_transition_condition_satisfied(frappe._dict(t), doc)
	}


class TestPACIUpdateActionsFollowProUser(FrappeTestCase):
	def test_blank_pro_user_shows_only_the_direct_updates(self):
		self.assertEqual(_actions_shown(None), set(DIRECT))

	def test_a_pro_user_shows_only_the_pro_updates(self):
		self.assertEqual(_actions_shown("Administrator"), set(BY_PRO))

	def test_the_patch_writes_the_conditions_to_the_live_workflow(self):
		paci_update_actions_follow_pro_user.execute()

	def test_the_patch_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.paci_update_actions_follow_pro_user", patches)
