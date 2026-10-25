# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The report shows the Operations Shift stored on the check-in record."""

import frappe
from frappe.tests.utils import FrappeTestCase

# Module import, so the runner does not pick up and rerun the check-in test class.
from one_fm.accommodation.doctype.accommodation_checkin_checkout import (
	test_accommodation_checkin_checkout as checkin_tests,
)
from one_fm.accommodation.report.accommodation_checkin_checkout_report.accommodation_checkin_checkout_report import (
	execute,
	get_columns,
)


class TestAccommodationCheckinCheckoutReport(FrappeTestCase):
	def setUp(self):
		self.employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not self.employee:
			self.skipTest("No Active Employee on this site")
		self.shift = checkin_tests.make_operations_shift()
		frappe.db.set_value("Employee", self.employee, "shift", self.shift)

	def report_row(self, checkin_name, **filters):
		_columns, data = execute({"employee": self.employee, **filters})
		return next(row for row in data if row["checkin_ref"] == checkin_name)

	def test_operations_shift_sits_between_project_and_nationality(self):
		fieldnames = [column["fieldname"] for column in get_columns({})]
		index = fieldnames.index("operations_shift")
		self.assertEqual(fieldnames[index - 1], "project")
		self.assertEqual(fieldnames[index + 1], "nationality")

	def test_row_shows_the_checkin_shift(self):
		checkin = checkin_tests.make_checkin(self.employee)
		self.assertEqual(self.report_row(checkin.name)["operations_shift"], self.shift)

	def test_row_keeps_the_stored_shift_after_the_employee_moves(self):
		checkin = checkin_tests.make_checkin(self.employee)
		frappe.db.set_value("Employee", self.employee, "shift", checkin_tests.make_operations_shift())
		self.assertEqual(self.report_row(checkin.name)["operations_shift"], self.shift)

	def test_checked_out_stay_shows_the_shift(self):
		checkin = checkin_tests.make_checkin(self.employee)
		frappe.db.set_value(checkin_tests.DOCTYPE, checkin.name, "checked_out", 1)
		row = self.report_row(checkin.name, checkout_list_only=1)
		self.assertEqual(row["operations_shift"], self.shift)
