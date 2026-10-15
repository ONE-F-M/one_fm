# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-003410: Payment Date on Work Permit, Medical Insurance, Residency and PACI, and the
legacy "Upload Payment Invoice On" stamps it replaces."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime, nowdate

from one_fm.grd.doctype.paci.paci import (
	create_PACI,
	notify_operator_to_take_hawiyati_renewal,
	notify_operator_to_take_hawiyati_transfer,
	reapply_paci,
)
from one_fm.grd.doctype.preparation.preparation import create_documents_for_row
from one_fm.grd.doctype.work_permit.work_permit import reapply_work_permit

DOCTYPES = ("Work Permit", "Medical Insurance", "Residency", "PACI")

# The five stamps removed by this work item. Work Permit lost two.
LEGACY_FIELDS = {
	"Work Permit": ("upload_payment_invoice_on", "datetime_17"),
	"Medical Insurance": ("upload_payment_invoice_on",),
	"Residency": ("invoice_attachment_date",),
	"PACI": ("upload_civil_id_payment_datetime",),
}


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"], "residency_expiry_date": ["is", "set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestPaymentDateMeta(FrappeTestCase):
	def test_payment_date_is_an_editable_datetime_on_all_four(self):
		for doctype in DOCTYPES:
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("payment_date")
				self.assertIsNotNone(field, f"{doctype} has no Payment Date field")
				self.assertEqual(field.fieldtype, "Datetime")
				self.assertEqual(field.label, "Payment Date")
				self.assertFalse(field.read_only)
				self.assertEqual(field.permlevel or 0, 0)

	def test_the_legacy_stamps_are_gone_from_meta(self):
		for doctype, fieldnames in LEGACY_FIELDS.items():
			meta = frappe.get_meta(doctype)
			for fieldname in fieldnames:
				with self.subTest(doctype=doctype, fieldname=fieldname):
					self.assertIsNone(meta.get_field(fieldname))

	def test_medical_insurance_keeps_its_upload_on_stamp(self):
		self.assertIsNotNone(frappe.get_meta("Medical Insurance").get_field("upload_medical_insurance_date"))

	def test_no_payment_reference_number_was_added(self):
		for doctype in DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertIsNone(frappe.get_meta(doctype).get_field("payment_reference_number"))


class TestHawiyatiRemindersReadPaymentDate(FrappeTestCase):
	"""The 05:40 cron selects the column by name, so it fails if the old one is gone."""

	def test_renewal_reminder_does_not_raise(self):
		with patch("one_fm.grd.doctype.paci.paci.is_scheduler_emails_enabled", return_value=False):
			notify_operator_to_take_hawiyati_renewal()

	def test_transfer_reminder_does_not_raise(self):
		with patch("one_fm.grd.doctype.paci.paci.is_scheduler_emails_enabled", return_value=False):
			notify_operator_to_take_hawiyati_transfer()


class TestReapplyClearsPaymentDate(FrappeTestCase):
	def test_a_reapplied_paci_has_no_payment_date(self):
		employee = frappe.get_doc("Employee", _an_active_employee())
		paci = create_PACI(employee, "Renewal")
		paci.db_set("workflow_state", "Rejected")
		paci.db_set("payment_date", now_datetime())
		paci.reload()
		self.assertTrue(paci.payment_date)

		new_name = reapply_paci(paci.name)["name"]

		self.assertNotEqual(new_name, paci.name)
		self.assertFalse(frappe.db.get_value("PACI", new_name, "payment_date"))

	def test_a_reapplied_work_permit_has_no_payment_date(self):
		employee = _an_active_employee()
		preparation = frappe.get_doc({
			"doctype": "Preparation",
			"category": "Onboarding",
			"posting_date": nowdate(),
			"preparation_record": [{"employee": employee, "renewal_or_extend": "Local Transfer"}],
		})
		preparation.flags.ignore_permissions = True
		preparation.insert()
		permit = create_documents_for_row(preparation.preparation_record[0], preparation.name)
		permit.db_set("workflow_state", "Rejected")
		permit.db_set("payment_date", now_datetime())
		permit.reload()
		self.assertTrue(permit.payment_date)

		new_name = reapply_work_permit(permit.name)["name"]

		self.assertNotEqual(new_name, permit.name)
		self.assertFalse(frappe.db.get_value("Work Permit", new_name, "payment_date"))
