# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-004230: Preparation Record.relieving_date follows Employee.relieving_date.

The column is a fetch_from field, so a save of a draft re-reads it with the link
validation lookup that already runs once per row. update_preparation_employee_dates is a
pure read the form uses to repaint rows that are stale.
"""

import re
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime, nowdate

from one_fm.grd.doctype.preparation.preparation import update_preparation_employee_dates

EMPLOYEE_TABLE = re.compile(r"[`\"]tabEmployee[`\"]")


def _an_active_employee():
	"""An Active employee to point rows at.

	Active, or validate_preparation_table throws before anything else is checked. Taken
	from the site like the sibling tests do; only when the site has none is a minimal row
	written with the Query Builder (the Employee controller needs a Company and custom
	columns this test site may not have, and none of that is under test).
	"""
	name = frappe.db.get_value("Employee", {"status": "Active"}, "name", order_by="creation asc")
	if name:
		return name

	name = "TEST-RELDATE-EMP"
	now = now_datetime()
	employee = frappe.qb.DocType("Employee")
	(
		frappe.qb.into(employee)
		.columns(
			"name", "creation", "modified", "modified_by", "owner", "docstatus", "idx",
			"employee_name", "first_name", "status",
		)
		.insert(name, now, now, "Administrator", "Administrator", 0, 0, name, name, "Active")
		.run()
	)
	return name


def _count(spy, pattern):
	return len([q for q in spy if pattern(q)])


class TestPreparationRelievingDate(FrappeTestCase):
	def setUp(self):
		self._drop_fetches_of_missing_employee_columns()
		self.employee = _an_active_employee()
		self._set_employee_date(None)
		self.date = add_days(nowdate(), 30)
		self.other_date = add_days(nowdate(), 90)

	# helpers

	def _drop_fetches_of_missing_employee_columns(self):
		"""Work around custom Employee columns this test site may not have.

		Link validation selects every fetch_from column of the row from tabEmployee, so a
		missing custom column (employee_id, one_fm_civil_id ...) fails every save with
		"Unknown column". Those fetches are switched off for the test, for the columns that
		are absent only. relieving_date is a standard Employee column and is never touched.
		"""
		for df in frappe.get_meta("Preparation Record").fields:
			source = (df.fetch_from or "").split(".")
			if len(source) != 2 or source[0] != "employee" or source[1] == "relieving_date":
				continue
			if not frappe.db.has_column("Employee", source[1]):
				patcher = mock.patch.object(df, "fetch_from", None)
				patcher.start()
				self.addCleanup(patcher.stop)

	def _set_employee_date(self, value):
		frappe.db.set_value("Employee", self.employee, "relieving_date", value)

	def _draft(self, rows=1):
		doc = frappe.get_doc({
			"doctype": "Preparation",
			"category": "Onboarding",
			"posting_date": nowdate(),
			"preparation_record": [
				{"employee": self.employee, "renewal_or_extend": "Overseas"} for _ in range(rows)
			],
		})
		doc.insert(ignore_permissions=True)
		return frappe.get_doc("Preparation", doc.name)

	def _stored(self, row):
		value = frappe.db.get_value("Preparation Record", row.name, "relieving_date")
		return getdate(value) if value else None

	def _save(self, name):
		doc = frappe.get_doc("Preparation", name)
		doc.save(ignore_permissions=True)
		return doc

	def _spy(self, fn):
		"""Every SQL statement text issued while fn runs."""
		statements = []
		original = frappe.db.sql

		def spy(query, *args, **kwargs):
			statements.append(str(query))
			return original(query, *args, **kwargs)

		with mock.patch.object(frappe.db, "sql", side_effect=spy):
			fn()
		return statements

	def _employee_queries(self, name):
		return _count(self._spy(lambda: self._save(name)), EMPLOYEE_TABLE.search)

	# saving a draft

	def test_saving_a_draft_fills_a_blank_row(self):
		doc = self._draft()
		self.assertIsNone(self._stored(doc.preparation_record[0]))

		self._set_employee_date(self.date)
		self._save(doc.name)

		self.assertEqual(self._stored(doc.preparation_record[0]), getdate(self.date))

	def test_saving_a_draft_corrects_a_stale_row(self):
		self._set_employee_date(self.date)
		doc = self._draft()
		row = doc.preparation_record[0]
		self.assertEqual(self._stored(row), getdate(self.date))

		self._set_employee_date(self.other_date)
		self._save(doc.name)

		self.assertEqual(self._stored(row), getdate(self.other_date))

	def test_clearing_the_employee_date_clears_the_row_on_next_save(self):
		self._set_employee_date(self.date)
		doc = self._draft()
		row = doc.preparation_record[0]
		self.assertEqual(self._stored(row), getdate(self.date))

		self._set_employee_date(None)
		self._save(doc.name)

		self.assertIsNone(self._stored(row))

	# submitted

	def test_a_submitted_document_does_not_re_fetch(self):
		self._set_employee_date(self.date)
		doc = self._draft()
		row = doc.preparation_record[0]
		# Marked submitted directly: submitting runs the document-creation machinery,
		# which is not what is under test.
		frappe.db.set_value("Preparation", doc.name, "docstatus", 1)
		frappe.db.set_value("Preparation Record", {"parent": doc.name}, "docstatus", 1)
		self._set_employee_date(self.other_date)

		before = self._stored(row)
		submitted = frappe.get_doc("Preparation", doc.name)
		submitted._action = "update_after_submit"  # what save() sets before validating links
		statements = self._spy(submitted._validate_links)

		self.assertEqual(submitted.preparation_record[0].relieving_date, before)
		self.assertEqual(self._stored(row), before)
		self.assertEqual(before, getdate(self.date))
		self.assertEqual(_count(statements, lambda q: q.lstrip().upper().startswith("UPDATE")), 0)

		# the form still learns the current date, through the read-only method
		result = update_preparation_employee_dates(doc.name)
		self.assertEqual(result["updated_rows"], [row.name])
		self.assertEqual(result["values"], {row.name: str(getdate(self.other_date))})
		self.assertEqual(self._stored(row), before)

	# query count

	def test_fetch_from_adds_no_employee_query(self):
		small = self._draft(rows=1)
		large = self._draft(rows=200)
		field = frappe.get_meta("Preparation Record").get_field("relieving_date")
		self.assertEqual(field.fetch_from, "employee.relieving_date")
		self._set_employee_date(self.date)

		small_with = self._employee_queries(small.name)
		large_with = self._employee_queries(large.name)
		self.assertEqual(self._stored(large.preparation_record[0]), getdate(self.date))

		# the same saves with relieving_date out of the fetch list
		frappe.db.set_value("Preparation Record", {"parent": ["in", [small.name, large.name]]}, "relieving_date", None)
		with mock.patch.object(field, "fetch_from", None):
			small_without = self._employee_queries(small.name)
			large_without = self._employee_queries(large.name)
			# proves the patch took effect: nothing fetched the date this time
			self.assertIsNone(self._stored(large.preparation_record[0]))

		# one lookup per row and nothing else per row: linear in the row count
		self.assertEqual(large_with - small_with, 199)
		# Fix 1 added a column to a SELECT that was already issued, not a query
		self.assertEqual(small_with, small_without)
		self.assertEqual(large_with, large_without)

	# loading the form

	def test_loading_the_form_writes_nothing(self):
		doc = self._draft(rows=200)
		self._set_employee_date(self.date)  # every row is now stale

		statements = self._spy(lambda: self._result.update(update_preparation_employee_dates(doc.name)))

		writes = _count(
			statements,
			lambda q: q.lstrip().upper().startswith(("UPDATE", "INSERT", "DELETE")),
		)
		self.assertEqual(writes, 0)
		self.assertIn("updated_rows", self._result)
		self.assertEqual(len(self._result["updated_rows"]), 200)
		self.assertEqual(len(self._result["values"]), 200)
		self.assertEqual(
			frappe.db.count("Preparation Record", {"parent": doc.name, "relieving_date": ["is", "set"]}), 0
		)

	def test_the_response_is_empty_when_every_date_is_current(self):
		self._set_employee_date(self.date)
		doc = self._draft(rows=3)

		result = update_preparation_employee_dates(doc.name)

		self.assertEqual(result["updated_rows"], [])
		self.assertFalse(result.get("values"))
		self.assertNotIn("data", result)

	@property
	def _result(self):
		if not hasattr(self, "_response"):
			self._response = {}
		return self._response
