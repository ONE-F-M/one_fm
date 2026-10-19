# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-003718: backfill Onboard Employee.last_name_in_arabic from the linked Employee."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.backfill_onboard_employee_last_name_in_arabic import (
	EMPLOYEE_FIELD,
	ONBOARD_FIELD,
	execute,
)

OLD_MODIFIED = "2020-01-01 10:00:00.000000"


def _insert(doctype, name, **values):
	"""Insert only the named columns straight into the table - no hooks, no mandatory
	checks, no dependence on unrelated columns - so each case is exactly the data shape
	under test. FrappeTestCase rolls it back."""
	row = {
		"name": name,
		"owner": "Administrator",
		"modified_by": "Administrator",
		"creation": OLD_MODIFIED,
		"modified": OLD_MODIFIED,
		**values,
	}
	table = frappe.qb.DocType(doctype)
	frappe.qb.into(table).columns(*row.keys()).insert(*row.values()).run()
	return name


class TestBackfillOnboardEmployeeLastNameInArabic(FrappeTestCase):
	def setUp(self):
		self.emp_with = _insert(
			"Employee", "WI3718-EMP-1", employee_name="With Arabic", **{EMPLOYEE_FIELD: "الأول"}
		)
		self.emp_other = _insert(
			"Employee", "WI3718-EMP-2", employee_name="Other Arabic", **{EMPLOYEE_FIELD: "الثاني"}
		)
		self.emp_without = _insert("Employee", "WI3718-EMP-3", employee_name="No Arabic")
		self.emp_blank = _insert(
			"Employee", "WI3718-EMP-4", employee_name="Blank Arabic", **{EMPLOYEE_FIELD: ""}
		)

		self.missing = _insert(
			"Onboard Employee",
			"WI3718-OE-MISSING",
			employee=self.emp_with,
			employee_name="Keep Me",
			first_name_in_arabic="اسم",
		)
		self.empty_string = _insert(
			"Onboard Employee",
			"WI3718-OE-EMPTY",
			employee=self.emp_with,
			**{ONBOARD_FIELD: ""},
		)
		self.populated = _insert(
			"Onboard Employee",
			"WI3718-OE-POPULATED",
			employee=self.emp_other,
			**{ONBOARD_FIELD: "موجود"},
		)
		self.no_employee = _insert("Onboard Employee", "WI3718-OE-NOEMP")
		self.blank_employee = _insert("Onboard Employee", "WI3718-OE-BLANKEMP", employee="")
		self.employee_no_arabic = _insert(
			"Onboard Employee", "WI3718-OE-NOARABIC", employee=self.emp_without
		)
		self.employee_blank_arabic = _insert(
			"Onboard Employee", "WI3718-OE-BLANKARABIC", employee=self.emp_blank
		)
		self.dangling = _insert(
			"Onboard Employee", "WI3718-OE-DANGLING", employee="WI3718-EMP-DOES-NOT-EXIST"
		)

	def _value(self, name):
		return frappe.db.get_value("Onboard Employee", name, ONBOARD_FIELD)

	def test_missing_value_is_filled_from_the_employee(self):
		execute()
		self.assertEqual(self._value(self.missing), "الأول")
		self.assertEqual(self._value(self.empty_string), "الأول")

	def test_existing_value_is_not_overwritten(self):
		execute()
		self.assertEqual(self._value(self.populated), "موجود")

	def test_record_without_employee_is_not_updated(self):
		execute()
		self.assertFalse(self._value(self.no_employee))
		self.assertFalse(self._value(self.blank_employee))

	def test_employee_without_arabic_last_name_leaves_record_unchanged(self):
		execute()
		self.assertFalse(self._value(self.employee_no_arabic))
		self.assertFalse(self._value(self.employee_blank_arabic))

	def test_missing_employee_record_is_skipped(self):
		execute()
		self.assertFalse(self._value(self.dangling))

	def test_unrelated_fields_and_modified_are_untouched(self):
		execute()
		row = frappe.db.get_value(
			"Onboard Employee",
			self.missing,
			["employee", "employee_name", "first_name_in_arabic", "modified", "modified_by"],
			as_dict=True,
		)
		self.assertEqual(row.employee, self.emp_with)
		self.assertEqual(row.employee_name, "Keep Me")
		self.assertEqual(row.first_name_in_arabic, "اسم")
		self.assertEqual(str(row.modified), OLD_MODIFIED)
		self.assertEqual(row.modified_by, "Administrator")

	def test_only_the_intended_records_are_written(self):
		before = {
			name: frappe.db.get_value("Onboard Employee", name, ONBOARD_FIELD)
			for name in (
				self.populated,
				self.no_employee,
				self.blank_employee,
				self.employee_no_arabic,
				self.employee_blank_arabic,
				self.dangling,
			)
		}
		execute()
		after = {name: self._value(name) for name in before}
		self.assertEqual(before, after)

	def test_running_twice_is_harmless(self):
		execute()
		execute()
		self.assertEqual(self._value(self.missing), "الأول")
		self.assertEqual(self._value(self.populated), "موجود")


class TestPatchIsRegistered(FrappeTestCase):
	def test_registered_in_post_model_sync(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		entry = "one_fm.patches.v15_0.backfill_onboard_employee_last_name_in_arabic"
		pre, post = patches.split("[post_model_sync]")
		self.assertNotIn(entry, pre)
		self.assertIn(entry, post)
