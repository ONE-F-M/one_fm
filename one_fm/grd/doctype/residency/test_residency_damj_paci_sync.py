# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002027: a completed Damj carries the merged Civil ID to the PACI beside it."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

A_LETTER = "/files/damj-letter.pdf"
MERGED_CIVIL_ID = "299010177777"


def _an_active_employee():
	name = frappe.db.get_value("Employee", {"status": "Active"}, "name", order_by="creation asc")
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestDamjCivilIdSyncToPaci(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.original_civil_id = frappe.db.get_value("Employee", self.employee, "one_fm_civil_id")
		self.preparation = self._preparation()

	def _preparation(self):
		preparation = frappe.get_doc(
			{
				"doctype": "Preparation",
				"posting_date": today(),
				"preparation_record": [{"employee": self.employee, "renewal_or_extend": "Renewal (Non-Kuwaiti)"}],
			}
		)
		preparation.flags.ignore_permissions = True
		preparation.insert()
		return preparation.name

	def _paci(self, preparation):
		paci = frappe.get_doc(
			{
				"doctype": "PACI",
				"employee": self.employee,
				"category": "New Application",
				"date_of_application": today(),
				"preparation": preparation,
			}
		)
		paci.flags.ignore_permissions = True
		paci.insert()
		return paci

	def _completed_damj_residency(self, preparation, **kwargs):
		residency = frappe.get_doc(
			{
				"doctype": "Residency",
				"employee": self.employee,
				"category": "Renewal",
				"date_of_application": today(),
				"preparation": preparation,
				"damj_is_applicable": 1,
				"original_civil_id": MERGED_CIVIL_ID,
				"upload_damj_letter": A_LETTER,
				"invoice_attachment": "/files/invoice.pdf",
				"new_residency_expiry_date": today(),
				**kwargs,
			}
		)
		residency.flags.ignore_permissions = True
		residency.insert()
		residency.submit()
		return residency

	def test_the_paci_under_the_same_preparation_gets_the_merged_number(self):
		paci = self._paci(self.preparation)
		self.assertEqual(paci.civil_id, self.original_civil_id)

		self._completed_damj_residency(self.preparation)

		self.assertEqual(frappe.db.get_value("PACI", paci.name, "civil_id"), MERGED_CIVIL_ID)

	def test_every_live_paci_under_the_preparation_is_corrected(self):
		# A rejected application and its replacement both sit under the same Preparation.
		first = self._paci(self.preparation)
		second = self._paci(self.preparation)

		self._completed_damj_residency(self.preparation)

		for paci in (first, second):
			self.assertEqual(frappe.db.get_value("PACI", paci.name, "civil_id"), MERGED_CIVIL_ID)

	def test_a_paci_under_a_different_preparation_is_left_alone(self):
		other = self._paci(self._preparation())

		self._completed_damj_residency(self.preparation)

		self.assertEqual(frappe.db.get_value("PACI", other.name, "civil_id"), self.original_civil_id)

	def test_a_cancelled_paci_is_left_alone(self):
		paci = self._paci(self.preparation)
		paci.submit()
		paci.cancel()

		self._completed_damj_residency(self.preparation)

		self.assertEqual(frappe.db.get_value("PACI", paci.name, "civil_id"), self.original_civil_id)

	def test_a_residency_without_a_preparation_touches_no_paci(self):
		paci = self._paci(self.preparation)

		self._completed_damj_residency(None)

		self.assertEqual(frappe.db.get_value("PACI", paci.name, "civil_id"), self.original_civil_id)
		# The Employee is still corrected - that part does not depend on the pairing.
		self.assertEqual(
			frappe.db.get_value("Employee", self.employee, "one_fm_civil_id"), MERGED_CIVIL_ID
		)
