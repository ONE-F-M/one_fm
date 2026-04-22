# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class ClientInterviewShortlist(Document):
	def on_submit(self):
		self.create_employee_schedule_for_client_interview()

	# ---------------------------------------------------------------------------
	# Story 3/1: Employee Schedule creation + Shift Assignment cleanup on submit
	# ---------------------------------------------------------------------------

	def create_employee_schedule_for_client_interview(self):
		for interview_employee in self.client_interview_employee:
			# All availability types that should be replaced by a Client Interview schedule
			# (matches all 5 paths in the BPMN diagram)
			employee_availability_list = [
				"Working",
				"Day Off",
				"Client Day Off",
				"On-the-job Training",
				"Client Event",
			]
			self.delete_existing_employee_schedules(interview_employee, employee_availability_list)
			day_off_ot = 1 if interview_employee.previous_employee_availability == "Day Off" else 0
			self.create_employee_schedule(interview_employee.employee, interview_employee.roster_type, day_off_ot)

	def delete_existing_employee_schedules(self, interview_employee, employee_availability_list):
		existing_schedules = frappe.get_all(
			"Employee Schedule",
			filters={
				"employee": interview_employee.employee,
				"date": self.interview_date,
				"employee_availability": ["in", employee_availability_list],
			},
			fields=["name", "employee_availability"]
		)
		for schedule in existing_schedules:
			self.delete_shift_assignments_for_schedule(interview_employee.employee, schedule.name)
			frappe.delete_doc("Employee Schedule", schedule.name, ignore_permissions=True)
			frappe.db.set_value(
				"Client Interview Employee",
				interview_employee.name,
				"previous_employee_availability",
				schedule.employee_availability
			)

	def delete_shift_assignments_for_schedule(self, employee, schedule_name):
		"""Story 5: Cancel and delete shift assignments linked to an employee schedule.
		If an Attendance record already exists for the shift assignment, preserve it and warn instead."""
		shift_assignments = frappe.get_all(
			"Shift Assignment",
			filters={"start_date": self.interview_date, "employee": employee, "employee_schedule": schedule_name},
			fields=["name", "docstatus"]
		)
		for sa in shift_assignments:
			# Story 5: If attendance already exists for this shift, do NOT delete
			attendance_exists = frappe.db.exists(
				"Attendance",
				{
					"employee": employee,
					"attendance_date": self.interview_date,
					"shift_assignment": sa.name,
					"docstatus": ["!=", 2],
				}
			)
			if attendance_exists:
				employee_name = frappe.db.get_value("Employee", employee, "employee_name") or employee
				frappe.throw(
					_(
						"{0} already has attendance marked on {1}. "
						"This shift assignment cannot be deleted to avoid inconsistencies."
					).format(employee_name, self.interview_date)
				)	

			# Cancel submitted shift assignments before deleting
			if sa.docstatus == 1:
				frappe.get_doc("Shift Assignment", sa.name).cancel()
			frappe.delete_doc("Shift Assignment", sa.name, ignore_permissions=True)


	def create_employee_schedule(self, employee, roster_type, day_off_ot):
		employee_schedule = frappe.get_doc({
			"doctype": "Employee Schedule",
			"employee": employee,
			"date": self.interview_date,
			"employee_availability": "Client Interview",
			"roster_type": roster_type,
			"reference_doctype": self.doctype,
			"reference_docname": self.name,
			"project": self.project,
			"day_off_ot": day_off_ot 
		})
		employee_schedule.insert(ignore_permissions=True)

	def on_update_after_submit(self):
		self.mark_attendance_for_interviewed_employees()

	def mark_attendance_for_interviewed_employees(self):
		"""Update attendance when the attended checkbox changes on a submitted document."""
		for interview_employee in self.client_interview_employee:
			if not interview_employee.has_value_changed("attended"):
				continue
			status = "Client Interview" if interview_employee.attended else "Absent"
			attendance_roster_type = interview_employee.roster_type
			day_off_ot = 1 if interview_employee.previous_employee_availability == "Day Off" else 0
			self.mark_attendance(interview_employee.employee, status, attendance_roster_type, day_off_ot)

	@frappe.whitelist()
	def mark_attendance(self, employee, status, roster_type, day_off_ot):
		attendance = frappe.db.exists(
			"Attendance",
			{
				"employee": employee,
				"attendance_date": self.interview_date,
				"docstatus": ["!=", 2],
			}
		)

		if attendance:
			frappe.db.set_value("Attendance", attendance, {
				"status": status,
				"roster_type": roster_type,
				"day_off_ot": day_off_ot,
				"reference_doctype": self.doctype,
				"reference_docname": self.name,
			})
		else:
			doc = frappe.new_doc("Attendance")
			doc.employee = employee
			doc.attendance_date = self.interview_date
			doc.status = status
			doc.roster_type = roster_type
			doc.day_off_ot = day_off_ot
			doc.reference_doctype = self.doctype
			doc.reference_docname = self.name
			doc.insert(ignore_permissions=True)
			doc.submit()

	# ---------------------------------------------------------------------------
	# Story 2: Cancellation validations and cleanup
	# ---------------------------------------------------------------------------

	def before_cancel(self):
		"""Story 2: Abort cancellation if attendance is already marked for any employee."""
		self.check_if_interview_date_is_in_the_past()
		self.validate_attendance_before_cancel()

	def check_if_interview_date_is_in_the_past(self):
		if getdate(self.interview_date) < getdate(today()):
			frappe.throw(_("Cannot cancel a client interview shortlist with a past interview date."))

	def validate_attendance_before_cancel(self):
		"""Story 2: Throw an error if any employee already has a submitted Attendance record
		linked to this Client Interview Shortlist, preventing data mismatch."""
		for interview_employee in self.client_interview_employee:
			attendance = frappe.db.exists(
				"Attendance",
				{
					"employee": interview_employee.employee,
					"attendance_date": self.interview_date,
					"reference_doctype": self.doctype,
					"reference_docname": self.name,
					"docstatus": 1,
				}
			)
			if attendance:
				employee_name = interview_employee.employee_name or interview_employee.employee
				frappe.throw(
					_(
						"{0}'s Attendance has been marked for this Client Interview Shortlist record. "
						"Cancellation aborted to prevent data mismatch."
					).format(employee_name)
				)

	def on_cancel(self):
		"""Story 2: On confirmed cancellation, delete linked Employee Schedules
		and cancel + delete linked Shift Assignments."""
		self.delete_linked_shift_assignments_on_cancel()
		self.delete_employee_schedule()

	def delete_linked_shift_assignments_on_cancel(self):
		"""Story 2: Find all Employee Schedules linked to this record, then cancel
		and delete their associated Shift Assignments."""
		schedules = frappe.get_all(
			"Employee Schedule",
			filters={
				"reference_doctype": self.doctype,
				"reference_docname": self.name,
			},
			fields=["name", "employee"]
		)
		for schedule in schedules:
			shift_assignments = frappe.get_all(
				"Shift Assignment",
				filters={"employee_schedule": schedule.name},
				fields=["name", "docstatus"]
			)
			for sa in shift_assignments:
				if sa.docstatus == 1:
					frappe.get_doc("Shift Assignment", sa.name).cancel()
				frappe.delete_doc("Shift Assignment", sa.name, ignore_permissions=True)

	def delete_employee_schedule(self):
		schedules = frappe.get_all(
			"Employee Schedule",
			filters={
				"date": self.interview_date,
				"reference_doctype": self.doctype,
				"reference_docname": self.name,
			},
		)
		for schedule in schedules:
			frappe.delete_doc("Employee Schedule", schedule.name, ignore_permissions=True)
