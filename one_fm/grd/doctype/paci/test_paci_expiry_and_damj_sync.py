# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002100: expiry dates carried down from the Work Permit, and the Damj write-back."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from one_fm.grd.doctype.preparation.preparation import create_documents_for_row

A_LETTER = "/files/damj-letter.pdf"
MERGED_CIVIL_ID = "299010101010"


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestExpirySyncFromWorkPermit(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.preparation = self._a_preparation()

	def _a_preparation(self):
		preparation = frappe.get_doc({
			"doctype": "Preparation",
			"category": "Onboarding",
			"posting_date": nowdate(),
			"preparation_record": [{"employee": self.employee, "renewal_or_extend": "Overseas"}],
		})
		preparation.flags.ignore_permissions = True
		preparation.insert()
		create_documents_for_row(preparation.preparation_record[0], preparation.name)
		return preparation

	def _linked(self, doctype):
		return frappe.get_last_doc(doctype, filters={"preparation": self.preparation.name})

	def test_a_new_expiry_reaches_the_residency_and_the_paci(self):
		expiry = add_days(nowdate(), 365)
		work_permit = self._linked("Work Permit")

		work_permit.sync_expiry_dates_to_linked_documents(expiry)

		self.assertEqual(str(self._linked("Residency").new_residency_expiry_date), expiry)
		self.assertEqual(str(self._linked("PACI").new_civil_id_expiry_date), expiry)

	def test_a_correction_reaches_them_too(self):
		"""Both read the date off the Employee once, when they are opened, so a later
		correction would otherwise never arrive."""
		work_permit = self._linked("Work Permit")
		work_permit.sync_expiry_dates_to_linked_documents(add_days(nowdate(), 365))

		corrected = add_days(nowdate(), 730)
		work_permit.sync_expiry_dates_to_linked_documents(corrected)

		self.assertEqual(str(self._linked("Residency").new_residency_expiry_date), corrected)
		self.assertEqual(str(self._linked("PACI").new_civil_id_expiry_date), corrected)

	def test_no_expiry_date_changes_nothing(self):
		work_permit = self._linked("Work Permit")
		work_permit.sync_expiry_dates_to_linked_documents(add_days(nowdate(), 365))
		before = self._linked("PACI").new_civil_id_expiry_date

		work_permit.sync_expiry_dates_to_linked_documents(None)

		self.assertEqual(self._linked("PACI").new_civil_id_expiry_date, before)

	def test_a_permit_with_no_preparation_has_nothing_to_pair_with(self):
		work_permit = self._linked("Work Permit")
		before = self._linked("PACI").new_civil_id_expiry_date
		work_permit.preparation = None

		work_permit.sync_expiry_dates_to_linked_documents(add_days(nowdate(), 365))

		self.assertEqual(self._linked("PACI").new_civil_id_expiry_date, before)


class TestPACIDamjWriteBack(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.before = frappe.db.get_value("Employee", self.employee, "one_fm_civil_id")

	def tearDown(self):
		frappe.db.set_value("Employee", self.employee, "one_fm_civil_id", self.before, update_modified=False)

	def _a_completed_paci(self, **kwargs):
		paci = frappe.get_doc({
			"doctype": "PACI",
			"employee": self.employee,
			"category": "Renewal",
			"date_of_application": nowdate(),
			"new_civil_id_expiry_date": add_days(nowdate(), 365),
			**kwargs,
		})
		paci.flags.ignore_permissions = True
		paci.insert()
		paci.db_set("workflow_state", "Completed")
		paci.reload()
		paci.submit()
		return paci

	def test_completing_a_damj_puts_the_merged_number_on_the_employee(self):
		self._a_completed_paci(
			damj_is_applicable=1, original_civil_id=MERGED_CIVIL_ID, upload_damj_letter=A_LETTER
		)

		self.assertEqual(
			frappe.db.get_value("Employee", self.employee, "one_fm_civil_id"), MERGED_CIVIL_ID
		)

	def test_the_record_stops_quoting_the_retired_number(self):
		paci = self._a_completed_paci(
			damj_is_applicable=1, original_civil_id=MERGED_CIVIL_ID, upload_damj_letter=A_LETTER
		)

		paci.reload()
		self.assertEqual(paci.civil_id, MERGED_CIVIL_ID)

	def test_a_completion_with_no_damj_leaves_the_employee_alone(self):
		self._a_completed_paci()

		self.assertEqual(
			frappe.db.get_value("Employee", self.employee, "one_fm_civil_id"), self.before
		)
