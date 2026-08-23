# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002033: the Action's classification reaches every sub-document it opens."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.grd.doctype.preparation.preparation import (
	NEW_ACTION_DOCUMENTS,
	category_for_action,
	create_documents_for_row,
)

# The field on each sub-document that carries the Action's classification.
CLASSIFICATION_FIELD = {
	"work_permit": ("Work Permit", "work_permit_type"),
	"medical_insurance": ("Medical Insurance", "insurance_status"),
	"residency": ("Residency", "category"),
	"paci": ("PACI", "category"),
}


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return frappe.get_doc("Employee", name)


class TestActionCategoryMapping(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()

	def _documents_for(self, action):
		preparation = frappe.get_doc(
			{
				"doctype": "Preparation",
				"category": category_for_action(action),
				"posting_date": nowdate(),
				"preparation_record": [{"employee": self.employee.name, "renewal_or_extend": action}],
			}
		)
		preparation.flags.ignore_permissions = True
		preparation.insert()
		create_documents_for_row(preparation.preparation_record[0], preparation.name)
		return preparation.name

	def test_every_planned_classification_is_stated_not_derived(self):
		# The point of the story: the table says what each document gets, rather than three
		# of the four reading None and leaving it to the creator.
		for action, plan in NEW_ACTION_DOCUMENTS.items():
			for document, classification in plan.items():
				self.assertIsNotNone(
					classification, f"{action} does not state what its {document} is opened as"
				)

	def test_the_plan_only_names_classifications_the_field_accepts(self):
		for action, plan in NEW_ACTION_DOCUMENTS.items():
			for document, classification in plan.items():
				doctype, fieldname = CLASSIFICATION_FIELD[document]
				options = frappe.get_meta(doctype).get_field(fieldname).options.split("\n")
				self.assertIn(
					classification,
					options,
					f"{action} opens its {document} as {classification!r}, which {doctype}.{fieldname} "
					"does not offer",
				)

	def test_overseas_government_maps_all_four_documents(self):
		action = "Overseas (Government)"
		preparation = self._documents_for(action)

		self.assertEqual(self._classification(preparation, "Work Permit", "work_permit_type"), action)
		self.assertEqual(
			self._classification(preparation, "Medical Insurance", "insurance_status"), "New"
		)
		self.assertEqual(self._classification(preparation, "Residency", "category"), "First Time")
		self.assertEqual(self._classification(preparation, "PACI", "category"), "New Application")

	def test_local_transfer_maps_all_four_documents(self):
		preparation = self._documents_for("Local Transfer")

		self.assertEqual(
			self._classification(preparation, "Work Permit", "work_permit_type"), "Local Transfer"
		)
		self.assertEqual(
			self._classification(preparation, "Medical Insurance", "insurance_status"), "Local Transfer"
		)
		self.assertEqual(self._classification(preparation, "Residency", "category"), "Transfer")
		self.assertEqual(self._classification(preparation, "PACI", "category"), "Transfer")

	def test_overseas_maps_all_four_documents(self):
		preparation = self._documents_for("Overseas")

		self.assertEqual(self._classification(preparation, "Work Permit", "work_permit_type"), "Overseas")
		self.assertEqual(
			self._classification(preparation, "Medical Insurance", "insurance_status"), "New"
		)
		self.assertEqual(self._classification(preparation, "Residency", "category"), "First Time")
		self.assertEqual(self._classification(preparation, "PACI", "category"), "New Application")

	def test_what_the_plan_says_is_what_the_documents_get(self):
		# The guard the story is really asking for: the table and reality cannot drift.
		for action, plan in NEW_ACTION_DOCUMENTS.items():
			preparation = self._documents_for(action)
			for document, classification in plan.items():
				doctype, fieldname = CLASSIFICATION_FIELD[document]
				self.assertEqual(
					self._classification(preparation, doctype, fieldname),
					classification,
					f"{action}: {doctype}.{fieldname} does not match the plan",
				)

	def test_a_submitted_sub_document_still_carries_its_classification(self):
		preparation = self._documents_for("Overseas (Government)")
		paci = frappe.get_doc(
			"PACI", {"preparation": preparation, "employee": self.employee.name}
		)
		paci.flags.ignore_permissions = True
		paci.new_civil_id_expiry_date = nowdate()
		paci.submit()

		self.assertEqual(frappe.db.get_value("PACI", paci.name, "category"), "New Application")
		self.assertEqual(paci.docstatus, 1)

	def _classification(self, preparation, doctype, fieldname):
		return frappe.db.get_value(
			doctype, {"preparation": preparation, "employee": self.employee.name}, fieldname
		)
