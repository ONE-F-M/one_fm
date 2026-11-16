# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A fresh install must create every one_fm Employee custom field.

ERPNext ships `iban` as a standard Employee field. one_fm's Employee list also defined it, and CustomField.validate throws
"A field with the name iban already exists" for a name that collides with a standard field. create_custom_fields stopped there, so the
fields after it (shift_working, custom_is_rambo_reliever and the rest) were never created, and the rows saved before it got no columns
because updatedb is skipped when the call raises. Production only worked because an Employee-iban Custom Field row already existed.
"""

from unittest.mock import call, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.custom_field.employee import get_employee_custom_fields
from one_fm.setup import setup


def _employee_fields():
	return get_employee_custom_fields()["Employee"]


class TestEmployeeCustomFieldsOnFreshInstall(FrappeTestCase):
	def test_no_employee_custom_field_redefines_a_standard_employee_field(self):
		standard = {df.fieldname for df in frappe.get_doc("DocType", "Employee").fields}
		clashes = sorted({f["fieldname"] for f in _employee_fields()} & standard)
		self.assertEqual(clashes, [], "These would stop create_custom_fields on a fresh site: " + ", ".join(clashes))

	def test_the_employee_list_has_the_fields_a_fresh_site_was_missing(self):
		names = [f["fieldname"] for f in _employee_fields()]
		self.assertIn("shift_working", names)
		self.assertIn("custom_is_rambo_reliever", names)
		self.assertEqual(len(names), len(set(names)), "a field is defined twice")

	def test_the_employee_table_has_the_columns(self):
		"""On a site where one_fm was installed fresh (as CI does), this is the install check itself."""
		for column in ("shift_working", "custom_is_rambo_reliever"):
			self.assertTrue(frappe.db.has_column("Employee", column), column)


class TestCreateCustomFieldsResiliently(FrappeTestCase):
	def _run(self, create_side_effect=None, updatedb_side_effect=None, exists=True):
		with patch.object(setup, "create_custom_fields", side_effect=create_side_effect) as create, \
				patch.object(setup.frappe, "log_error") as log, patch.object(setup.frappe.db, "updatedb", side_effect=updatedb_side_effect) as updatedb, \
				patch.object(setup.frappe.db, "exists", return_value=exists), patch.object(setup.frappe, "clear_cache"):
			setup._create_custom_fields_resiliently({"First": [{"fieldname": "a"}], "Second": [{"fieldname": "b"}]})
		return create, log, updatedb

	def test_the_columns_of_rows_saved_before_a_failure_are_still_added(self):
		def fail_first(fields):
			if "First" in fields:
				raise frappe.ValidationError("A field with the name iban already exists")

		create, log, updatedb = self._run(create_side_effect=fail_first)
		self.assertEqual(updatedb.call_args_list, [call("First"), call("Second")])  # the failed doctype too, and the next one still ran
		self.assertEqual(log.call_args_list[0].kwargs["title"], "one_fm after_install: failed to create custom fields for First")
		self.assertEqual(len(log.call_args_list), 1)

	def test_a_successful_doctype_is_updated_and_nothing_is_logged(self):
		create, log, updatedb = self._run()
		self.assertEqual(updatedb.call_args_list, [call("First"), call("Second")])
		log.assert_not_called()

	def test_a_failing_table_update_is_logged_and_does_not_stop_the_next_doctype(self):
		def fail_first(doctype):
			if doctype == "First":
				raise RuntimeError("cannot alter table")

		create, log, updatedb = self._run(updatedb_side_effect=fail_first)
		self.assertEqual(updatedb.call_args_list, [call("First"), call("Second")])
		self.assertEqual([c.kwargs["title"] for c in log.call_args_list], ["one_fm after_install: failed to add the custom field columns for First"])
		self.assertEqual(create.call_count, 2)

	def test_a_doctype_that_does_not_exist_has_no_table_to_update(self):
		create, log, updatedb = self._run(exists=False)
		updatedb.assert_not_called()
