# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.submit_approved_document_requests import execute


class TestDocumentRequestSubmittable(FrappeTestCase):
	def test_doctype_is_submittable_and_employee_can_submit(self):
		frappe.reload_doc("one_fm", "doctype", "document_request")
		meta = frappe.get_meta("Document Request")
		self.assertTrue(meta.is_submittable)
		employee_perms = [p for p in meta.permissions if p.role == "Employee"]
		self.assertTrue(all(p.submit for p in employee_perms))

	def test_patch_submits_only_approved_drafts_and_is_rerunnable(self):
		if not frappe.db.has_column("Document Request", "workflow_state"):
			create_custom_field(
				"Document Request", {"fieldname": "workflow_state", "fieldtype": "Data", "label": "Workflow State"}
			)
		rows = {}
		for state, docstatus in (("Approved", 0), ("Pending", 0), ("Approved", 2)):
			name = frappe.generate_hash(length=10)
			frappe.get_doc(
				{"doctype": "Document Request", "name": name, "docstatus": docstatus, "workflow_state": state}
			).db_insert()
			rows[(state, docstatus)] = name

		execute()
		execute()

		get = lambda key: frappe.db.get_value("Document Request", rows[key], "docstatus")
		self.assertEqual(get(("Approved", 0)), 1)
		self.assertEqual(get(("Pending", 0)), 0)
		self.assertEqual(get(("Approved", 2)), 2)
