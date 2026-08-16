# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002028: the PCC Attestation record, its employee details, fees and receipt stamps."""

import frappe
from frappe.tests.utils import FrappeTestCase

A_RECEIPT = "/files/receipt.pdf"

# From the reporter's master data. Nepali needs all of embassy and MOFA; Indian needs MOFA
# only; Ugandan needs neither, translation only - the row the earlier shape could not
# represent, and the reason the requirements are three separate flags.
EMBASSY_AND_MOFA = "Nepali"
MOFA_ONLY = "Indian"
NEITHER = "Ugandan"
EMBASSY_FEE = 16.0
MOFA_FEE = 5.0


def _an_active_employee():
	name = frappe.db.get_value("Employee", {"status": "Active"}, "name", order_by="creation asc")
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestPCCAttestation(FrappeTestCase):
	def setUp(self):
		for nationality in (EMBASSY_AND_MOFA, MOFA_ONLY, NEITHER):
			if not frappe.db.exists("Nationality", nationality):
				self.skipTest(f"Nationality {nationality} is not on this site")

		self.employee = _an_active_employee()
		settings = frappe.get_doc("HR Settings")
		settings.set("nationality_attestation_rules", [])
		settings.append("nationality_attestation_rules", {
			"nationality": EMBASSY_AND_MOFA,
			"embassy_required": 1, "embassy_fee_kwd": EMBASSY_FEE,
			"mofa_required": 1, "mofa_fee_kwd": MOFA_FEE,
			"translation_required": 0,
		})
		settings.append("nationality_attestation_rules", {
			"nationality": MOFA_ONLY,
			"embassy_required": 0,
			"mofa_required": 1, "mofa_fee_kwd": MOFA_FEE,
			"translation_required": 0,
		})
		settings.append("nationality_attestation_rules", {
			"nationality": NEITHER,
			"embassy_required": 0, "mofa_required": 0, "translation_required": 1,
		})
		settings.mofa_fee_kwd = MOFA_FEE
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_cache(doctype="HR Settings")

	def _pcc(self, nationality=None, **kwargs):
		"""A PCC Attestation for the test employee, optionally of a given nationality.

		The nationality is set on the Employee, not on the record: PCC Attestation.nationality
		is fetched from employee.one_fm_nationality, and Frappe applies fetch_from before
		validate runs, so a value passed here would be overwritten before the controller ever
		saw it. Which is the behaviour we want - the nationality is the Employee's fact, not
		the operator's.
		"""
		if nationality is not None:
			frappe.db.set_value("Employee", self.employee, "one_fm_nationality", nationality)

		pcc = frappe.get_doc(
			{
				"doctype": "PCC Attestation",
				"employee": self.employee,
				"type": "Attestation",
				**kwargs,
			}
		)
		pcc.flags.ignore_permissions = True
		pcc.insert()
		return pcc

	def test_selecting_an_employee_populates_the_read_only_details(self):
		pcc = self._pcc()

		employee = frappe.get_doc("Employee", self.employee)
		self.assertEqual(pcc.employee_name, employee.employee_name)
		self.assertEqual(pcc.employee_id, employee.employee_id)
		self.assertEqual(pcc.one_fm_civil_id, employee.one_fm_civil_id)
		self.assertEqual(pcc.nationality, employee.one_fm_nationality)
		self.assertEqual(pcc.passport_number, employee.passport_number)
		self.assertEqual(pcc.company_pam_file_number, employee.pam_file_number)

	def test_a_nationality_needing_embassy_and_mofa_gets_both_fees(self):
		pcc = self._pcc(nationality=EMBASSY_AND_MOFA)

		self.assertEqual(pcc.nationality, EMBASSY_AND_MOFA)
		self.assertTrue(pcc.embassy_attestation_required)
		self.assertEqual(pcc.requires_embassy_attestation, EMBASSY_FEE)
		self.assertTrue(pcc.mofa_attestation_required)
		self.assertEqual(pcc.mofa_fee, MOFA_FEE)
		self.assertTrue(pcc.needs_embassy_attestation)
		self.assertTrue(pcc.needs_mofa_attestation)

	def test_a_mofa_only_nationality_skips_the_embassy(self):
		pcc = self._pcc(nationality=MOFA_ONLY)

		self.assertFalse(pcc.embassy_attestation_required)
		self.assertEqual(pcc.requires_embassy_attestation, 0)
		self.assertTrue(pcc.mofa_attestation_required)
		self.assertEqual(pcc.mofa_fee, MOFA_FEE)
		self.assertFalse(pcc.needs_embassy_attestation)
		self.assertTrue(pcc.needs_mofa_attestation)

	def test_a_nationality_needing_neither_step(self):
		# Ugandan. Under the earlier shape this routed to Pending MOFA and blocked the PRO on
		# a receipt that was never going to exist.
		pcc = self._pcc(nationality=NEITHER)

		self.assertFalse(pcc.embassy_attestation_required)
		self.assertFalse(pcc.mofa_attestation_required)
		self.assertFalse(pcc.needs_embassy_attestation)
		self.assertFalse(pcc.needs_mofa_attestation)
		self.assertEqual([pcc.requires_embassy_attestation, pcc.mofa_fee], [0, 0])

	def test_the_translation_flag_comes_from_the_nationality(self):
		self.assertTrue(self._pcc(nationality=NEITHER).translation_required)
		self.assertFalse(self._pcc(nationality=MOFA_ONLY).translation_required)

	def test_the_nationality_comes_from_the_employee_not_the_operator(self):
		# An operator cannot talk the record into an embassy fee the candidate is not entitled
		# to by typing a nationality in.
		pcc = self._pcc(nationality=MOFA_ONLY)
		self.assertEqual(pcc.nationality, MOFA_ONLY)
		self.assertEqual(pcc.requires_embassy_attestation, 0)

	def test_an_unlisted_nationality_needs_nothing(self):
		unlisted = frappe.db.get_value(
			"Nationality",
			{"name": ["not in", [EMBASSY_AND_MOFA, MOFA_ONLY, NEITHER]]},
			"name",
			order_by="name asc",
		)
		if not unlisted:
			self.skipTest("No unlisted Nationality on this site")

		pcc = self._pcc(nationality=unlisted)

		self.assertFalse(pcc.embassy_attestation_required)
		self.assertFalse(pcc.mofa_attestation_required)
		self.assertFalse(pcc.translation_required)

	def test_translation_work_never_carries_an_embassy_or_mofa_fee(self):
		pcc = self._pcc(nationality=EMBASSY_AND_MOFA, type="Translation")

		self.assertEqual(pcc.requires_embassy_attestation, 0)
		self.assertEqual(pcc.mofa_fee, 0)
		self.assertFalse(pcc.needs_embassy_attestation)
		self.assertFalse(pcc.needs_mofa_attestation)

	def test_attaching_a_receipt_stamps_its_timestamp(self):
		pcc = self._pcc(upload_mofa_payment_receipt=A_RECEIPT)
		self.assertTrue(pcc.upload_mofa_payment_receipt_on)

	def test_removing_a_receipt_clears_its_timestamp(self):
		pcc = self._pcc(upload_mofa_payment_receipt=A_RECEIPT)
		self.assertTrue(pcc.upload_mofa_payment_receipt_on)

		pcc.upload_mofa_payment_receipt = None
		pcc.save()

		self.assertIsNone(pcc.upload_mofa_payment_receipt_on)

	def test_each_receipt_stamps_only_its_own_timestamp(self):
		pcc = self._pcc(upload_embassy_payment_receipt=A_RECEIPT)

		self.assertTrue(pcc.upload_embassy_payment_receipt_on)
		self.assertFalse(pcc.upload_mofa_payment_receipt_on)
		self.assertFalse(pcc.upload_translation_payment_receipt_on)

	def test_an_existing_stamp_is_not_overwritten_on_a_later_save(self):
		pcc = self._pcc(upload_mofa_payment_receipt=A_RECEIPT)
		stamped_at = pcc.upload_mofa_payment_receipt_on

		pcc.category = "Overseas"
		pcc.save()

		self.assertEqual(pcc.upload_mofa_payment_receipt_on, stamped_at)

	def test_every_stamped_pair_of_fields_exists(self):
		from one_fm.grd.doctype.pcc_attestation.pcc_attestation import RECEIPT_TIMESTAMPS

		meta = frappe.get_meta("PCC Attestation")
		for receipt_field, timestamp_field in RECEIPT_TIMESTAMPS:
			self.assertTrue(meta.get_field(receipt_field), f"no field {receipt_field}")
			self.assertTrue(meta.get_field(timestamp_field), f"no field {timestamp_field}")

	def test_it_is_not_the_recruitment_side_pcc_record(self):
		# PCC Clearance already exists and tracks obtaining the certificate for a candidate
		# abroad. This doctype is about attesting an employee's certificate once it is here.
		self.assertTrue(frappe.db.exists("DocType", "PCC Clearance"))
		self.assertEqual(frappe.get_meta("PCC Attestation").get_field("employee").options, "Employee")
