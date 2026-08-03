# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Accommodation Leave Movement assignment rules (WI-001781).

An OUT movement is assigned to the resident's site supervisor and closes once the
matching IN movement is submitted; an IN movement is assigned and stays open until
the document is cancelled.
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.safe_exec import get_safe_globals

OUT_RULE = "Accommodation Leave Movement-Site Supervisor"
IN_RULE = "Accommodation Leave Movement-Site Supervisor- CheckIn"


def _rule(name):
	if not frappe.db.exists("Assignment Rule", name):
		return None
	return frappe.get_doc("Assignment Rule", name)


class TestRulesExist(FrappeTestCase):
	def test_both_rules_are_installed(self):
		for name in (OUT_RULE, IN_RULE):
			self.assertTrue(frappe.db.exists("Assignment Rule", name), msg=name)

	def test_they_assign_on_the_site_supervisor_field(self):
		for name in (OUT_RULE, IN_RULE):
			rule = _rule(name)
			self.assertEqual(rule.rule, "Based on Field")
			self.assertEqual(rule.field, "site_supervisor")

	def test_the_field_they_assign_on_exists(self):
		# Assigning on a missing field silently assigns to nobody.
		self.assertTrue(
			frappe.get_meta("Accommodation Leave Movement").has_field("site_supervisor")
		)

	def test_they_are_enabled_and_cover_every_day(self):
		for name in (OUT_RULE, IN_RULE):
			rule = _rule(name)
			self.assertFalse(rule.disabled)
			self.assertEqual(len(rule.assignment_days), 7)

	def test_each_rule_targets_one_movement_direction(self):
		self.assertIn('type == "OUT"', _rule(OUT_RULE).assign_condition)
		self.assertIn('type == "IN"', _rule(IN_RULE).assign_condition)
		for name in (OUT_RULE, IN_RULE):
			self.assertIn("docstatus == 1", _rule(name).assign_condition)


class TestConditionsAreEvaluable(FrappeTestCase):
	"""Conditions run through safe_eval, which exposes only a subset of frappe."""

	def _eval(self, condition, doc):
		return frappe.safe_eval(condition, get_safe_globals(), doc)

	def test_no_condition_calls_something_safe_eval_cannot_reach(self):
		# frappe.db.exists is unavailable here - the same trap already patched out of
		# the Leave Application rule - so a condition using it never evaluates.
		for name in (OUT_RULE, IN_RULE):
			rule = _rule(name)
			for condition in (rule.assign_condition, rule.close_condition or ""):
				self.assertNotIn("frappe.db.exists", condition)

	def test_the_out_rule_assigns_a_submitted_out_movement(self):
		self.assertTrue(
			self._eval(_rule(OUT_RULE).assign_condition, {"docstatus": 1, "type": "OUT"})
		)
		self.assertFalse(
			self._eval(_rule(OUT_RULE).assign_condition, {"docstatus": 1, "type": "IN"})
		)
		self.assertFalse(
			self._eval(_rule(OUT_RULE).assign_condition, {"docstatus": 0, "type": "OUT"})
		)

	def test_the_out_rule_closes_once_the_resident_has_returned(self):
		close = _rule(OUT_RULE).close_condition
		self.assertTrue(self._eval(close, {"docstatus": 1, "checked_out": 1}))
		self.assertFalse(self._eval(close, {"docstatus": 1, "checked_out": 0}))
		# Cancelling also closes it.
		self.assertTrue(self._eval(close, {"docstatus": 2, "checked_out": 0}))

	def test_the_in_rule_closes_only_on_cancellation(self):
		close = _rule(IN_RULE).close_condition
		self.assertTrue(self._eval(close, {"docstatus": 2}))
		self.assertFalse(self._eval(close, {"docstatus": 1}))

	def test_the_closing_flag_is_a_real_field(self):
		self.assertTrue(
			frappe.get_meta("Accommodation Leave Movement").has_field("checked_out")
		)


class TestReapplyOnReturn(FrappeTestCase):
	"""The OUT assignment closes on a flag written with set_value, which does not
	save that document - so the rule has to be re-applied explicitly."""

	def test_the_controller_reapplies_rules_for_the_linked_movement(self):
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "accommodation", "doctype", "accommodation_leave_movement",
				"accommodation_leave_movement.py",
			)
		)
		self.assertIn("reapply_own_assignment_rules(self.checkin_reference)", source)
		self.assertIn("def reapply_own_assignment_rules", source)
