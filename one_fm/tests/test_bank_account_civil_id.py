# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Bank Account Civil ID rule.

The hook is exercised against a document stub, so no Bank Account is created.
"""

import os

import frappe
from frappe.tests.utils import FrappeTestCase

import one_fm
from one_fm.overrides.bank_account import validate_civil_id


def _doc(**values):
	doc = frappe._dict(
		is_company_account=0, party_type=None, party=None, civil_id=None, flags=frappe._dict()
	)
	doc.update(values)
	return doc


class TestValidateCivilId(FrappeTestCase):
	def _employee(self, civil_id):
		employee = frappe.db.get_value("Employee", {}, "name")
		if not employee:
			self.skipTest("No Employee on this site")
		frappe.db.set_value("Employee", employee, "one_fm_civil_id", civil_id)
		return employee

	def test_no_party_and_no_civil_id_throws(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			validate_civil_id(_doc())
		self.assertIn("Civil ID is mandatory", str(cm.exception))

	def test_a_blank_civil_id_counts_as_empty(self):
		with self.assertRaises(frappe.ValidationError):
			validate_civil_id(_doc(civil_id="   "))

	def test_no_party_with_a_typed_civil_id_saves(self):
		doc = _doc(civil_id=" 123456789012 ")
		validate_civil_id(doc)
		self.assertEqual(doc.civil_id, "123456789012")

	def test_employee_with_a_civil_id_fills_an_empty_field(self):
		employee = self._employee("EMP-CID-1")
		doc = _doc(party_type="Employee", party=employee)
		validate_civil_id(doc)
		self.assertEqual(doc.civil_id, "EMP-CID-1")

	def test_employee_without_a_civil_id_keeps_the_typed_value(self):
		employee = self._employee("")
		doc = _doc(party_type="Employee", party=employee, civil_id="TYPED-CID")
		validate_civil_id(doc)
		self.assertEqual(doc.civil_id, "TYPED-CID")

	def test_a_typed_value_is_not_overwritten_by_the_employee_value(self):
		employee = self._employee("EMP-CID-1")
		doc = _doc(party_type="Employee", party=employee, civil_id="TYPED-CID")
		validate_civil_id(doc)
		self.assertEqual(doc.civil_id, "TYPED-CID")

	def test_employee_without_a_civil_id_and_empty_field_throws(self):
		employee = self._employee("")
		with self.assertRaises(frappe.ValidationError):
			validate_civil_id(_doc(party_type="Employee", party=employee))

	def test_ignore_civil_id_flag_lets_an_empty_field_save(self):
		doc = _doc(flags=frappe._dict(ignore_civil_id=True))
		validate_civil_id(doc)
		self.assertFalse(doc.civil_id)

	def test_ignore_mandatory_flag_is_not_the_bypass(self):
		with self.assertRaises(frappe.ValidationError):
			validate_civil_id(_doc(flags=frappe._dict(ignore_mandatory=True)))

	def test_company_account_saves_without_a_civil_id(self):
		validate_civil_id(_doc(is_company_account=1))

	def test_non_employee_party_saves_without_a_civil_id(self):
		validate_civil_id(_doc(party_type="Supplier", party="Any Supplier"))


class TestCivilIdIsWired(FrappeTestCase):
	def test_the_hook_is_in_the_validate_list_with_the_existing_ones(self):
		validate = frappe.get_hooks("doc_events").get("Bank Account", {}).get("validate") or []
		if isinstance(validate, str):
			validate = [validate]
		self.assertIn("one_fm.overrides.bank_account.validate_civil_id", validate)
		self.assertIn("one_fm.overrides.bank_account.validate_iban", validate)
		self.assertIn("one_fm.utils.validate_iban_is_filled", validate)

	def test_the_custom_field_is_defined_without_a_fetch_from(self):
		from one_fm.custom.custom_field.bank_account import get_bank_account_custom_fields

		field = next(
			f for f in get_bank_account_custom_fields()["Bank Account"] if f["fieldname"] == "civil_id"
		)
		self.assertEqual(field["fieldtype"], "Data")
		self.assertEqual(field["insert_after"], "party")
		self.assertNotIn("fetch_from", field)
		self.assertFalse(field.get("reqd"))
		self.assertIn("mandatory_depends_on", field)

	def test_the_patch_is_registered_after_post_model_sync(self):
		path = os.path.join(os.path.dirname(one_fm.__file__), "patches.txt")
		with open(path) as f:
			lines = [line.split("#")[0].strip() for line in f.read().splitlines()]
		self.assertIn("one_fm.patches.v15_0.add_bank_account_civil_id", lines)
		self.assertGreater(
			lines.index("one_fm.patches.v15_0.add_bank_account_civil_id"), lines.index("[post_model_sync]")
		)
