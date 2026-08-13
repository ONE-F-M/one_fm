# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002029: the PCC Attestation workflow, its routing and its receipt guards."""

import frappe
from frappe.tests.utils import FrappeTestCase

A_RECEIPT = "/files/receipt.pdf"
# From the reporter's master data (WI-002025).
EMBASSY_AND_MOFA = "Nepali"
MOFA_ONLY = "Indian"
NEITHER = "Ugandan"
WORKFLOW = "PCC Attestation"
GRO = "Government Relations Operator"
PRO = "PRO"


def _an_active_employee():
	name = frappe.db.get_value("Employee", {"status": "Active"}, "name", order_by="creation asc")
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestPCCAttestationWorkflow(FrappeTestCase):
	def setUp(self):
		for nationality in (EMBASSY_AND_MOFA, MOFA_ONLY, NEITHER):
			if not frappe.db.exists("Nationality", nationality):
				self.skipTest(f"Nationality {nationality} is not on this site")
		if not frappe.db.exists("Workflow", WORKFLOW):
			self.skipTest("The PCC Attestation workflow is not installed on this site")

		self.employee = _an_active_employee()
		settings = frappe.get_doc("HR Settings")
		settings.set("nationality_attestation_rules", [])
		settings.append(
			"nationality_attestation_rules",
			{"nationality": EMBASSY_AND_MOFA, "embassy_required": 1, "embassy_fee_kwd": 16.0,
			 "mofa_required": 1, "mofa_fee_kwd": 5.0, "translation_required": 0},
		)
		settings.append(
			"nationality_attestation_rules",
			{"nationality": MOFA_ONLY, "embassy_required": 0,
			 "mofa_required": 1, "mofa_fee_kwd": 5.0, "translation_required": 0},
		)
		settings.append(
			"nationality_attestation_rules",
			{"nationality": NEITHER, "embassy_required": 0, "mofa_required": 0,
			 "translation_required": 1},
		)
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_cache(doctype="HR Settings")

		self.workflow = frappe.get_doc("Workflow", WORKFLOW)

	def _pcc(self, nationality, **kwargs):
		frappe.db.set_value("Employee", self.employee, "one_fm_nationality", nationality)
		pcc = frappe.get_doc(
			{"doctype": "PCC Attestation", "employee": self.employee, "type": "Attestation", **kwargs}
		)
		pcc.flags.ignore_permissions = True
		pcc.insert()
		return pcc

	def _transition(self, from_state, action, next_state):
		matches = [
			t
			for t in self.workflow.transitions
			if (t.state, t.action, t.next_state) == (from_state, action, next_state)
		]
		self.assertEqual(len(matches), 1, f"{from_state} --{action}--> {next_state} is not a single transition")
		return matches[0]

	# ------------------------------------------------------------------ routing

	def test_the_workflow_is_active_on_the_right_doctype(self):
		self.assertEqual(self.workflow.document_type, "PCC Attestation")
		self.assertTrue(self.workflow.is_active)
		self.assertEqual(self.workflow.workflow_state_field, "workflow_state")

	def test_every_assign_pro_transition_carries_a_condition(self):
		# Four transitions share the action name and differ only in where they lead. Without a
		# condition on each, the engine takes whichever it matches first and routes every
		# record the same way. The fourth exists because the reporter's master data has a
		# nationality needing neither embassy nor MOFA (WI-002025).
		assign_pro = [t for t in self.workflow.transitions if t.action == "Assign PRO"]
		self.assertEqual(len(assign_pro), 4)
		for transition in assign_pro:
			self.assertTrue(
				transition.condition,
				f"Assign PRO -> {transition.next_state} has no condition",
			)

	def test_the_assign_pro_conditions_are_mutually_exclusive(self):
		# Exactly one branch may match any given record, or the routing is still a coin toss.
		# Every combination of the three requirement flags is covered, including the ones the
		# reporter's data actually contains: embassy+MOFA (Nepali), MOFA only (Indian), and
		# neither-but-translation (Ugandan).
		cases = (
			("Attestation", 1, 1, 0, "Pending Embassy"),
			("Attestation", 1, 0, 0, "Pending Embassy"),
			("Attestation", 1, 1, 1, "Pending Embassy"),
			("Attestation", 0, 1, 0, "Pending MOFA"),
			("Attestation", 0, 1, 1, "Pending MOFA"),
			("Attestation", 0, 0, 1, "Pending Translation"),
			("Attestation", 0, 0, 0, "Pending GR Operator"),
			("Translation", 1, 1, 1, "Pending Translation"),
			("Translation", 0, 0, 0, "Pending Translation"),
		)
		for doc_type, embassy, mofa, translation, expected in cases:
			doc = frappe._dict(
				type=doc_type,
				embassy_attestation_required=embassy,
				mofa_attestation_required=mofa,
				translation_required=translation,
			)
			matched = [
				t.next_state
				for t in self.workflow.transitions
				if t.action == "Assign PRO"
				and frappe.safe_eval(t.condition, None, {"doc": doc})
			]
			self.assertEqual(
				matched,
				[expected],
				f"type={doc_type} embassy={embassy} mofa={mofa} translation={translation} "
				f"matched {matched}",
			)

	def test_a_nationality_needing_the_embassy_routes_through_it(self):
		pcc = self._pcc(EMBASSY_AND_MOFA)
		self.assertTrue(pcc.embassy_attestation_required)

		transition = self._transition("Draft", "Assign PRO", "Pending Embassy")
		self.assertTrue(frappe.safe_eval(transition.condition, None, {"doc": pcc.as_dict()}))

	def test_a_mofa_only_nationality_skips_straight_to_mofa(self):
		pcc = self._pcc(MOFA_ONLY)
		self.assertFalse(pcc.embassy_attestation_required)

		to_mofa = self._transition("Draft", "Assign PRO", "Pending MOFA")
		to_embassy = self._transition("Draft", "Assign PRO", "Pending Embassy")
		self.assertTrue(frappe.safe_eval(to_mofa.condition, None, {"doc": pcc.as_dict()}))
		self.assertFalse(frappe.safe_eval(to_embassy.condition, None, {"doc": pcc.as_dict()}))

	def test_translation_routes_to_pending_translation(self):
		pcc = self._pcc(EMBASSY_AND_MOFA, type="Translation")

		transition = self._transition("Draft", "Assign PRO", "Pending Translation")
		self.assertTrue(frappe.safe_eval(transition.condition, None, {"doc": pcc.as_dict()}))
		# Even though the candidate's nationality needs the embassy, translation work never goes there.
		to_embassy = self._transition("Draft", "Assign PRO", "Pending Embassy")
		self.assertFalse(frappe.safe_eval(to_embassy.condition, None, {"doc": pcc.as_dict()}))

	def test_a_zero_fee_embassy_still_routes_through_the_embassy(self):
		# The reason routing reads the flag and not the fee.
		settings = frappe.get_doc("HR Settings")
		settings.set("nationality_attestation_rules", [])
		settings.append(
			"nationality_attestation_rules",
			{"nationality": EMBASSY_AND_MOFA, "embassy_required": 1, "embassy_fee_kwd": 0,
			 "mofa_required": 1, "mofa_fee_kwd": 5.0, "translation_required": 0},
		)
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_cache(doctype="HR Settings")

		pcc = self._pcc(EMBASSY_AND_MOFA)

		self.assertEqual(pcc.requires_embassy_attestation, 0)
		self.assertTrue(pcc.embassy_attestation_required)
		transition = self._transition("Draft", "Assign PRO", "Pending Embassy")
		self.assertTrue(frappe.safe_eval(transition.condition, None, {"doc": pcc.as_dict()}))

	def test_the_states_sit_on_the_right_desks(self):
		by_state = {}
		for state in self.workflow.states:
			by_state.setdefault(state.state, set()).add(state.allow_edit)

		for state in ("Pending Embassy", "Pending MOFA", "Pending Translation"):
			self.assertIn(PRO, by_state[state])
		for state in ("Draft", "Pending GR Operator", "On Hold", "Completed"):
			self.assertIn(GRO, by_state[state])

	def test_completed_submits_the_document(self):
		completed = [s for s in self.workflow.states if s.state == "Completed"]
		self.assertTrue(completed)
		self.assertEqual(completed[0].doc_status, "1")

	# ------------------------------------------------- assignment rules

	def test_both_assignment_rules_exist_and_are_enabled(self):
		for rule in ("PCC Attestation-GRO", "PCC Attestation-PRO"):
			self.assertTrue(frappe.db.exists("Assignment Rule", rule), f"{rule} is missing")
			self.assertFalse(frappe.db.get_value("Assignment Rule", rule, "disabled"))

	def test_the_rule_conditions_evaluate_against_a_plain_field_context(self):
		# Frappe evaluates these with the document's fields as globals - there is no `doc` name
		# in scope. A condition written as doc.workflow_state raises NameError, which the
		# assignment layer swallows, and the record is assigned to nobody.
		for rule_name, assigning_states, other_state in (
			("PCC Attestation-GRO", ("Draft", "Pending GR Operator", "On Hold"), "Pending MOFA"),
			(
				"PCC Attestation-PRO",
				("Pending Embassy", "Pending MOFA", "Pending Translation"),
				"Draft",
			),
		):
			rule = frappe.get_doc("Assignment Rule", rule_name)
			for state in assigning_states:
				context = {"workflow_state": state}
				self.assertTrue(
					frappe.safe_eval(rule.assign_condition, None, dict(context)),
					f"{rule_name} does not assign in {state}",
				)
				self.assertFalse(
					frappe.safe_eval(rule.close_condition, None, dict(context)),
					f"{rule_name} closes in {state}",
				)

			context = {"workflow_state": other_state}
			self.assertFalse(
				frappe.safe_eval(rule.assign_condition, None, dict(context)),
				f"{rule_name} assigns in {other_state}",
			)
			self.assertTrue(
				frappe.safe_eval(rule.close_condition, None, dict(context)),
				f"{rule_name} does not close in {other_state}",
			)

	def test_the_pro_rule_assigns_from_the_pro_user_field(self):
		rule = frappe.get_doc("Assignment Rule", "PCC Attestation-PRO")
		self.assertEqual(rule.rule, "Based on Field")
		self.assertEqual(rule.field, "pro_user")
		self.assertTrue(frappe.get_meta("PCC Attestation").get_field("pro_user"))

	def test_the_gro_rule_assigns_from_a_field_that_exists(self):
		rule = frappe.get_doc("Assignment Rule", "PCC Attestation-GRO")
		self.assertEqual(rule.rule, "Based on Field")
		self.assertEqual(rule.field, "owner")

	# ------------------------------------------------------ receipt guards

	def test_leaving_pending_embassy_without_the_receipt_is_blocked(self):
		pcc = self._pcc(EMBASSY_AND_MOFA)
		pcc.db_set("workflow_state", "Pending Embassy")
		pcc.reload()

		pcc.workflow_state = "Pending MOFA"
		with self.assertRaises(frappe.ValidationError):
			pcc.save()

	def test_leaving_pending_mofa_without_the_receipt_is_blocked(self):
		pcc = self._pcc(MOFA_ONLY)
		pcc.db_set("workflow_state", "Pending MOFA")
		pcc.reload()

		pcc.workflow_state = "Pending GR Operator"
		with self.assertRaises(frappe.ValidationError):
			pcc.save()

	def test_leaving_pending_translation_without_the_receipt_is_blocked(self):
		pcc = self._pcc(MOFA_ONLY, type="Translation")
		pcc.db_set("workflow_state", "Pending Translation")
		pcc.reload()

		pcc.workflow_state = "Pending GR Operator"
		with self.assertRaises(frappe.ValidationError):
			pcc.save()

	def test_the_receipt_lets_the_transition_through(self):
		pcc = self._pcc(MOFA_ONLY)
		pcc.db_set("workflow_state", "Pending MOFA")
		pcc.reload()

		pcc.upload_mofa_payment_receipt = A_RECEIPT
		pcc.workflow_state = "Pending GR Operator"
		pcc.save()

		self.assertEqual(pcc.workflow_state, "Pending GR Operator")

	def test_the_wrong_receipt_does_not_satisfy_the_guard(self):
		pcc = self._pcc(EMBASSY_AND_MOFA)
		pcc.db_set("workflow_state", "Pending Embassy")
		pcc.reload()

		pcc.upload_mofa_payment_receipt = A_RECEIPT
		pcc.workflow_state = "Pending MOFA"
		with self.assertRaises(frappe.ValidationError):
			pcc.save()

	def test_editing_without_moving_state_demands_nothing(self):
		pcc = self._pcc(MOFA_ONLY)
		pcc.db_set("workflow_state", "Pending MOFA")
		pcc.reload()

		pcc.category = "Overseas"
		pcc.save()

		self.assertEqual(pcc.workflow_state, "Pending MOFA")

	def test_a_state_that_collects_no_receipt_is_left_freely(self):
		pcc = self._pcc(MOFA_ONLY)
		pcc.db_set("workflow_state", "Pending GR Operator")
		pcc.reload()

		pcc.workflow_state = "On Hold"
		pcc.save()

		self.assertEqual(pcc.workflow_state, "On Hold")

	def test_every_guarded_state_is_a_state_the_workflow_has(self):
		from one_fm.grd.doctype.pcc_attestation.pcc_attestation import RECEIPT_REQUIRED_BY_STATE

		states = {state.state for state in self.workflow.states}
		meta = frappe.get_meta("PCC Attestation")
		for state, (fieldname, _label) in RECEIPT_REQUIRED_BY_STATE.items():
			self.assertIn(state, states, f"{state} is guarded but not a workflow state")
			self.assertTrue(meta.get_field(fieldname), f"no field {fieldname}")

	# ------------------------------------------------- the paths the data demands

	def test_a_nationality_needing_neither_step_is_not_sent_to_mofa(self):
		"""Ugandan: no embassy, no MOFA, translation only.

		The reason the routing needed a fourth condition. "Not embassy" used to fall through
		to Pending MOFA, so this record went to a step its nationality does not have and its
		PRO was then blocked by the receipt guard on evidence that was never going to exist.
		"""
		pcc = self._pcc(NEITHER)

		self.assertNotEqual(self._state_after_assign_pro(pcc), "Pending MOFA")

	def test_a_translation_only_nationality_goes_to_pending_translation(self):
		pcc = self._pcc(NEITHER)

		self.assertEqual(self._state_after_assign_pro(pcc), "Pending Translation")

	def test_a_nationality_needing_nothing_goes_straight_to_the_operator(self):
		settings = frappe.get_doc("HR Settings")
		settings.set("nationality_attestation_rules", [])
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_cache(doctype="HR Settings")

		pcc = self._pcc(MOFA_ONLY)

		self.assertEqual(self._state_after_assign_pro(pcc), "Pending GR Operator")

	def test_the_embassy_step_hands_back_to_the_operator_when_mofa_does_not_apply(self):
		"""An embassy-only nationality must not be parked in Pending MOFA either.

		None of the reporter's thirteen rows is embassy-without-MOFA today, so this is the
		symmetric case rather than one seen in the data - but the condition costs a line and
		the alternative is a record that cannot be moved.
		"""
		transitions = [
			t for t in frappe.get_doc("Workflow", "PCC Attestation").transitions
			if t.state == "Pending Embassy"
		]
		destinations = {t.next_state: t.condition for t in transitions}

		self.assertIn("Pending MOFA", destinations)
		self.assertIn("Pending GR Operator", destinations)
		self.assertEqual(destinations["Pending MOFA"], "doc.mofa_attestation_required")
		self.assertEqual(destinations["Pending GR Operator"], "not doc.mofa_attestation_required")

	def _state_after_assign_pro(self, pcc):
		"""The one Draft destination whose condition this record satisfies.

		Evaluated the way frappe.model.workflow does, so a change to the expressions is caught
		here rather than in a user's face.
		"""
		from frappe.model.workflow import get_workflow_safe_globals

		matched = [
			transition.next_state
			for transition in frappe.get_doc("Workflow", "PCC Attestation").transitions
			if transition.state == "Draft"
			and frappe.safe_eval(
				transition.condition, get_workflow_safe_globals(), dict(doc=pcc.as_dict())
			)
		]

		self.assertEqual(len(matched), 1, f"expected exactly one destination, got {matched}")
		return matched[0]
