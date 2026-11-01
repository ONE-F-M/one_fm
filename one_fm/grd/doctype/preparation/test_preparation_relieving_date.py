# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-004230: Preparation Record.relieving_date mirrors Employee.relieving_date.

The row column used to be written once, when the row was created, and never refreshed.
`validate` now refreshes it from one bulk lookup, and `update_preparation_employee_dates`
reports the stale rows without writing anything.
"""

from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from one_fm.grd.doctype.preparation import preparation as preparation_module
from one_fm.grd.doctype.preparation.preparation import update_preparation_employee_dates

FETCH = "one_fm.grd.doctype.preparation.preparation.fetch_employee_relieving_dates"


def _active_employee(name="Test Relieving Date Employee"):
	"""A fresh Employee with no relieving date.

	Active, or validate_preparation_table throws before anything else is checked. The
	test site may hold no employees at all, so this never relies on existing ones.
	"""
	employee_name = "TEST-RELDATE-EMP"
	# The Employee controller needs custom fields and a Company this site may not have, and
	# the table here can lag its meta, so none of that is under test: write only the columns
	# the Preparation code reads. The class rolls the transaction back when it finishes.
	frappe.db.delete("Employee", {"name": employee_name})
	now = now_datetime()
	Employee = frappe.qb.DocType("Employee")
	(
		frappe.qb.into(Employee)
		.columns(
			Employee.name,
			Employee.employee_name,
			Employee.first_name,
			Employee.status,
			Employee.owner,
			Employee.modified_by,
			Employee.creation,
			Employee.modified,
			Employee.docstatus,
		)
		.insert(employee_name, name, name, "Active", "Administrator", "Administrator", now, now, 0)
		.run()
	)
	return employee_name


def _employee_queries(callable_):
	"""Run `callable_` and return the statements it sent that read tabEmployee."""
	statements = []
	original = frappe.db.sql

	def recording(query, *args, **kwargs):
		if "tabEmployee" in str(query):
			statements.append(str(query))
		return original(query, *args, **kwargs)

	with mock.patch.object(frappe.db, "sql", side_effect=recording):
		callable_()
	return statements


class TestPreparationRelievingDate(FrappeTestCase):
	def setUp(self):
		self.employee = _active_employee()
		self.date = add_days(nowdate(), 30)

	def _set_employee_date(self, employee, value):
		previous = frappe.db.get_value("Employee", employee, "relieving_date")
		frappe.db.set_value("Employee", employee, "relieving_date", value, update_modified=False)
		self.addCleanup(
			frappe.db.set_value, "Employee", employee, "relieving_date", previous, update_modified=False
		)

	def _a_preparation(self, employees=None):
		employees = employees or [self.employee]
		preparation = frappe.get_doc({
			"doctype": "Preparation",
			"category": "Onboarding",
			"posting_date": nowdate(),
			"preparation_record": [
				{"employee": employee, "renewal_or_extend": "Overseas"} for employee in employees
			],
		})
		preparation.flags.ignore_permissions = True
		preparation.insert()
		return preparation

	def _store_row_date(self, row, value):
		frappe.db.set_value(row.doctype, row.name, "relieving_date", value, update_modified=False)

	def _stored_row_date(self, row):
		return frappe.db.get_value(row.doctype, row.name, "relieving_date")

	def _reloaded(self, preparation):
		return frappe.get_doc("Preparation", preparation.name)

	# validate

	def test_validate_fills_a_blank_row(self):
		preparation = self._a_preparation()
		row = preparation.preparation_record[0]
		self._store_row_date(row, None)
		self._set_employee_date(self.employee, self.date)

		doc = self._reloaded(preparation)
		self.assertIsNone(doc.preparation_record[0].relieving_date)
		doc.validate()

		self.assertEqual(getdate(doc.preparation_record[0].relieving_date), getdate(self.date))

	def test_validate_corrects_a_stale_row(self):
		preparation = self._a_preparation()
		row = preparation.preparation_record[0]
		self._store_row_date(row, add_days(nowdate(), 5))
		self._set_employee_date(self.employee, self.date)

		doc = self._reloaded(preparation)
		doc.validate()

		self.assertEqual(getdate(doc.preparation_record[0].relieving_date), getdate(self.date))

	def test_validate_clears_the_row_when_the_employee_date_was_removed(self):
		preparation = self._a_preparation()
		row = preparation.preparation_record[0]
		self._store_row_date(row, add_days(nowdate(), 5))
		self.assertFalse(frappe.db.get_value("Employee", self.employee, "relieving_date"))

		doc = self._reloaded(preparation)
		self.assertTrue(doc.preparation_record[0].relieving_date)
		doc.validate()

		self.assertIsNone(doc.preparation_record[0].relieving_date)

	def test_validate_leaves_a_row_whose_employee_is_not_found(self):
		preparation = self._a_preparation()
		row = preparation.preparation_record[0]
		kept = add_days(nowdate(), 5)
		self._store_row_date(row, kept)

		doc = self._reloaded(preparation)
		with mock.patch(FETCH, return_value={}):
			doc.validate()

		self.assertEqual(getdate(doc.preparation_record[0].relieving_date), getdate(kept))

	def test_a_duplicate_employee_is_looked_up_once(self):
		self._set_employee_date(self.employee, self.date)
		doc = frappe.get_doc({
			"doctype": "Preparation",
			"preparation_record": [{"employee": self.employee}, {"employee": self.employee}],
		})

		with mock.patch(FETCH, wraps=preparation_module.fetch_employee_relieving_dates) as fetch:
			statements = _employee_queries(doc.set_relieving_dates)

		self.assertEqual(len(statements), 1)
		self.assertEqual(list(fetch.call_args[0][0]), [self.employee])
		for row in doc.preparation_record:
			self.assertEqual(getdate(row.relieving_date), getdate(self.date))

	def test_the_query_count_does_not_grow_with_the_row_count(self):
		# One real employee, the rest distinct names: the lookup count must not depend on them.
		pool = [self.employee] + ["NO-SUCH-EMP-{0}".format(index) for index in range(199)]

		def queries_for(rows):
			doc = frappe.get_doc({
				"doctype": "Preparation",
				"preparation_record": [
					{"employee": pool[index % len(pool)]} for index in range(rows)
				],
			})
			return _employee_queries(doc.set_relieving_dates)

		single = queries_for(1)
		many = queries_for(200)

		self.assertEqual(len(single), 1)
		self.assertEqual(len(many), len(single))

	# update_preparation_employee_dates

	def test_updating_the_dates_writes_nothing_and_reports_the_stale_rows(self):
		preparation = self._a_preparation()
		row = preparation.preparation_record[0]
		stale = add_days(nowdate(), 5)
		self._store_row_date(row, stale)
		self._set_employee_date(self.employee, self.date)
		# Submitted: the stored value is what an auditor reads.
		frappe.db.set_value("Preparation", preparation.name, "docstatus", 1, update_modified=False)

		with mock.patch.object(frappe.db, "set_value") as set_value, mock.patch.object(
			frappe.db, "bulk_update"
		) as bulk_update:
			result = update_preparation_employee_dates(preparation.name)

		set_value.assert_not_called()
		bulk_update.assert_not_called()
		self.assertEqual(getdate(self._stored_row_date(row)), getdate(stale))
		self.assertIn(row.name, result["updated_rows"])
		self.assertEqual(getdate(result["values"][row.name]), getdate(self.date))
		self.assertNotIn("data", result)

	def test_updating_the_dates_skips_rows_that_already_match(self):
		preparation = self._a_preparation()
		row = preparation.preparation_record[0]
		self._set_employee_date(self.employee, self.date)
		self._store_row_date(row, self.date)

		result = update_preparation_employee_dates(preparation.name)

		self.assertEqual(result["updated_rows"], [])
		self.assertEqual(result["values"], {})

	def test_updating_the_dates_reports_a_cleared_date(self):
		preparation = self._a_preparation()
		row = preparation.preparation_record[0]
		self._store_row_date(row, add_days(nowdate(), 5))

		result = update_preparation_employee_dates(preparation.name)

		self.assertEqual(result["updated_rows"], [row.name])
		self.assertIsNone(result["values"][row.name])
