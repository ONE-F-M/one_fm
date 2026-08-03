# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Bank Account IBAN rules (WI-001797).

Spaces are always stripped; the 30-character rule bites only when the IBAN
changes, so a legacy account with a non-conforming IBAN can still be saved for
unrelated edits instead of being frozen.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides.bank_account import IBAN_LENGTH, normalise_iban, validate_iban

VALID_IBAN = "KW48NBOK0000000000204576567500"
SHORT_IBAN = "KW48NBOK123"


class TestNormaliseIban(FrappeTestCase):
	def test_the_fixture_is_the_length_the_rule_expects(self):
		self.assertEqual(len(VALID_IBAN), IBAN_LENGTH)

	def test_grouping_spaces_are_removed(self):
		self.assertEqual(
			normalise_iban("KW48 NBOK 0000 0000 0020 4576 5675 00"),
			"KW48NBOK0000000000204576567500",
		)

	def test_all_whitespace_is_removed(self):
		self.assertEqual(normalise_iban("KW48\tNBOK\n0000"), "KW48NBOK0000")

	def test_blank_input_is_safe(self):
		self.assertEqual(normalise_iban(""), "")
		self.assertEqual(normalise_iban(None), "")

	def test_a_clean_iban_is_untouched(self):
		self.assertEqual(normalise_iban(VALID_IBAN), VALID_IBAN)


class TestValidateIban(FrappeTestCase):
	"""Exercises the hook against a document stub, so no Bank Account is created."""

	def _doc(self, iban, before_iban=None):
		doc = frappe._dict(iban=iban)
		before = frappe._dict(iban=before_iban) if before_iban is not None else None
		doc.get_doc_before_save = lambda: before
		return doc

	def test_a_valid_new_iban_passes_and_is_stored_clean(self):
		doc = self._doc(VALID_IBAN)
		validate_iban(doc)
		self.assertEqual(doc.iban, VALID_IBAN)

	def test_spaces_are_stripped_on_a_new_record(self):
		spaced = " ".join([VALID_IBAN[i : i + 4] for i in range(0, len(VALID_IBAN), 4)])
		doc = self._doc(spaced)
		validate_iban(doc)
		self.assertEqual(doc.iban, VALID_IBAN)
		self.assertEqual(len(doc.iban), IBAN_LENGTH)

	def test_a_short_new_iban_is_rejected(self):
		doc = self._doc(SHORT_IBAN)
		with self.assertRaises(frappe.ValidationError):
			validate_iban(doc)

	def test_a_long_new_iban_is_rejected(self):
		doc = self._doc(VALID_IBAN + "99")
		with self.assertRaises(frappe.ValidationError):
			validate_iban(doc)

	def test_the_error_message_is_the_one_the_ac_specifies(self):
		doc = self._doc(SHORT_IBAN)
		with self.assertRaises(frappe.ValidationError) as cm:
			validate_iban(doc)
		self.assertIn("IBAN must be exactly 30 characters long.", str(cm.exception))

	def test_an_empty_iban_is_left_to_the_existing_workflow_rule(self):
		# validate_iban_is_filled already guards the Active Account transition.
		doc = self._doc("")
		validate_iban(doc)
		self.assertFalse(doc.iban)

	def test_an_untouched_legacy_iban_does_not_block_an_unrelated_save(self):
		# The whole point of validating on change: a short stored IBAN must not
		# freeze the record.
		doc = self._doc(SHORT_IBAN, before_iban=SHORT_IBAN)
		validate_iban(doc)
		self.assertEqual(doc.iban, SHORT_IBAN)

	def test_stripping_a_legacy_value_is_not_treated_as_a_change(self):
		# Normalised-to-normalised comparison: removing the stored spaces must not
		# by itself trip the length check.
		doc = self._doc("KW48 NBOK 123", before_iban="KW48 NBOK 123")
		validate_iban(doc)
		self.assertEqual(doc.iban, "KW48NBOK123")

	def test_editing_a_legacy_iban_to_another_bad_value_is_rejected(self):
		doc = self._doc("KW48NBOK999", before_iban=SHORT_IBAN)
		with self.assertRaises(frappe.ValidationError):
			validate_iban(doc)

	def test_editing_a_legacy_iban_to_a_valid_one_is_accepted(self):
		doc = self._doc(VALID_IBAN, before_iban=SHORT_IBAN)
		validate_iban(doc)
		self.assertEqual(doc.iban, VALID_IBAN)


class TestIbanHookIsWired(FrappeTestCase):
	"""The logic above is only reached if the hook is registered, and a validate
	hook that was left a bare string would silently drop the existing IBAN rule."""

	def test_both_bank_account_validate_hooks_are_registered(self):
		hooks = frappe.get_hooks("doc_events").get("Bank Account", {})
		validate = hooks.get("validate") or []
		if isinstance(validate, str):
			validate = [validate]
		self.assertIn("one_fm.overrides.bank_account.validate_iban", validate)
		self.assertIn("one_fm.utils.validate_iban_is_filled", validate)

	def test_the_form_script_is_registered(self):
		self.assertEqual(
			frappe.get_hooks("doctype_js").get("Bank Account"),
			["public/js/doctype_js/bank_account.js"],
		)
