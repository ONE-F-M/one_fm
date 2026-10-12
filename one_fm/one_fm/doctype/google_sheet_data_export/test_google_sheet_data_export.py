# Copyright (c) 2023, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.google_sheet_data_export.exporter import (
	STANDARD_FIELDS,
	DataExporter,
	get_link_title_field,
	get_link_titles,
	get_standard_field,
)


def make_exporter(doctype, select_columns, **kwargs):
	"""Build a DataExporter without touching the Google Sheet API."""
	fake_api = {"service": None, "drive_api": None, "credentials": None}
	with patch.object(DataExporter, "initialize_service", return_value=fake_api):
		return DataExporter(
			doctype=doctype,
			select_columns=frappe.as_json(select_columns),
			with_data=1,
			**kwargs,
		)


def build_columns(doctype, select_columns, **kwargs):
	exporter = make_exporter(doctype, select_columns, **kwargs)
	exporter.labelrow = []
	exporter.fieldrow = []
	exporter.columns = []
	exporter.name_field = "name"
	exporter.build_field_columns(doctype)
	return exporter.columns


class TestGoogleSheetDataExport(FrappeTestCase):
	def test_get_standard_field(self):
		"""Standard columns resolve to a docfield owned by the exported DocType."""
		for fieldname in STANDARD_FIELDS:
			docfield = get_standard_field(fieldname, "ToDo")
			self.assertEqual(docfield.fieldname, fieldname)
			self.assertEqual(docfield.parent, "ToDo")
			self.assertFalse(docfield.hidden)

		self.assertIsNone(get_standard_field("not_a_standard_field", "ToDo"))

	def test_metadata_columns_are_exported(self):
		"""All six metadata columns survive column building for the parent DocType."""
		metadata = list(STANDARD_FIELDS.keys())
		columns = build_columns("ToDo", {"ToDo": ["description"] + metadata})

		for fieldname in metadata:
			self.assertIn(fieldname, columns)

		# metadata is merged after the regular fields, so it lands on the right edge
		self.assertLess(columns.index("description"), columns.index("owner"))

	def test_hidden_field_excluded_unless_included(self):
		"""A hidden field is only exported when the export opts in."""
		hidden_field = frappe.db.get_value(
			"DocField", {"parent": "ToDo", "hidden": 1, "fieldtype": ["not in", ("Section Break", "Column Break")]}, "fieldname"
		)
		if not hidden_field:
			self.skipTest("No hidden field on ToDo to test with")

		select_columns = {"ToDo": ["description", hidden_field]}

		self.assertNotIn(hidden_field, build_columns("ToDo", select_columns))
		self.assertIn(hidden_field, build_columns("ToDo", select_columns, include_hidden=1))

	def test_child_table_fields_are_exported(self):
		"""Child table columns are built alongside the parent ones."""
		select_columns = {
			"Workflow": ["document_type"],
			"Workflow Document State": ["state", "doc_status"],
		}
		exporter = make_exporter("Workflow", select_columns)
		exporter.labelrow = []
		exporter.fieldrow = []
		exporter.columns = []
		exporter.name_field = "name"

		exporter.build_field_columns("Workflow")
		exporter.build_field_columns("Workflow Document State", "states")

		self.assertIn("document_type", exporter.columns)
		self.assertIn("state", exporter.columns)
		self.assertIn("doc_status", exporter.columns)

	def test_stale_field_cache_is_dropped(self):
		"""A fieldname left over from a renamed or deleted field is skipped silently."""
		columns = build_columns("ToDo", {"ToDo": ["description", "field_that_no_longer_exists"]})

		self.assertIn("description", columns)
		self.assertNotIn("field_that_no_longer_exists", columns)

	def test_virtual_field_is_dropped(self):
		"""Virtual fields have no column in the table, so they cannot be exported."""
		virtual_field = frappe.db.get_value(
			"DocField", {"parent": "ToDo", "is_virtual": 1}, "fieldname"
		)
		if not virtual_field:
			self.skipTest("No virtual field on ToDo to test with")

		self.assertNotIn(virtual_field, build_columns("ToDo", {"ToDo": [virtual_field]}))


class TestLinkTitleExport(FrappeTestCase):
	"""A Link column must export what the form shows, not the stored document name."""

	def setUp(self):
		self.contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Gsde",
				"middle_name": "Link",
				"last_name": "Title",
			}
		).insert()
		# reproduce the live data: the name was set before the rest of the name was typed
		frappe.rename_doc("Contact", self.contact.name, "Gsde", force=True)
		self.contact.reload()

	def test_get_link_title_field(self):
		"""Only a DocType that asks to show its title in links resolves to a title field."""
		self.assertEqual(get_link_title_field("Contact"), "full_name")
		# ToDo has no title shown in links, so the name is what the form shows
		self.assertIsNone(get_link_title_field("ToDo"))

	def test_get_link_title_field_without_permission(self):
		"""Without read permission the name is kept rather than leaking a title."""
		with patch.object(frappe, "has_permission", return_value=False):
			self.assertIsNone(get_link_title_field("Contact"))

	def test_get_link_titles(self):
		"""Titles come back keyed by document name."""
		titles = get_link_titles("Contact", "full_name", [self.contact.name])

		self.assertEqual(titles[self.contact.name], self.contact.full_name)
		self.assertNotEqual(self.contact.name, self.contact.full_name)

	def test_link_value_is_exported_as_title(self):
		"""The stored name `Gsde` is exported as the full name the form shows."""
		exporter = make_exporter("Contact", {"Contact": ["first_name"]}, export_link_titles=1)
		docfield = frappe._dict({"fieldtype": "Link", "options": "Contact"})

		self.assertEqual(
			exporter.get_link_title(docfield, self.contact.name), self.contact.full_name
		)

	def test_plain_value_is_untouched(self):
		"""Anything that is not a resolvable Link keeps its stored value."""
		exporter = make_exporter("Contact", {"Contact": ["first_name"]}, export_link_titles=1)

		self.assertEqual(
			exporter.get_link_title(frappe._dict({"fieldtype": "Data"}), "Gsde"), "Gsde"
		)
		self.assertEqual(
			exporter.get_link_title(frappe._dict({"fieldtype": "Link", "options": "ToDo"}), "Gsde"),
			"Gsde",
		)
		self.assertEqual(
			exporter.get_link_title(frappe._dict({"fieldtype": "Link", "options": "Contact"}), ""), ""
		)

	def test_missing_link_keeps_the_stored_value(self):
		"""A deleted or unreadable document falls back to the stored name."""
		exporter = make_exporter("Contact", {"Contact": ["first_name"]}, export_link_titles=1)
		docfield = frappe._dict({"fieldtype": "Link", "options": "Contact"})

		self.assertEqual(exporter.get_link_title(docfield, "Not A Contact"), "Not A Contact")

	def test_titles_are_cached(self):
		"""Each linked DocType is queried once, however many rows use it."""
		exporter = make_exporter("Contact", {"Contact": ["first_name"]}, export_link_titles=1)
		docfield = frappe._dict({"fieldtype": "Link", "options": "Contact"})

		exporter.get_link_title(docfield, self.contact.name)
		with patch(
			"one_fm.one_fm.doctype.google_sheet_data_export.exporter.get_link_titles"
		) as get_titles:
			exporter.get_link_title(docfield, self.contact.name)
			get_titles.assert_not_called()

	def test_link_titles_are_opt_in(self):
		"""Without the setting the stored ID is exported, as it always was."""
		exporter = make_exporter("Contact", {"Contact": ["first_name"]})
		docfield = frappe._dict({"fieldtype": "Link", "options": "Contact"})

		self.assertEqual(exporter.get_link_title(docfield, self.contact.name), self.contact.name)
