# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Completing a Residency syncs the Visa Extension Expiry Date to the Employee."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from one_fm.custom.custom_field.employee import get_employee_custom_fields
from one_fm.grd.doctype.preparation.preparation import RESIDENCY_ONLY_ACTIONS

FIELD = "custom_visa_extension_expiry_date"
RESTORED_FIELDS = (FIELD, "residency_expiry_date", "work_permit_expiry_date")
ATTACHMENT = "Residency Expiry Attachment"
ATTACHMENT_FIELDS = ("attach", "issued_on", "valid_till")


def _fixture_field(fieldname):
	for field in get_employee_custom_fields()["Employee"]:
		if field["fieldname"] == fieldname:
			return field


class TestTheFixture(FrappeTestCase):
	def test_field_is_a_read_only_date_after_work_permit_expiry_date(self):
		field = _fixture_field(FIELD)
		self.assertIsNotNone(field)
		self.assertEqual(field["fieldtype"], "Date")
		self.assertEqual(field["label"], "Visa Extension Expiry Date")
		self.assertEqual(field["insert_after"], "work_permit_expiry_date")
		self.assertEqual(field.get("read_only"), 1)
		self.assertNotIn("under_company_residency", field.get("depends_on") or "")

	def test_column_break_no_longer_shares_the_anchor(self):
		self.assertEqual(_fixture_field("column_break_64")["insert_after"], FIELD)

	def test_patch_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.add_employee_visa_extension_expiry_date", patches)


class TestEmployeeSync(FrappeTestCase):
	def setUp(self):
		self.employee = frappe.db.get_value(
			"Employee", {"status": "Active"}, "name", order_by="creation asc"
		)
		if not self.employee:
			self.skipTest("No active employee on this site")
		self.saved = frappe.db.get_value("Employee", self.employee, RESTORED_FIELDS, as_dict=True)
		self.attachment = frappe.db.get_value(
			"Employee Document",
			{"parent": self.employee, "document_name": ATTACHMENT},
			["name", *ATTACHMENT_FIELDS],
			as_dict=True,
		)
		# before_insert commits; keep everything inside the test transaction.
		commit = patch("frappe.db.commit")
		commit.start()
		self.addCleanup(commit.stop)

	def tearDown(self):
		frappe.db.set_value("Employee", self.employee, dict(self.saved))
		if self.attachment:
			frappe.db.set_value(
				"Employee Document",
				self.attachment.name,
				{f: self.attachment[f] for f in ATTACHMENT_FIELDS},
			)
		else:
			frappe.db.delete(
				"Employee Document", {"parent": self.employee, "document_name": ATTACHMENT}
			)

	def _submit(self, category, action, **kwargs):
		residency = frappe.get_doc(
			{
				"doctype": "Residency",
				"employee": self.employee,
				"category": category,
				"renewal_or_extend": action,
				"date_of_application": today(),
				"invoice_attachment": "/files/invoice.pdf",
				**kwargs,
			}
		)
		residency.flags.ignore_permissions = True
		residency.insert()
		residency.submit()
		return residency

	def _employee(self, fieldname):
		return frappe.db.get_value("Employee", self.employee, fieldname)

	def test_extension_writes_the_date_and_leaves_residency_expiry_alone(self):
		residency_expiry_date = self._employee("residency_expiry_date")
		for i, action in enumerate(RESIDENCY_ONLY_ACTIONS):
			extension_date = add_days(today(), 30 + i)
			self._submit("Extend", action, visa_extension_expiry_date=extension_date)
			self.assertEqual(self._employee(FIELD), getdate(extension_date), action)
			self.assertEqual(self._employee("residency_expiry_date"), residency_expiry_date, action)

	def test_renewal_expat_clears_the_date_and_writes_residency_expiry(self):
		# A non-Extend Residency takes its new expiry from the Employee's work permit expiry.
		new_expiry = add_days(today(), 365)
		frappe.db.set_value(
			"Employee",
			self.employee,
			{FIELD: add_days(today(), 30), "work_permit_expiry_date": new_expiry},
		)
		self._submit("Renewal", "Renewal Expat")
		self.assertIsNone(self._employee(FIELD))
		self.assertEqual(self._employee("residency_expiry_date"), getdate(new_expiry))

	def test_cancellation_with_category_extend_leaves_the_date_alone(self):
		extension_date = getdate(add_days(today(), 30))
		frappe.db.set_value("Employee", self.employee, FIELD, extension_date)
		residency = frappe.new_doc("Residency")
		residency.update(
			{"employee": self.employee, "category": "Extend", "renewal_or_extend": "Cancellation"}
		)
		residency.sync_visa_extension_expiry_date()
		self.assertEqual(self._employee(FIELD), extension_date)
