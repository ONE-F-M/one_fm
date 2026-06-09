# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

class TestClientInterviewShortlist(FrappeTestCase):
	def setUp(self):
		self.employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"employee_name": "Test Employee",
				"company": "_Test Company",
				"date_of_joining": "2025-01-01",
				"department": "_Test Department",
			}
		).insert(ignore_if_duplicate=True)
		self.project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": "Test Project",
			}
		).insert(ignore_if_duplicate=True)

	def tearDown(self):
		frappe.db.rollback()

	def test_create_employee_schedule_on_submit(self):
		shortlist = create_client_interview_shortlist(self.employee.name, self.project.name)
		shortlist.submit()

		schedule_exists = frappe.db.exists(
			"Employee Schedule",
			{
				"employee": self.employee.name,
				"date": shortlist.interview_date,
				"employee_availability": "Client Interview",
				"project": self.project.name,
			},
		)
		self.assertTrue(schedule_exists)

	def test_replace_existing_employee_schedule_on_submit(self):
		interview_date = getdate("2025-11-30")
		# Create an existing schedule
		existing_schedule = frappe.get_doc(
			{
				"doctype": "Employee Schedule",
				"employee": self.employee.name,
				"date": interview_date,
				"employee_availability": "Working",
			}
		).insert(ignore_permissions=True)

		shortlist = create_client_interview_shortlist(
			self.employee.name, self.project.name, interview_date=interview_date
		)
		shortlist.submit()

		# Check that the old schedule is deleted
		self.assertFalse(frappe.db.exists("Employee Schedule", existing_schedule.name))

		# Check that the new schedule is created
		new_schedule_exists = frappe.db.exists(
			"Employee Schedule",
			{
				"employee": self.employee.name,
				"date": interview_date,
				"employee_availability": "Client Interview",
				"project": self.project.name,
			},
		)
		self.assertTrue(new_schedule_exists)

	def test_cancel_shift_assignments_with_absent_attendance(self):
		"""Story 5: When shift assignment has 'Absent' attendance, remove attendance and cancel the shift assignment."""
		interview_date = getdate("2025-11-30")
		
		# Create an existing schedule
		existing_schedule = frappe.get_doc(
			{
				"doctype": "Employee Schedule",
				"employee": self.employee.name,
				"date": interview_date,
				"employee_availability": "Working",
			}
		).insert(ignore_permissions=True)

		# Create a shift assignment linked to the schedule
		shift_assignment = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"employee": self.employee.name,
				"start_date": interview_date,
				"employee_schedule": existing_schedule.name,
			}
		).insert(ignore_permissions=True)
		shift_assignment.submit()

		# Create "Absent" attendance record for this shift
		attendance = frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": self.employee.name,
				"attendance_date": interview_date,
				"status": "Absent",
				"shift_assignment": shift_assignment.name,
			}
		).insert(ignore_permissions=True)
		attendance.submit()

		# Submit client interview shortlist - should automatically remove "Absent" attendance and cancel shift assignment
		shortlist = create_client_interview_shortlist(
			self.employee.name, self.project.name, interview_date=interview_date
		)
		shortlist.submit()

		# Check that attendance was removed
		self.assertFalse(frappe.db.exists("Attendance", attendance.name))

		# Check that shift assignment was cancelled
		cancelled_sa = frappe.get_doc("Shift Assignment", shift_assignment.name)
		self.assertEqual(cancelled_sa.docstatus, 2)

	def test_prevent_shift_assignment_cancel_with_non_absent_attendance(self):
		"""Story 5: When shift assignment has non-'Absent' attendance, prevent cancellation."""
		interview_date = getdate("2025-11-30")
		
		# Create an existing schedule
		existing_schedule = frappe.get_doc(
			{
				"doctype": "Employee Schedule",
				"employee": self.employee.name,
				"date": interview_date,
				"employee_availability": "Working",
			}
		).insert(ignore_permissions=True)

		# Create a shift assignment linked to the schedule
		shift_assignment = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"employee": self.employee.name,
				"start_date": interview_date,
				"employee_schedule": existing_schedule.name,
			}
		).insert(ignore_permissions=True)
		shift_assignment.submit()

		# Create "Present" attendance record for this shift
		attendance = frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": self.employee.name,
				"attendance_date": interview_date,
				"status": "Present",
				"shift_assignment": shift_assignment.name,
			}
		).insert(ignore_permissions=True)
		attendance.submit()

		# Submit client interview shortlist - should throw error
		shortlist = create_client_interview_shortlist(
			self.employee.name, self.project.name, interview_date=interview_date
		)
		
		with self.assertRaises(frappe.ValidationError):
			shortlist.submit()

def create_client_interview_shortlist(employee, project, interview_date=None):
	if not interview_date:
		interview_date = getdate("2025-11-30")

	shortlist = frappe.get_doc(
		{
			"doctype": "Client Interview Shortlist",
			"company": "_Test Company",
			"project": project,
			"interview_date": interview_date,
			"client_interview_employee": [
				{
					"employee": employee,
					"roster_type": "Basic",
				}
			],
		}
	).insert(ignore_permissions=True)
	return shortlist