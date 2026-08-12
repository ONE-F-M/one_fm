# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Recording a government document on an Employee without saving the whole Employee.

Reported from testing on MOI-2026-00369: completing a Residency threw

    Marital Status cannot be "Single". It should be one of "Unmarried", "Married",
    "Widow", "Divorce", "Unknown"

The Residency has nothing to do with marital status. It failed because it wrote its
attachment through ``employee.save()``, which re-validates every field on the Employee -
and most of the fleet holds a Marital Status the field's current options reject.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.utils import attach_employee_document, next_employee_document_idx

DOCUMENT = "Residency Expiry Attachment"


class TestAttachingAnEmployeeDocument(FrappeTestCase):
	def setUp(self):
		self.employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not self.employee:
			self.skipTest("no Active Employee on this instance")

	def rows(self, document_name=DOCUMENT):
		return frappe.get_all(
			"Employee Document",
			filters={"parent": self.employee, "document_name": document_name},
			fields=["name", "attach", "valid_till", "idx"],
			order_by="idx",
		)

	def test_a_document_the_employee_does_not_have_is_added(self):
		name = f"Test Doc {frappe.generate_hash(length=6)}"
		self.addCleanup(
			frappe.db.delete, "Employee Document", {"parent": self.employee, "document_name": name}
		)

		attach_employee_document(
			self.employee, document_name=name, attach="/private/files/x.pdf",
			valid_till="2027-01-01",
		)

		rows = self.rows(name)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].attach, "/private/files/x.pdf")

	def test_it_takes_the_next_row_number(self):
		"""A raw insert gets no idx of its own; two rows at 0 would tie."""
		name = f"Test Doc {frappe.generate_hash(length=6)}"
		self.addCleanup(
			frappe.db.delete, "Employee Document", {"parent": self.employee, "document_name": name}
		)
		expected = next_employee_document_idx(self.employee)

		attach_employee_document(
			self.employee, document_name=name, attach="/private/files/x.pdf",
			valid_till="2027-01-01",
		)

		self.assertEqual(self.rows(name)[0].idx, expected)

	def test_a_renewal_replaces_the_row_it_renews(self):
		"""The old code inserted the new row beside the existing one and kept both, so
		every renewal left another copy behind."""
		name = f"Test Doc {frappe.generate_hash(length=6)}"
		self.addCleanup(
			frappe.db.delete, "Employee Document", {"parent": self.employee, "document_name": name}
		)
		attach_employee_document(
			self.employee, document_name=name, attach="/private/files/old.pdf",
			valid_till="2026-01-01",
		)

		attach_employee_document(
			self.employee, document_name=name, attach="/private/files/new.pdf",
			valid_till="2027-01-01",
		)

		rows = self.rows(name)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].attach, "/private/files/new.pdf")
		self.assertEqual(str(rows[0].valid_till), "2027-01-01")

	def test_it_does_not_drag_the_employee_through_validation(self):
		"""The whole point. An Employee holding a Marital Status the options no longer
		accept can still be given a document - which is what a GRD clerk needs."""
		name = f"Test Doc {frappe.generate_hash(length=6)}"
		self.addCleanup(
			frappe.db.delete, "Employee Document", {"parent": self.employee, "document_name": name}
		)
		was = frappe.db.get_value("Employee", self.employee, "marital_status")
		self.addCleanup(
			frappe.db.set_value, "Employee", self.employee, "marital_status", was,
			update_modified=False,
		)
		frappe.db.set_value(
			"Employee", self.employee, "marital_status", "Not A Valid Option",
			update_modified=False,
		)

		attach_employee_document(
			self.employee, document_name=name, attach="/private/files/x.pdf",
			valid_till="2027-01-01",
		)

		self.assertEqual(len(self.rows(name)), 1)

	def test_a_full_employee_save_would_have_failed_there(self):
		"""What makes the test above meaningful rather than a tautology."""
		was = frappe.db.get_value("Employee", self.employee, "marital_status")
		self.addCleanup(
			frappe.db.set_value, "Employee", self.employee, "marital_status", was,
			update_modified=False,
		)
		frappe.db.set_value(
			"Employee", self.employee, "marital_status", "Not A Valid Option",
			update_modified=False,
		)

		doc = frappe.get_doc("Employee", self.employee)
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)


class TestTheResidencyUsesIt(FrappeTestCase):
	def test_completing_a_residency_no_longer_saves_the_whole_employee(self):
		"""Pinned on the source: a full save is what broke this."""
		import inspect

		from one_fm.grd.doctype.residency.residency import Residency

		method = Residency.set_residency_expiry_new_date_in_employee_doctype
		# The docstring explains the save it replaced, so only the body is inspected.
		body = inspect.getsource(method).replace(method.__doc__ or "", "")

		self.assertIn("attach_employee_document", body)
		self.assertNotIn("employee.save()", body)
