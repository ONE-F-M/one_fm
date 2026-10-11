# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.show_document_request_status_column import execute


class TestDocumentRequestStatusColumn(FrappeTestCase):
	"""Saved list settings keep only the columns they name, so the patch adds the status column."""

	def _save_settings(self, fields):
		frappe.db.delete("List View Settings", "Document Request")
		settings = frappe.new_doc("List View Settings")
		settings.name = "Document Request"
		settings.fields = json.dumps(fields) if fields is not None else None
		settings.db_insert()

	def _fields(self):
		return json.loads(frappe.db.get_value("List View Settings", "Document Request", "fields"))

	def test_status_column_is_added_after_the_subject(self):
		self._save_settings([{"fieldname": "title"}, {"fieldname": "document_type"}])
		execute()
		self.assertEqual([d["fieldname"] for d in self._fields()], ["title", "status_field", "document_type"])

	def test_running_twice_adds_the_column_once(self):
		self._save_settings([{"fieldname": "title"}, {"fieldname": "document_type"}])
		execute()
		execute()
		self.assertEqual([d["fieldname"] for d in self._fields()].count("status_field"), 1)

	def test_settings_without_saved_columns_are_left_alone(self):
		self._save_settings(None)
		execute()
		self.assertIsNone(frappe.db.get_value("List View Settings", "Document Request", "fields"))
