# Copyright (c) 2023, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.google_sheet_data_export.exporter import (
	STANDARD_FIELDS,
	DataExporter,
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
