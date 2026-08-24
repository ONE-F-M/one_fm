# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002145: the PRO User gate on "Assign PRO", and where the GR Operator side is routed."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.pcc_attestation.pcc_attestation import DRAFT, PRO_STATES

GRO_RULE = "PCC Attestation-GRO"
PRO_RULE = "PCC Attestation-PRO"

# A nationality per route out of Draft, so each case travels the transition the AC's routing
# table names rather than a state written past the workflow.
EMBASSY = "Nepali"
MOFA = "Indian"
TRANSLATION = "Ugandan"
NOTHING = "Egyptian"

NATIONALITY_FOR_STATE = {
	"Pending Embassy": EMBASSY,
	"Pending MOFA": MOFA,
	"Pending Translation": TRANSLATION,
}


def _an_active_employee():
	name = frappe.db.get_value("Employee", {"status": "Active"}, "name", order_by="creation asc")
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestPCCAssignPRO(FrappeTestCase):
	def setUp(self):
		for nationality in NATIONALITY_FOR_STATE.values():
			if not frappe.db.exists("Nationality", nationality):
				self.skipTest(f"Nationality {nationality} is not on this site")
		if not frappe.db.exists("Nationality", NOTHING):
			self.skipTest(f"Nationality {NOTHING} is not on this site")

		self.employee = _an_active_employee()

		settings = frappe.get_doc("HR Settings")
		settings.set("nationality_attestation_rules", [])
		settings.append("nationality_attestation_rules", {
			"nationality": EMBASSY,
			"embassy_required": 1, "embassy_fee_kwd": 16, "mofa_required": 1, "mofa_fee_kwd": 5,
			"translation_required": 0,
		})
		settings.append("nationality_attestation_rules", {
			"nationality": MOFA,
			"embassy_required": 0, "mofa_required": 1, "mofa_fee_kwd": 5, "translation_required": 0,
		})
		settings.append("nationality_attestation_rules", {
			"nationality": TRANSLATION,
			"embassy_required": 0, "mofa_required": 0, "translation_required": 1,
		})
		# Needs none of the three - the route that hands the record straight to the GR
		# Operator without a PRO in it.
		settings.append("nationality_attestation_rules", {
			"nationality": NOTHING,
			"embassy_required": 0, "mofa_required": 0, "translation_required": 0,
		})
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_cache(doctype="HR Settings")

	def _draft(self, nationality, **kwargs):
		frappe.db.set_value("Employee", self.employee, "one_fm_nationality", nationality)

		pcc = frappe.get_doc(
			{"doctype": "PCC Attestation", "employee": self.employee, "type": "Attestation", **kwargs}
		)
		pcc.flags.ignore_permissions = True
		pcc.insert()
		self.assertEqual(pcc.workflow_state, DRAFT)
		return pcc

	def _assign(self, pcc, next_state):
		pcc.workflow_state = next_state
		pcc.save(ignore_permissions=True)

	# ── The gate ──────────────────────────────────────────────────────────────────

	def test_assigning_without_a_pro_user_is_refused(self):
		for next_state, nationality in NATIONALITY_FOR_STATE.items():
			with self.subTest(next_state=next_state):
				pcc = self._draft(nationality)

				with self.assertRaises(frappe.ValidationError) as caught:
					self._assign(pcc, next_state)

				self.assertIn("PRO User", str(caught.exception))

	def test_assigning_with_a_pro_user_goes_through(self):
		for next_state, nationality in NATIONALITY_FOR_STATE.items():
			with self.subTest(next_state=next_state):
				pcc = self._draft(nationality, pro_user="Administrator")

				self._assign(pcc, next_state)

				self.assertEqual(pcc.workflow_state, next_state)

	def test_the_route_that_assigns_no_pro_is_not_gated(self):
		"""A nationality needing no embassy, no MOFA and no translation goes straight to the
		GR Operator - there is no PRO work to give anybody."""
		pcc = self._draft(NOTHING)

		self._assign(pcc, "Pending GR Operator")

		self.assertEqual(pcc.workflow_state, "Pending GR Operator")

	def test_a_later_state_change_is_not_gated(self):
		"""The gate is on leaving Draft, not on every save of a record with no PRO."""
		pcc = self._draft(MOFA)
		pcc.db_set("workflow_state", "Pending GR Operator")
		pcc.reload()

		pcc.workflow_state = "On Hold"
		pcc.save(ignore_permissions=True)

		self.assertEqual(pcc.workflow_state, "On Hold")

	# ── The routing table and the rules ───────────────────────────────────────────

	def test_assign_pro_routes_on_the_required_task(self):
		"""The AC's routing table, held by the workflow's conditions (WI-002029)."""
		workflow = frappe.get_doc("Workflow", "PCC Attestation")
		routes = {
			t.next_state: (t.allowed, t.condition or "")
			for t in workflow.transitions
			if t.state == DRAFT and t.action == "Assign PRO"
		}

		for next_state in PRO_STATES:
			with self.subTest(next_state=next_state):
				self.assertIn(next_state, routes)
				allowed, condition = routes[next_state]
				self.assertEqual(allowed, "Government Relations Operator")
				# Conditioned, or the engine takes whichever it matches first and every
				# record goes the same way.
				self.assertTrue(condition, f"{next_state} is reached unconditionally")

	def test_the_gro_rule_takes_its_assignee_from_a_process_task(self):
		rule = frappe.get_doc("Assignment Rule", GRO_RULE)

		self.assertFalse(rule.disabled)
		self.assertEqual(rule.rule, "Based on Process Task")
		self.assertTrue(rule.custom_routine_task, "the rule names no Process Task")

		task = frappe.get_doc("Process Task", rule.custom_routine_task)
		self.assertEqual(task.erp_document, "PCC Attestation")
		self.assertTrue(task.is_active)
		self.assertTrue(task.employee_user, "the Process Task names nobody to assign")

	def test_the_pro_rule_still_follows_the_record_s_own_pro(self):
		"""Which PRO holds a record is a property of that record, not of a Process Task."""
		rule = frappe.get_doc("Assignment Rule", PRO_RULE)

		self.assertEqual(rule.rule, "Based on Field")
		self.assertEqual(rule.field, "pro_user")
