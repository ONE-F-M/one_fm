# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002593: what a Work Permit or a PACI is called before its Civil ID exists."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.document_title import TITLE_SOURCES, document_title, set_document_title

DOCTYPES = ("Work Permit", "PACI")


def _definition(module, doctype_folder):
	return json.loads(
		frappe.read_file(
			frappe.get_app_path("one_fm", "grd", "doctype", doctype_folder, f"{doctype_folder}.json")
		)
	)


class TestTheTitleFallsBack(FrappeTestCase):
	def test_the_civil_id_wins_when_it_is_there(self):
		doc = frappe._dict(
			civil_id="288010101234", employee_id="EMP-0001", employee="HR-EMP-04448"
		)
		self.assertEqual(document_title(doc), "288010101234")

	def test_the_employee_id_stands_in_while_the_civil_id_is_blank(self):
		"""The Work Permit is one of the steps that PRODUCES the Civil ID, so an
		onboarding candidate's record cannot be titled by it."""
		doc = frappe._dict(civil_id=None, employee_id="EMP-0001", employee="HR-EMP-04448")
		self.assertEqual(document_title(doc), "EMP-0001")

	def test_whitespace_is_not_an_identifier(self):
		doc = frappe._dict(civil_id="   ", employee_id="EMP-0001", employee="HR-EMP-04448")
		self.assertEqual(document_title(doc), "EMP-0001")

	def test_the_employee_link_is_the_last_resort(self):
		"""PACI has no employee_name field, so the link is what both records share."""
		doc = frappe._dict(civil_id="", employee_id="", employee="HR-EMP-04448")
		self.assertEqual(document_title(doc), "HR-EMP-04448")

	def test_a_record_naming_nobody_is_titled_by_nothing(self):
		"""An invented title would be worse than an empty one."""
		doc = frappe._dict(civil_id="", employee_id=None, employee="")
		self.assertEqual(document_title(doc), "")

	def test_the_title_comes_back_to_the_civil_id_once_it_is_issued(self):
		doc = frappe._dict(civil_id=None, employee_id="EMP-0001", employee="HR-EMP-04448")
		set_document_title(doc)
		self.assertEqual(doc.title, "EMP-0001")

		doc.civil_id = "288010101234"
		set_document_title(doc)
		self.assertEqual(doc.title, "288010101234")


class TestTheDocTypesAreWiredForIt(FrappeTestCase):
	def test_both_are_titled_by_the_derived_field(self):
		for folder in ("work_permit", "paci"):
			definition = _definition(folder, folder)
			self.assertEqual(definition["title_field"], "title", folder)

	def test_the_title_field_is_derived_not_typed(self):
		for folder in ("work_permit", "paci"):
			field = next(
				f for f in _definition(folder, folder)["fields"] if f["fieldname"] == "title"
			)
			self.assertEqual(field["fieldtype"], "Data", folder)
			self.assertEqual(field["read_only"], 1, folder)
			self.assertEqual(field["no_copy"], 1, folder)

	def test_every_source_field_exists_on_both_doctypes(self):
		"""A source that is not a field reads as blank and silently skips a rung."""
		for folder in ("work_permit", "paci"):
			fieldnames = {f["fieldname"] for f in _definition(folder, folder)["fields"]}
			for source in TITLE_SOURCES:
				self.assertIn(source, fieldnames, f"{folder}.{source}")

	def test_both_controllers_derive_it_on_validate(self):
		for folder in ("work_permit", "paci"):
			source = frappe.read_file(
				frappe.get_app_path("one_fm", "grd", "doctype", folder, f"{folder}.py")
			)
			self.assertIn("set_document_title(self)", source, folder)

	def test_the_backfill_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.backfill_grd_document_titles", patches)
