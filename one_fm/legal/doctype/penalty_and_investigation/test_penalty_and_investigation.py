import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days


class TestPenaltyAndInvestigation(FrappeTestCase):
	def setUp(self):
		# Create test employee if not exists
		if not frappe.db.exists("Employee", "TEST-EMP-001"):
			self.employee = frappe.get_doc({
				"doctype": "Employee",
				"employee": "TEST-EMP-001",
				"first_name": "Test",
				"last_name": "Employee",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"status": "Active",
				"company": "One Facilities Management"
			}).insert()
		else:
			self.employee = frappe.get_doc("Employee", "TEST-EMP-001")

		# Create test penalty code (without penalty_level rows)
		if not frappe.db.exists("Penalty Code", "TEST-PEN-001"):
			self.penalty_code = frappe.get_doc({
				"doctype": "Penalty Code",
				"penalty_name": "Test Penalty",
				"violation_type": "Work",
				"naming_series": "HR-PEN-.####",
				"is_active": 1
			}).insert()
			# Rename to predictable name if series was used
			if self.penalty_code.name != "TEST-PEN-001":
				frappe.rename_doc("Penalty Code", self.penalty_code.name, "TEST-PEN-001")
				self.penalty_code = frappe.get_doc("Penalty Code", "TEST-PEN-001")
		else:
			self.penalty_code = frappe.get_doc("Penalty Code", "TEST-PEN-001")

		# Create test penalty code WITH all five penalty_level rows
		if not frappe.db.exists("Penalty Code", "TEST-PEN-LEVELS"):
			pc = frappe.get_doc({
				"doctype": "Penalty Code",
				"penalty_name": "Test Penalty With Levels",
				"violation_type": "Work",
				"naming_series": "HR-PEN-.####",
				"is_active": 1,
				"penalty_level": [
					{"offence_level": "1st", "deduction_type": "Warning", "salary_deduction_days": 0},
					{"offence_level": "2nd", "deduction_type": "Salary Deduction", "salary_deduction_days": 1},
					{"offence_level": "3rd", "deduction_type": "Salary Deduction", "salary_deduction_days": 2},
					{"offence_level": "4th", "deduction_type": "Suspension", "salary_deduction_days": 0},
					{"offence_level": "5th", "deduction_type": "Termination", "salary_deduction_days": 0},
				]
			}).insert()
			if pc.name != "TEST-PEN-LEVELS":
				frappe.rename_doc("Penalty Code", pc.name, "TEST-PEN-LEVELS")
				pc = frappe.get_doc("Penalty Code", "TEST-PEN-LEVELS")
			self.penalty_code_with_levels = pc
		else:
			self.penalty_code_with_levels = frappe.get_doc("Penalty Code", "TEST-PEN-LEVELS")

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	def test_duplicate_penalty_validation(self):
		# 1. Create first penalty investigation
		doc1 = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code.name,
			"incident_date": today(),
			"issuance_date": today(),
		}).insert()

		# 2. Try to create second penalty investigation with same details
		doc2 = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code.name,
			"incident_date": today(),
			"issuance_date": today(),
		})

		self.assertRaises(frappe.ValidationError, doc2.insert)

		# 3. Cancel first and try again (should succeed)
		doc1.cancel()
		doc2.insert()
		self.assertTrue(frappe.db.exists("Penalty And Investigation", doc2.name))

	def test_offence_level_mapping_first_offence(self):
		"""First offence uses 1st-level row: Warning / 0 deduction days."""
		doc = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code_with_levels.name,
			"incident_date": today(),
			"issuance_date": today(),
		}).insert()

		self.assertEqual(doc.offence_count, 1)
		self.assertEqual(doc.applied_level, "1")
		self.assertEqual(doc.deduction_type, "Warning")
		self.assertEqual(doc.salary_deduction_days, 0)

	def test_offence_level_mapping_escalation(self):
		"""Second offence escalates to 2nd-level row: Salary Deduction / 1 day."""
		# First offence on a prior date
		frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code_with_levels.name,
			"incident_date": add_days(today(), -5),
			"issuance_date": today(),
		}).insert()

		# Second offence today
		doc2 = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code_with_levels.name,
			"incident_date": today(),
			"issuance_date": today(),
		}).insert()

		self.assertEqual(doc2.offence_count, 2)
		self.assertEqual(doc2.applied_level, "2")
		self.assertEqual(doc2.deduction_type, "Salary Deduction")
		self.assertEqual(doc2.salary_deduction_days, 1)

	def test_offence_level_mapping_no_matching_level(self):
		"""Penalty Code with no penalty_level rows falls back to None / 0."""
		# self.penalty_code (TEST-PEN-001) has no penalty_level rows
		doc = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code.name,
			"incident_date": today(),
			"issuance_date": today(),
		}).insert()

		self.assertIsNone(doc.deduction_type)
		self.assertEqual(doc.salary_deduction_days, 0)

	def test_offence_level_capped_at_five(self):
		"""Offence level is capped at 5 even when there are more than 5 prior incidents."""
		# Create 5 prior offences on distinct dates
		for i in range(5, 0, -1):
			frappe.get_doc({
				"doctype": "Penalty And Investigation",
				"employee": self.employee.name,
				"applied_penalty_code": self.penalty_code_with_levels.name,
				"incident_date": add_days(today(), -i),
				"issuance_date": today(),
			}).insert()

		# Sixth offence — level should be capped at 5
		doc6 = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code_with_levels.name,
			"incident_date": today(),
			"issuance_date": today(),
		}).insert()

		self.assertEqual(doc6.offence_count, 6)
		self.assertEqual(doc6.applied_level, "5")
		self.assertEqual(doc6.deduction_type, "Termination")
		self.assertEqual(doc6.salary_deduction_days, 0)
