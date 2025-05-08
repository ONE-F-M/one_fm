# Copyright (c) 2024, omar jaber and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count
from frappe.utils import getdate, get_last_day

class DefaultShiftChecker(Document):
	def on_submit(self):
		self.update_employee_shift_details()

	def update_employee_shift_details(self):
		"""
			Updates the employee's shift or reliever status based on the action type.
		"""
		employee = frappe.get_doc("Employee", self.employee)

		field_updates = {
			"Shift Allocation Update": {
				"shift": self.new_shift_allocation,
				"custom_operations_role_allocation": self.new_operations_role_allocation
			},
			"Mark Employee as Reliever": {
				"custom_is_reliever": 1
			}
		}

		if self.action_type in field_updates:
			employee.update(field_updates[self.action_type])
			employee.save()

		self.db_set("status", "Completed")


def create_default_shift_checker():
	start_date = getdate()
	last_day_of_month = get_last_day(start_date)

	# For normal employees
	create_checker(start_date, last_day_of_month, is_reliever=False)
	# For relievers
	create_checker(start_date, last_day_of_month, is_reliever=True)


def create_checker(start_date, last_day_of_month, is_reliever=False):
	"""
	Unified function to create Default Shift Checker records for both regular employees and relievers
	"""
	Employee = frappe.qb.DocType("Employee")
	EmployeeSchedule = frappe.qb.DocType("Employee Schedule")
	Project = frappe.qb.DocType("Project")

	# Configuration for threshold and fieldname
	threshold_type = "reliever_default_shift_checker_threshold" if is_reliever else "default_shift_checker_threshold"
	threshold = frappe.db.get_single_value("ONEFM General Setting", threshold_type) or 0
	field_name = "reliever_assigned_to_the_same_shift" if is_reliever else "assigned_shifts_outside_default_shift"

	# Fetch list of employees
	query = (
		frappe.qb.from_(Employee)
		.join(EmployeeSchedule).on(Employee.name == EmployeeSchedule.employee)
		.left_join(Project).on(Employee.project == Project.name)
		.select(
			Employee.name.as_("employee"),
			Employee.shift.as_("default_shift"),
			Employee.site.as_("default_site")
		)
		.where(
			(Employee.status == "Active")
			& (Employee.shift_working == 1)
			& (Employee.custom_is_reliever == (1 if is_reliever else 0))
			& (Employee.shift.isnotnull())
			& (EmployeeSchedule.shift == Employee.shift if is_reliever else EmployeeSchedule.shift != Employee.shift)
			& (EmployeeSchedule.employee_availability == "Working")
			& (EmployeeSchedule.roster_type == "Basic")
			& (EmployeeSchedule.date[start_date:last_day_of_month])
			& (Project.custom_exclude_from_default_shift_checker != 1)
		)
		.groupby(Employee.name)
		.having(Count(EmployeeSchedule.shift) > threshold)
	)

	# Create default shift checker
	for employee in query.run(as_dict=True):
		try:
			doc = frappe.new_doc("Default Shift Checker")
			doc.employee = employee.employee
			doc.start_date = start_date
			doc.end_date = last_day_of_month
			doc.site_supervisor = frappe.db.get_value("Operations Site", employee.default_site, "account_supervisor")
			
			if is_reliever:
				doc.is_reliever = 1

			# Get shiftwise count for each employee
			shift_condition = (EmployeeSchedule.shift == employee.default_shift) if is_reliever else (EmployeeSchedule.shift != employee.default_shift)
			shifts = get_shift_assignments(
				employee.employee, shift_condition, 
				start_date, last_day_of_month, EmployeeSchedule
			)

			for shift in shifts:
				doc.append(field_name, {
					"operations_shift": shift.shift,
					"count": shift.operations_shift_count
				})

			doc.insert()
		except Exception as e:
			frappe.log_error("Default Shift Checker Error", str(e))
			continue


def get_shift_assignments(employee_id, shift_condition, start_date, end_date, EmployeeSchedule):
	return (
		frappe.qb.from_(EmployeeSchedule)
		.select(
			EmployeeSchedule.shift,
			Count(EmployeeSchedule.shift).as_("operations_shift_count")
		)
		.where(
			(EmployeeSchedule.employee == employee_id)
			& shift_condition
			& (EmployeeSchedule.employee_availability == "Working")
			& (EmployeeSchedule.roster_type == "Basic")
			& (EmployeeSchedule.date[start_date:end_date])
		)
		.groupby(EmployeeSchedule.shift)
	).run(as_dict=True)