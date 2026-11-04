# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Payment Made Via and Bank Account on Work Permit, Residency, Medical Insurance and PACI
(WI-004415). Meta-only: these are optional, receipt-gated fields."""

import frappe
from frappe.tests.utils import FrappeTestCase

# The attached receipt/invoice that reveals Payment Made Via on each DocType.
RECEIPT_FIELD = {
	"Work Permit": "attach_invoice",
	"Residency": "invoice_attachment",
	"Medical Insurance": "upload_medical_insurance",
	"PACI": "upload_civil_id_payment",
}

BANK_ACCOUNT_DEPENDS_ON = 'eval:doc.payment_made_via == "Card" || doc.payment_made_via == "Bank"'


class TestPaymentMadeViaMeta(FrappeTestCase):
	def test_payment_made_via_is_an_optional_bank_or_cash_select(self):
		for doctype in RECEIPT_FIELD:
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("payment_made_via")
				self.assertIsNotNone(field, f"{doctype} has no Payment Made Via field")
				self.assertEqual(field.fieldtype, "Select")
				self.assertEqual(field.label, "Payment Made Via")
				self.assertEqual([o for o in (field.options or "").split("\n") if o], ["Bank", "Cash"])
				self.assertFalse(field.reqd)
				self.assertFalse(field.mandatory_depends_on)

	def test_bank_account_is_an_optional_link_to_bank_account(self):
		for doctype in RECEIPT_FIELD:
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("bank_account")
				self.assertIsNotNone(field, f"{doctype} has no Bank Account field")
				self.assertEqual(field.fieldtype, "Link")
				self.assertEqual(field.options, "Bank Account")
				self.assertFalse(field.reqd)
				self.assertFalse(field.mandatory_depends_on)

	def test_payment_made_via_shows_once_a_receipt_is_attached(self):
		for doctype, receipt in RECEIPT_FIELD.items():
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("payment_made_via")
				self.assertEqual(field.depends_on, f"eval:doc.{receipt}")
				self.assertFalse(field.hidden)

	def test_bank_account_shows_only_for_bank(self):
		for doctype in RECEIPT_FIELD:
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("bank_account")
				self.assertEqual(field.depends_on, BANK_ACCOUNT_DEPENDS_ON)
				self.assertFalse(field.hidden)

	def test_payment_fields_sit_after_payment_date(self):
		for doctype in RECEIPT_FIELD:
			with self.subTest(doctype=doctype):
				order = [df.fieldname for df in frappe.get_meta(doctype).fields]
				start = order.index("payment_date")
				self.assertEqual(order[start + 1 : start + 3], ["payment_made_via", "bank_account"])
