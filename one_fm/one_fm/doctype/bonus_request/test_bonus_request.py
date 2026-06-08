# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import json
from datetime import date

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate, getdate, add_months


def make_bonus_request(**kwargs):
	"""Factory: create a Bonus Request with sensible defaults."""
	today = getdate(nowdate())
	# Default to next month to pass effective month validation
	next_month_date = getdate(add_months(nowdate(), 2))
	month_names = [
		"", "January", "February", "March", "April", "May", "June",
		"July", "August", "September", "October", "November", "December"
	]

	defaults = {
		"doctype": "Bonus Request",
		"posting_date": nowdate(),
		"effective_month": month_names[next_month_date.month],
		"effective_year": next_month_date.year,
		"items": [],
	}
	defaults.update(kwargs)

	# If no items supplied, add a default item
	if not defaults["items"]:
		employees = frappe.get_list(
			"Employee",
			filters={"status": "Active"},
			fields=["name"],
			limit=1
		)
		if employees:
			defaults["items"] = [{
				"employee": employees[0].name,
				"bonus_amount": 100,
				"justification": "Excellent Performance",
			}]

	doc = frappe.get_doc(defaults)
	return doc


class TestBonusRequest(FrappeTestCase):

	def test_total_bonus_amount_calculated(self):
		"""total_bonus_amount should equal the sum of all child row bonus_amount values."""
		employees = frappe.get_list(
			"Employee",
			filters={"status": "Active"},
			fields=["name"],
			limit=3
		)
		if len(employees) < 2:
			self.skipTest("Need at least 2 active employees for this test.")

		doc = make_bonus_request(items=[
			{"employee": employees[0].name, "bonus_amount": 150, "justification": "Excellent Performance"},
			{"employee": employees[1].name, "bonus_amount": 250, "justification": "Perfect Attendance"},
		])
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.total_bonus_amount, 400)

	def test_total_updates_on_row_removal(self):
		"""Removing a row and re-validating should reduce total_bonus_amount."""
		employees = frappe.get_list(
			"Employee",
			filters={"status": "Active"},
			fields=["name"],
			limit=3
		)
		if len(employees) < 3:
			self.skipTest("Need at least 3 active employees for this test.")

		doc = make_bonus_request(items=[
			{"employee": employees[0].name, "bonus_amount": 100, "justification": "Excellent Performance"},
			{"employee": employees[1].name, "bonus_amount": 200, "justification": "Perfect Attendance"},
			{"employee": employees[2].name, "bonus_amount": 300, "justification": "Long Service"},
		])
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.total_bonus_amount, 600)

		# Remove second row
		doc.items = [row for row in doc.items if row.employee != employees[1].name]
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.total_bonus_amount, 400)

	def test_effective_month_rejects_current_month(self):
		"""Selecting the current month should raise a ValidationError."""
		today = getdate(nowdate())
		month_names = [
			"", "January", "February", "March", "April", "May", "June",
			"July", "August", "September", "October", "November", "December"
		]

		doc = make_bonus_request(
			effective_month=month_names[today.month],
			effective_year=today.year,
		)
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_effective_month_rejects_past_month(self):
		"""Selecting a past month should raise a ValidationError."""
		past_date = getdate(add_months(nowdate(), -2))
		month_names = [
			"", "January", "February", "March", "April", "May", "June",
			"July", "August", "September", "October", "November", "December"
		]

		doc = make_bonus_request(
			effective_month=month_names[past_date.month],
			effective_year=past_date.year,
		)
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_effective_month_accepts_future_month(self):
		"""Selecting a future month should succeed without error."""
		future_date = getdate(add_months(nowdate(), 3))
		month_names = [
			"", "January", "February", "March", "April", "May", "June",
			"July", "August", "September", "October", "November", "December"
		]

		doc = make_bonus_request(
			effective_month=month_names[future_date.month],
			effective_year=future_date.year,
		)
		doc.insert(ignore_permissions=True)
		self.assertTrue(doc.name)

	def test_justification_other_requires_description(self):
		"""justification='Other' without description should raise ValidationError."""
		employees = frappe.get_list(
			"Employee",
			filters={"status": "Active"},
			fields=["name"],
			limit=1
		)
		if not employees:
			self.skipTest("Need at least 1 active employee for this test.")

		doc = make_bonus_request(items=[
			{
				"employee": employees[0].name,
				"bonus_amount": 100,
				"justification": "Other",
				"description": "",
			}
		])
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_justification_other_with_description_succeeds(self):
		"""justification='Other' with description should save successfully."""
		employees = frappe.get_list(
			"Employee",
			filters={"status": "Active"},
			fields=["name"],
			limit=1
		)
		if not employees:
			self.skipTest("Need at least 1 active employee for this test.")

		doc = make_bonus_request(items=[
			{
				"employee": employees[0].name,
				"bonus_amount": 100,
				"justification": "Other",
				"description": "Custom reason for bonus",
			}
		])
		doc.insert(ignore_permissions=True)
		self.assertTrue(doc.name)

	def test_description_cleared_when_justification_not_other(self):
		"""If justification is not 'Other', description should be cleared on validate."""
		employees = frappe.get_list(
			"Employee",
			filters={"status": "Active"},
			fields=["name"],
			limit=1
		)
		if not employees:
			self.skipTest("Need at least 1 active employee for this test.")

		doc = make_bonus_request(items=[
			{
				"employee": employees[0].name,
				"bonus_amount": 100,
				"justification": "Excellent Performance",
				"description": "This should be cleared",
			}
		])
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.items[0].description, "")

	def test_self_request_prevention(self):
		"""Adding the current user's employee to the grid should raise ValidationError."""
		current_employee = frappe.db.get_value(
			"Employee",
			{"user_id": frappe.session.user, "status": "Active"},
			"name"
		)
		if not current_employee:
			self.skipTest("Current session user has no active Employee record.")

		doc = make_bonus_request(items=[
			{
				"employee": current_employee,
				"bonus_amount": 100,
				"justification": "Excellent Performance",
			}
		])
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_consolidated_api_creates_single_doc_with_n_rows(self):
		"""create_consolidated_bonus_request should produce 1 parent + N child rows."""
		from one_fm.one_fm.doctype.bonus_request.bonus_request import create_consolidated_bonus_request

		employees = frappe.get_list(
			"Employee",
			filters={"status": "Active"},
			fields=["name"],
			limit=3
		)
		if len(employees) < 2:
			self.skipTest("Need at least 2 active employees for this test.")

		future_date = getdate(add_months(nowdate(), 2))
		month_names = [
			"", "January", "February", "March", "April", "May", "June",
			"July", "August", "September", "October", "November", "December"
		]

		emp_ids = [e.name for e in employees]

		doc_name = create_consolidated_bonus_request(
			employees=json.dumps(emp_ids),
			bonus_amount=200.0,
			effective_month=month_names[future_date.month],
			effective_year=future_date.year,
			justification="Excellent Performance",
		)

		doc = frappe.get_doc("Bonus Request", doc_name)

		# Exactly 1 parent document with N child rows
		self.assertEqual(len(doc.items), len(emp_ids))
		# Each row should have the same bonus amount
		for row in doc.items:
			self.assertEqual(row.bonus_amount, 200.0)
		# Total should be bonus_amount * number of employees
		self.assertEqual(doc.total_bonus_amount, 200.0 * len(emp_ids))

	def test_consolidated_api_rejects_empty_employees(self):
		"""create_consolidated_bonus_request with empty list should raise."""
		from one_fm.one_fm.doctype.bonus_request.bonus_request import create_consolidated_bonus_request

		self.assertRaises(
			frappe.ValidationError,
			create_consolidated_bonus_request,
			employees="[]",
			bonus_amount=100,
			effective_month="December",
			effective_year=2099,
			justification="Excellent Performance",
		)

	def test_consolidated_api_rejects_zero_bonus(self):
		"""create_consolidated_bonus_request with zero amount should raise."""
		from one_fm.one_fm.doctype.bonus_request.bonus_request import create_consolidated_bonus_request

		employees = frappe.get_list(
			"Employee",
			filters={"status": "Active"},
			fields=["name"],
			limit=1
		)
		if not employees:
			self.skipTest("Need at least 1 active employee for this test.")

		self.assertRaises(
			frappe.ValidationError,
			create_consolidated_bonus_request,
			employees=json.dumps([employees[0].name]),
			bonus_amount=0,
			effective_month="December",
			effective_year=2099,
			justification="Excellent Performance",
		)
