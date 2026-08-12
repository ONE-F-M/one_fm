# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002023: the PACI fine follows the master rate in HR Settings."""

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import today

MASTER_RATE = 20.0


def _an_active_employee():
	name = frappe.db.get_value("Employee", {"status": "Active"}, "name", order_by="creation asc")
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestPaciFine(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()

	def _paci(self, **kwargs):
		paci = frappe.get_doc(
			{
				"doctype": "PACI",
				"employee": self.employee,
				"category": "New Application",
				"date_of_application": today(),
				**kwargs,
			}
		)
		paci.flags.ignore_permissions = True
		paci.insert()
		return paci

	@change_settings("HR Settings", {"paci_fine_amount_kwd": MASTER_RATE})
	def test_ticking_the_box_fetches_the_master_rate(self):
		paci = self._paci(is_paci_fine_applicable=1)
		self.assertEqual(paci.paci_fine_amount_kwd, MASTER_RATE)

	@change_settings("HR Settings", {"paci_fine_amount_kwd": MASTER_RATE})
	def test_an_unticked_record_carries_no_fine(self):
		paci = self._paci()
		self.assertEqual(paci.paci_fine_amount_kwd, 0)

	@change_settings("HR Settings", {"paci_fine_amount_kwd": MASTER_RATE})
	def test_unticking_clears_a_populated_amount(self):
		paci = self._paci(is_paci_fine_applicable=1)
		self.assertEqual(paci.paci_fine_amount_kwd, MASTER_RATE)

		paci.is_paci_fine_applicable = 0
		paci.save()

		# The field is hidden once unticked, so a stale amount would be invisible and
		# still reach the costing.
		self.assertEqual(paci.paci_fine_amount_kwd, 0)

	@change_settings("HR Settings", {"paci_fine_amount_kwd": MASTER_RATE})
	def test_a_hand_typed_amount_is_replaced_by_the_master_rate(self):
		paci = self._paci(is_paci_fine_applicable=1, paci_fine_amount_kwd=999)
		self.assertEqual(paci.paci_fine_amount_kwd, MASTER_RATE)

	@change_settings("HR Settings", {"paci_fine_amount_kwd": 0})
	def test_an_unconfigured_master_rate_yields_zero_rather_than_none(self):
		paci = self._paci(is_paci_fine_applicable=1)
		self.assertEqual(paci.paci_fine_amount_kwd, 0)

	@change_settings("HR Settings", {"paci_fine_amount_kwd": 25.5})
	def test_a_changed_master_rate_is_picked_up_on_the_next_save(self):
		paci = self._paci(is_paci_fine_applicable=1)
		self.assertEqual(paci.paci_fine_amount_kwd, 25.5)
