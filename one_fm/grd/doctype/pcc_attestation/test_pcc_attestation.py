# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002028: the PCC Attestation record, its employee details, fees and receipt stamps."""

import frappe
from frappe.tests.utils import FrappeTestCase

A_RECEIPT = "/files/receipt.pdf"
ATTESTING_COUNTRY = "Nepal"
NON_ATTESTING_COUNTRY = "India"
EMBASSY_FEE = 15.0


def _an_active_employee():
	name = frappe.db.get_value("Employee", {"status": "Active"}, "name", order_by="creation asc")
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestPCCAttestation(FrappeTestCase):
	def setUp(self):
		for country in (ATTESTING_COUNTRY, NON_ATTESTING_COUNTRY):
			if not frappe.db.exists("Country", country):
				self.skipTest(f"Country {country} is not on this site")

		self.employee = _an_active_employee()
		settings = frappe.get_doc("HR Settings")
		settings.set("embassy_attestation_rates", [])
		settings.append(
			"embassy_attestation_rates",
			{"country": ATTESTING_COUNTRY, "embassy_fee_kwd": EMBASSY_FEE},
		)
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_cache(doctype="HR Settings")

	def _pcc(self, born_in=None, **kwargs):
		"""A PCC Attestation for the test employee, optionally born in a given country.

		The country is set on the Employee, not on the record: place_of_birth is fetched from
		employee.one_fm_place_of_birth, and Frappe applies fetch_from before validate runs, so
		a value passed here would be overwritten before the controller ever saw it. Which is
		the behaviour we want - the country is the Employee's fact, not the operator's.
		"""
		if born_in is not None:
			frappe.db.set_value("Employee", self.employee, "one_fm_place_of_birth", born_in)

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

	def test_an_attesting_country_gets_its_embassy_fee(self):
		pcc = self._pcc(born_in=ATTESTING_COUNTRY)
		self.assertEqual(pcc.place_of_birth, ATTESTING_COUNTRY)
		self.assertEqual(pcc.requires_embassy_attestation, EMBASSY_FEE)
		self.assertTrue(pcc.needs_embassy_attestation)

	def test_the_country_comes_from_the_employee_not_the_operator(self):
		# place_of_birth is fetched from the Employee, so an operator cannot talk the record
		# into an embassy fee the candidate is not entitled to by typing a country in.
		pcc = self._pcc(born_in=NON_ATTESTING_COUNTRY, place_of_birth=ATTESTING_COUNTRY)

		self.assertEqual(pcc.place_of_birth, NON_ATTESTING_COUNTRY)
		self.assertEqual(pcc.requires_embassy_attestation, 0)

	def test_a_country_not_in_the_table_needs_no_embassy_step(self):
		pcc = self._pcc(born_in=NON_ATTESTING_COUNTRY)
		self.assertEqual(pcc.requires_embassy_attestation, 0)
		self.assertFalse(pcc.needs_embassy_attestation)

	def test_translation_work_never_carries_an_embassy_fee(self):
		pcc = self._pcc(born_in=ATTESTING_COUNTRY, type="Translation")
		self.assertEqual(pcc.requires_embassy_attestation, 0)
		self.assertFalse(pcc.needs_embassy_attestation)

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
