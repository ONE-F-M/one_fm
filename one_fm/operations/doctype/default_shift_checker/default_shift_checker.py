# Copyright (c) 2024, omar jaber and contributors
# For license information, please see license.txt
import frappe
from collections import defaultdict
from frappe.model.document import Document
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count
from frappe.utils import getdate, get_first_day, get_last_day, add_days, add_months, nowdate

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
			"Mark Employee as Day Off Reliever": {
				"custom_is_reliever": 1,
				"custom_is_weekend_reliever": 0
			},
			"Mark Employee as Weekend Reliever": {
				"custom_is_reliever": 0,
				"custom_is_weekend_reliever": 1
			},
			"UnMark Employee as Day Off Reliever": {
				"custom_is_reliever": 0
			},
			"UnMark Employee as Weekend Reliever": {
				"custom_is_weekend_reliever": 0
			},
		}

		if self.action_type in field_updates:
			employee.update(field_updates[self.action_type])
			employee.save()

		self.db_set("status", "Completed")


def create_default_shift_checker():
	tomorrow = add_days(getdate(), 1)
	next_month = add_months(tomorrow, 1)

	durations = [
		{
			"start_date": tomorrow,
			"end_date": get_last_day(tomorrow)
		},
		{
			"start_date": get_first_day(next_month),
			"end_date": get_last_day(next_month)
		},
	]

	for duration in durations:
		# For normal employees
		create_checker(duration["start_date"], duration["end_date"])

		# For day off relievers
		create_checker(duration["start_date"], duration["end_date"], is_day_off_reliever=True)

		# For weekend relievers
		create_checker(duration["start_date"], duration["end_date"], is_weekend_reliever=True)


def create_checker(start_date, end_date, is_day_off_reliever=False, is_weekend_reliever=False):
	"""
	Unified function to create Default Shift Checker records for both regular employees and relievers
	"""
	Employee = frappe.qb.DocType("Employee")
	EmployeeSchedule = frappe.qb.DocType("Employee Schedule")
	Project = frappe.qb.DocType("Project")

	is_reliever = is_day_off_reliever or is_weekend_reliever

	# Threshold field
	threshold_field = "default_shift_checker_threshold"
	if is_day_off_reliever: threshold_field = "day_off_reliever_default_shift_checker_threshold"
	elif is_weekend_reliever: threshold_field = "weekend_reliever_default_shift_checker_threshold"


	threshold = frappe.db.get_single_value("ONEFM General Setting", threshold_field) or 0
	child_table_field_name = "reliever_assigned_to_the_same_shift" if is_reliever else "assigned_shifts_outside_default_shift"

	# Start building conditions
	conditions = (
		(Employee.status == "Active") &
		(Employee.shift_working == 1) &
		(Employee.shift.isnotnull()) &
		(EmployeeSchedule.employee_availability == "Working") &
		(EmployeeSchedule.roster_type == "Basic") &
		(EmployeeSchedule.date.between(start_date, end_date)) &
		(Project.custom_exclude_from_default_shift_checker != 1)
	)

	# Shift Condition
	if is_reliever:
		conditions &= (EmployeeSchedule.shift == Employee.shift)
	else:
		conditions &= (EmployeeSchedule.shift != Employee.shift)

	# Reliever Condition
	if is_day_off_reliever:
		conditions &= (Employee.custom_is_reliever == 1)
	elif is_weekend_reliever:
		conditions &= (Employee.custom_is_weekend_reliever == 1)
	else:
		conditions &= ((Employee.custom_is_reliever == 0) & (Employee.custom_is_weekend_reliever == 0))

	query = (
		frappe.qb.from_(Employee)
		.join(EmployeeSchedule).on(Employee.name == EmployeeSchedule.employee)
		.left_join(Project).on(Employee.project == Project.name)
		.select(
			Employee.name.as_("employee"),
			Employee.shift.as_("default_shift"),
			Employee.site.as_("default_site")
		)
		.where(conditions)
		.groupby(Employee.name)
		.having(Count(EmployeeSchedule.shift) > threshold)
	)

	# Create Default Shift Checker records
	for employee in query.run(as_dict=True):
		try:
			yesterday_repeat_count = frappe.db.get_value(
				"Default Shift Checker",
				{
					"employee": employee.employee,
					# If start date lies within current month then check for yesterday else check for first day of month (for next month)
					"start_date": add_days(start_date, -1) if getdate(start_date).month == getdate(nowdate()).month and getdate(start_date).year == getdate(nowdate()).year else get_first_day(start_date),
					"creation": ["between", [add_days(nowdate(), -1), nowdate()]],
				},
				["repeat_count"]
			)

			doc = frappe.new_doc("Default Shift Checker")
			doc.employee = employee.employee
			doc.start_date = start_date
			doc.end_date = end_date
			doc.repeat_count = (yesterday_repeat_count or 0) + 1
			doc.site_supervisor = frappe.db.get_value("Operations Site", employee.default_site, "account_supervisor")

			if is_day_off_reliever:
				doc.is_day_off_reliever = 1
			if is_weekend_reliever:
				doc.is_weekend_reliever = 1

			# Determine shift condition
			shift_condition = (EmployeeSchedule.shift == employee.default_shift) if is_reliever else (EmployeeSchedule.shift != employee.default_shift)
			shifts = get_shift_assignments(employee.employee, shift_condition, start_date, end_date, EmployeeSchedule)

			for shift_name, data in shifts.items():
				doc.append(child_table_field_name, {
					"operations_shift": shift_name,
					"schedule_dates": data["dates"],
					"count": data["count"]
				})

			doc.insert()
		except Exception as e:
			frappe.log_error("Default Shift Checker Error", str(e))


def get_shift_assignments(employee_id, shift_condition, start_date, end_date, EmployeeSchedule):
    records = (
        frappe.qb.from_(EmployeeSchedule)
        .select(EmployeeSchedule.shift, EmployeeSchedule.date)
        .where(
            (EmployeeSchedule.employee == employee_id)
            & shift_condition
            & (EmployeeSchedule.employee_availability == "Working")
            & (EmployeeSchedule.roster_type == "Basic")
            & EmployeeSchedule.date.between(start_date, end_date)
        )
    ).run(as_dict=True)

    result = defaultdict(lambda: {"dates": [], "count": 0})

    for row in records:
        shift = row["shift"]
        date_str = row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])
        result[shift]["dates"].append(date_str)
        result[shift]["count"] += 1

    for shift in result:
        result[shift]["dates"] = ", ".join(result[shift]["dates"])

    return dict(result)