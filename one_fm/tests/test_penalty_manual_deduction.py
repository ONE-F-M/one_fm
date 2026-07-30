# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the manual (non-code) penalty deduction path (WI-001795).

With no Applied Penalty Code the penalty is not a repeat offence: no history is
consulted, the Offence Count reads zero, and a Uniform or Damage category exposes
Salary Deduction Amount as an editable figure instead of one derived from the
Penalty Level matrix.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

DOCTYPE = "Penalty And Investigation"
CODE_DRIVEN = "eval:!!doc.applied_penalty_code"


class TestPenaltyCategoryOptions(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.meta = frappe.get_meta(DOCTYPE)

	def _options(self, fieldname):
		return [o for o in (self.meta.get_field(fieldname).options or "").split("\n") if o]

	def test_the_manual_categories_are_available(self):
		self.assertEqual(
			self._options("penalty_category"),
			["Warning", "Salary Deduction", "Uniform", "Damage"],
		)

	def test_action_type_still_offers_the_code_driven_values(self):
		self.assertEqual(
			self._options("deduction_type"),
			["Warning", "Salary Deduction", "Suspension", "Termination"],
		)

	def test_action_type_is_still_labelled_action_type(self):
		# Relabelled rather than duplicated, so there is one source of truth.
		self.assertEqual(self.meta.get_field("deduction_type").label, "Action Type")


class TestEditabilityFollowsThePenaltyCode(FrappeTestCase):
	"""The code-driven path stays derived; the manual path is hand-entered."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.meta = frappe.get_meta(DOCTYPE)

	def test_the_three_manual_fields_unlock_when_no_code_is_selected(self):
		for fieldname in ("penalty_category", "deduction_type", "salary_deduction_amount"):
			df = self.meta.get_field(fieldname)
			self.assertEqual(df.read_only_depends_on, CODE_DRIVEN, msg=fieldname)
			# A static read_only would win over the conditional rule.
			self.assertFalse(df.read_only, msg=fieldname)

	def test_the_amount_is_hidden_unless_it_is_relevant(self):
		# Shown on the code-driven path (read-only, per WI-001794) and on the manual
		# path only for Uniform or Damage - hidden for a manual Warning or Salary
		# Deduction, which carry no monetary figure of their own.
		depends_on = self.meta.get_field("salary_deduction_amount").depends_on
		self.assertIn("applied_penalty_code", depends_on)
		self.assertIn("Uniform", depends_on)
		self.assertIn("Damage", depends_on)

	def test_derived_fields_stay_read_only_on_both_paths(self):
		for fieldname in ("offence_count", "applied_level", "salary_deduction_days"):
			self.assertEqual(self.meta.get_field(fieldname).read_only, 1, msg=fieldname)


class TestManualPathSkipsTheHistoryLookup(FrappeTestCase):
	def setUp(self):
		self.employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not self.employee:
			self.skipTest("no Active employee on this instance")

	def _doc(self, **kwargs):
		doc = frappe.new_doc(DOCTYPE)
		doc.employee = self.employee
		doc.update(kwargs)
		return doc

	def test_a_uniform_deduction_reports_no_offence(self):
		doc = self._doc(penalty_category="Uniform", salary_deduction_amount=25)
		doc.calculate_offence_count()
		self.assertEqual(doc.offence_count, 0)

	def test_a_damage_deduction_keeps_its_entered_amount(self):
		doc = self._doc(penalty_category="Damage", salary_deduction_amount=150)
		doc.calculate_offence_count()
		self.assertEqual(doc.offence_count, 0)
		# The manual figure must survive: nothing derives it on this path.
		self.assertEqual(doc.salary_deduction_amount, 150)

	def test_the_level_and_days_are_left_untouched(self):
		# The AC is explicit that these are "not updated" rather than cleared.
		doc = self._doc(penalty_category="Uniform", applied_level="3rd", salary_deduction_days=2)
		doc.calculate_offence_count()
		self.assertEqual(doc.applied_level, "3rd")
		self.assertEqual(doc.salary_deduction_days, 2)

	def test_a_stale_offence_count_is_reset(self):
		# Selecting a code and then clearing it must not leave the old count behind.
		doc = self._doc(penalty_category="Damage", offence_count=4)
		doc.calculate_offence_count()
		self.assertEqual(doc.offence_count, 0)

	def test_a_manual_warning_carries_no_amount_field(self):
		# Nothing to assert on the value; the field is hidden by depends_on, so the
		# meaningful check is that the count is still zeroed.
		doc = self._doc(penalty_category="Warning")
		doc.calculate_offence_count()
		self.assertEqual(doc.offence_count, 0)
