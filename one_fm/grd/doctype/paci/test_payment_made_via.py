# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Payment Made Via and Bank Account on the GRD DocTypes."""

import frappe
from frappe.tests.utils import FrappeTestCase

BANK_ACCOUNT_DEPENDS_ON = 'eval:doc.payment_made_via == "Card" || doc.payment_made_via == "Bank"'

# doctype: (receipt that reveals Payment Made Via, field before it, field before Bank Account)
SINGLE_STREAM = {
	"Work Permit": ("attach_invoice", "attach_invoice", "payment_date"),
	"Residency": ("invoice_attachment", "visa_extension_expiry_date", "payment_made_via"),
	"Medical Insurance": ("upload_medical_insurance", "medical_insurance_submitted_by", "payment_made_via"),
	"Medical Appointment": ("payment_invoice", "payment_invoice", "payment_date"),
	"PACI": ("upload_civil_id_payment", "pro_user", "payment_made_via"),
}

PCC_STREAMS = {
	"embassy": "upload_embassy_payment_receipt",
	"mofa": "upload_mofa_payment_receipt",
	"translation": "upload_translation_payment_receipt",
}
PCC_ORDER = [
	"translation_payment_date",
	"column_break_opsr",
	"embassy_payment_made_via",
	"mofa_payment_made_via",
	"translation_payment_made_via",
	"column_break_slhv",
	"embassy_payment_bank_account",
	"mofa_payment_bank_account",
	"translation_payment_bank_account",
]


def _order(doctype):
	return [df.fieldname for df in frappe.get_meta(doctype).fields]


class TestPaymentMadeViaMeta(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for doctype in [*SINGLE_STREAM, "PCC Attestation"]:
			frappe.reload_doc("grd", "doctype", frappe.scrub(doctype))

	def assert_method_field(self, field, label, depends_on):
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Select")
		self.assertEqual(field.label, label)
		self.assertEqual(field.options, "\nBank\nCash")
		self.assertEqual(field.depends_on, depends_on)
		self.assert_optional(field)

	def assert_account_field(self, field, label, depends_on):
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.label, label)
		self.assertEqual(field.options, "Bank Account")
		self.assertEqual(field.depends_on, depends_on)
		self.assert_optional(field)

	def assert_optional(self, field):
		self.assertFalse(field.reqd)
		self.assertFalse(field.mandatory_depends_on)
		self.assertFalse(field.read_only)
		self.assertFalse(field.hidden)
		self.assertFalse(field.allow_on_submit)

	def test_single_stream_fields(self):
		for doctype, (receipt, method_after, account_after) in SINGLE_STREAM.items():
			with self.subTest(doctype=doctype):
				meta = frappe.get_meta(doctype)
				self.assert_method_field(meta.get_field("payment_made_via"), "Payment Made Via", f"eval:doc.{receipt}")
				self.assert_account_field(meta.get_field("bank_account"), "Bank Account", BANK_ACCOUNT_DEPENDS_ON)
				order = _order(doctype)
				self.assertEqual(order[order.index(method_after) + 1], "payment_made_via")
				self.assertEqual(order[order.index(account_after) + 1], "bank_account")

	def test_pcc_streams_are_independent(self):
		meta = frappe.get_meta("PCC Attestation")
		for stream, receipt in PCC_STREAMS.items():
			with self.subTest(stream=stream):
				title = "MOFA" if stream == "mofa" else stream.title()
				self.assert_method_field(
					meta.get_field(f"{stream}_payment_made_via"),
					f"{title} Payment Made Via",
					f"eval:doc.{receipt}",
				)
				self.assert_account_field(
					meta.get_field(f"{stream}_payment_bank_account"),
					f"{title} Payment Bank Account",
					f"eval:doc.{stream}_payment_made_via == 'Bank'",
				)
				self.assertEqual(meta.get_field(f"{stream}_payment_date").depends_on, f"eval:doc.{receipt}")

	def test_pcc_field_order(self):
		order = _order("PCC Attestation")
		start = order.index("translation_payment_date")
		self.assertEqual(order[start : start + len(PCC_ORDER)], PCC_ORDER)


class TestPaymentMadeViaIsOptional(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.reload_doc("grd", "doctype", "medical_appointment")
		frappe.reload_doc("grd", "doctype", "pcc_attestation")
		cls.bank_account = frappe.db.get_value("Bank Account", {}, "name")

	def test_bank_and_account_are_retained(self):
		appointment = frappe.new_doc("Medical Appointment")
		appointment.payment_made_via = "Bank"
		appointment.bank_account = self.bank_account
		appointment.insert(ignore_permissions=True, ignore_mandatory=True)
		appointment.reload()
		self.assertEqual(appointment.payment_made_via, "Bank")
		self.assertEqual(appointment.bank_account, self.bank_account)

	def test_pcc_saves_with_a_receipt_and_no_payment_details(self):
		pcc = frappe.new_doc("PCC Attestation")
		pcc.upload_mofa_payment_receipt = "/files/receipt.pdf"
		pcc.insert(ignore_permissions=True, ignore_mandatory=True)
		pcc.reload()
		self.assertFalse(pcc.mofa_payment_made_via)
		self.assertFalse(pcc.mofa_payment_bank_account)
