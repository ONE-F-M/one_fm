# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-003915: creating an Employee no longer ticks Under Company Residency.

The flag used to be switched on in a before_insert hook for every non-Kuwaiti,
non-Subcontractor Employee. It is now only set by a person or by the Work Permit flow.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today


class TestResidencyNotAutoTicked(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.company = frappe.db.get_value("Company", {"is_group": 0}, "name")
		if not self.company:
			self.skipTest("no Company on this site")

	def _insert(self, nationality=None, employment_type=None, **extra):
		doc = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": "Residency Default Test",
				"employee_name": "Residency Default Test",
				"one_fm_first_name_in_arabic": "اختبار",
				"one_fm_last_name_in_arabic": "إقامة",
				"status": "Active",
				"date_of_birth": "1990-01-01",
				"date_of_joining": add_days(today(), -365),
				"gender": "Male",
				"company": self.company,
				"one_fm_basic_salary": 100,
				"day_off_category": "Weekly",
				"number_of_days_off": 1,
				"create_user_permission": 0,
				"one_fm_nationality": nationality,
				"employment_type": employment_type,
				**extra,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def _nationality(self, kuwaiti):
		name = frappe.db.exists("Nationality", "Kuwaiti") if kuwaiti else None
		if kuwaiti:
			if not name:
				self.skipTest("no Kuwaiti Nationality on this site")
			return name
		other = frappe.db.get_value("Nationality", {"name": ["!=", "Kuwaiti"]}, "name")
		if not other:
			self.skipTest("no non-Kuwaiti Nationality on this site")
		return other

	def _stored(self, doc):
		return frappe.db.get_value("Employee", doc.name, "under_company_residency")

	def test_non_kuwaiti_is_created_unticked(self):
		doc = self._insert(nationality=self._nationality(kuwaiti=False))
		self.assertEqual(doc.under_company_residency or 0, 0)
		self.assertEqual(self._stored(doc) or 0, 0)

	def test_kuwaiti_is_created_unticked(self):
		doc = self._insert(nationality=self._nationality(kuwaiti=True))
		self.assertEqual(self._stored(doc) or 0, 0)

	def test_subcontractor_is_created_unticked(self):
		if not frappe.db.exists("Employment Type", "Subcontractor"):
			self.skipTest("no Subcontractor Employment Type on this site")
		doc = self._insert(
			nationality=self._nationality(kuwaiti=False), employment_type="Subcontractor"
		)
		self.assertEqual(self._stored(doc) or 0, 0)

	def test_a_manual_tick_on_creation_is_kept(self):
		doc = self._insert(
			nationality=self._nationality(kuwaiti=False), under_company_residency=1
		)
		self.assertEqual(self._stored(doc), 1)


class TestTheHookIsGone(FrappeTestCase):
	def test_both_modules_import_and_the_hook_is_removed(self):
		import one_fm.hiring.utils as hiring_utils
		import one_fm.overrides.employee as employee_override

		self.assertFalse(hasattr(hiring_utils, "employee_before_insert"))
		self.assertNotIn("before_insert", vars(employee_override.EmployeeOverride))
