# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Extract
from frappe.utils import cint, cstr
from calendar import monthrange
from frappe import _

class AttendanceAmendment(Document):
	@frappe.whitelist()
	def fetch_attendance_record(self):
		filters = self.get_attendance_amendment_filters()
		employee_details = get_employee_details()
		attendance_map = get_attendance_map(filters, self.attendance_based_on)
		data = get_rows(employee_details, filters, attendance_map, self.attendance_based_on)
		if data:
			self.update_attendance_records(data)
		else:
			frappe.msgprint(_("No attendance records found."), alert=True, indicator="orange")

		if self.ot_data_required:
			ot_attendance_map = get_ot_attendance_map(filters)
			ot_data = get_ot_rows(employee_details, filters, ot_attendance_map)
			if ot_data:
				self.update_attendance_records(ot_data, type="Overtime")
			else:
				frappe.msgprint(_("No OT attendance records found."), alert=True, indicator="orange")

	def get_attendance_amendment_filters(self):
		month_map = { 
			"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
			"July": 7, "August": 8, "September": 9, "October": 10, "November": 11,
			"December": 12
		}
		filters = {
			"month": month_map.get(self.month),
			"year": self.year
		}
		if self.project:
			filters["project"] = self.project
		if self.site:
			filters["site"] = self.site
		return frappe._dict(filters)

	def update_attendance_records(self, data, type="Basic"):
		if not self.attendance_based_on:
			return
		child_table = "overtime_details" if type == "Overtime" else "attendance_details"
		self.set(child_table, [])
		for record in data:
			if type == "Overtime" or self.attendance_based_on == "Shift Hours":
				day_fields = {f"day_{i}_hour": record.get(str(i), 'N/A' if type == "Overtime" else '') for i in range(1, 32)}
			else:
				day_fields = {f"day_{i}": record.get(str(i), '') for i in range(1, 32)}

			self.append(child_table, {
				"employee": record.get("employee"),
				"employee_id": record.get("employee_id"),
				"employee_name": record.get("employee_name"),
				"sale_item": record.get("sale_item"),
				"shift": record.get("shift"),
				"working_days": record.get("working_days"),
				"off_days": record.get("off_days"),
				**day_fields
			})

def get_employee_details():
	Employee = frappe.qb.DocType("Employee")
	OperationsRole = frappe.qb.DocType("Operations Role")
	query = (
		frappe.qb.from_(Employee)
		.left_join(OperationsRole)
		.on(Employee.custom_operations_role_allocation == OperationsRole.name)
		.select(
			Employee.name,
			Employee.employee_id,
			Employee.employee_name,
			OperationsRole.sale_item
		)
		.where(Employee.shift_working == 1)
	)

	employee_details = query.run(as_dict=True)

	emp_map = {}

	for emp in employee_details:
		emp_map[emp.name] = emp

	return emp_map

def get_attendance_map(filters, attendance_based_on=None):
	"""Returns a dictionary of employee wise attendance map as per shifts for all the days of the month like
	{
		'employee1': {
				'Morning': {1: 'Present', 2: 'Absent', ...}
				'Evening': {1: 'Absent', 2: 'Present', ...}
		},
		'employee2': {
				'Afternoon': {1: 'Present', 2: 'Absent', ...}
				'Night': {1: 'Absent', 2: 'Absent', ...}
		},
		'employee3': {
				None: {1: 'On Leave'}
		}
	}
	"""
	non_day_off_attendance_records = get_non_day_off_attendance_records(filters)

	attendance_map = {}
	leave_map = {}

	for d in non_day_off_attendance_records:
		if d.status == "On Leave":
			leave_map.setdefault(d.employee, {}).setdefault(d.shift, []).append(d.day_of_month)
			continue

		if d.shift is None:
			d.shift = ""

		attendance_map.setdefault(d.employee, {}).setdefault(d.shift, {})
		attendance_map[d.employee][d.shift][d.day_of_month] = d.status if attendance_based_on == "Attendance Status" else d.working_hours

	# leave is applicable for the entire day so all shifts should show the leave entry
	for employee, leave_days in leave_map.items():
		for assigned_shift, days in leave_days.items():
			# no attendance records exist except leaves
			if employee not in attendance_map:
				attendance_map.setdefault(employee, {}).setdefault(assigned_shift, {})

			for day in days:
				for shift in attendance_map[employee].keys():
					attendance_map[employee][shift][day] = "On Leave"

	return attendance_map

def get_non_day_off_attendance_records(filters):
	Attendance = frappe.qb.DocType("Attendance")
	OperationsShift = frappe.qb.DocType("Operations Shift")

	query = (
		frappe.qb.from_(Attendance)
		.join(OperationsShift)
		.on(Attendance.operations_shift == OperationsShift.name)
		.select(
			Attendance.employee,
			Extract("day", Attendance.attendance_date).as_("day_of_month"),
			Attendance.status,
			OperationsShift.shift_classification.as_("shift"),
			Attendance.working_hours
		)
		.where(
			(Attendance.docstatus == 1)
			& (Extract("month", Attendance.attendance_date) == filters.month)
			& (Extract("year", Attendance.attendance_date) == filters.year)
			& ~(Attendance.status.isin(["Day Off", "Client Day Off"]))
			& (Attendance.roster_type == "Basic")
		)
		.orderby(Attendance.employee, Attendance.attendance_date)
	)

	if filters.get("project"):
		query = query.where(Attendance.project == filters.project)

	if filters.get("site"):
		query = query.where(Attendance.site == filters.site)

	return query.run(as_dict=True)

def get_rows(employee_details, filters, attendance_map, attendance_based_on):
	records = []

	day_off_attendance_map = get_day_off_attendance_map(filters)

	for employee, details in employee_details.items():
		employee_attendance = attendance_map.get(employee)

		employee_day_off_attendance = day_off_attendance_map.get(employee, {})

		if not employee_attendance:
			# no attendance records found for employee
			continue

		attendance_for_employee = get_attendance_status(filters, employee_attendance, employee_day_off_attendance, attendance_based_on)

		# set employee details in the first row
		for record in attendance_for_employee:
			record.update({
				"employee": details.name,
				"employee_id": details.employee_id,
				"employee_name": details.employee_name,
				"sale_item": details.sale_item
			})

		records.extend(attendance_for_employee)

	return records

def get_day_off_attendance_map(filters, roster_type="Basic"):
	Attendance = frappe.qb.DocType("Attendance")

	query = (
		frappe.qb.from_(Attendance)
		.select(
			Attendance.employee,
			Extract("day", Attendance.attendance_date).as_("day_of_month"),
			Attendance.status,
			Attendance.working_hours
		)
		.where(
			(Attendance.docstatus == 1)
			& (Extract("month", Attendance.attendance_date) == filters.month)
			& (Extract("year", Attendance.attendance_date) == filters.year)
			& (Attendance.status.isin(["Day Off", "Client Day Off"]))
			& (Attendance.roster_type == roster_type)
		)
		.orderby(Attendance.employee, Attendance.attendance_date)
	)

	day_off_records = query.run(as_dict=True)

	day_off_map = {}

	for record in day_off_records:
		day_off_map.setdefault(record.employee, {})[record.day_of_month] = record.status
		
	return day_off_map

def get_attendance_status(filters, employee_non_day_off_attendance, employee_day_off_attendance=None, attendance_based_on=None):
	"""Returns list of shift-wise attendance status for employee
	[
			{'shift': 'Morning', 1: 'A', 2: 'P', 3: 'A'....},
			{'shift': 'Evening', 1: 'P', 2: 'A', 3: 'P'....}
	]
	"""
	total_days = monthrange(cint(filters.year), cint(filters.month))[1]
	attendance_values = []

	employee_non_day_off_attendance = employee_non_day_off_attendance or {}

	shifts = set(employee_non_day_off_attendance.keys())

	for shift in shifts:
		row = {"shift": shift}

		# Merge Attendance and Schedule statuses
		attendance_dict = { **employee_non_day_off_attendance.get(shift, {})}

		working_days = 0
		off_days = 0

		for day in range(1, total_days + 1):
			status = attendance_dict.get(day)

			# if status is not found in non day attendance records, check day off attendance
			if attendance_based_on == "Attendance Status":
				if not status and employee_day_off_attendance:
					status = employee_day_off_attendance.get(day, "")
				if status in ["Present", "Working", "Work From Home"]:
					working_days += 1

			if attendance_based_on == "Shift Hours":
				if not status and employee_day_off_attendance:
					status = employee_day_off_attendance.get(day, 0)
				if status and status not in ["Day Off", "Client Day Off", "Absent", "On Leave"]: # For Shift Hours, status contains the working hours value
					working_days += 1

			if status in ["Day Off", "Client Day Off"]:
				off_days += 1

			row[cstr(day)] = status

		row["working_days"] = working_days
		row["off_days"] = off_days
		
		attendance_values.append(row)

	return attendance_values

def get_ot_attendance_map(filters):
	non_day_off_attendance_records = get_ot_attendance_records(filters)

	attendance_map = {}

	for d in non_day_off_attendance_records:
		if d.shift is None:
			d.shift = ""

		attendance_map.setdefault(d.employee, {}).setdefault(d.shift, {})
		attendance_map[d.employee][d.shift][d.day_of_month] = d.working_hours

	return attendance_map

def get_ot_attendance_records(filters):
	Attendance = frappe.qb.DocType("Attendance")
	OperationsShift = frappe.qb.DocType("Operations Shift")

	query = (
		frappe.qb.from_(Attendance)
		.join(OperationsShift)
		.on(Attendance.operations_shift == OperationsShift.name)
		.select(
			Attendance.employee,
			Extract("day", Attendance.attendance_date).as_("day_of_month"),
			Attendance.status,
			OperationsShift.shift_classification.as_("shift"),
			Attendance.working_hours
		)
		.where(
			(Attendance.docstatus == 1)
			& (Extract("month", Attendance.attendance_date) == filters.month)
			& (Extract("year", Attendance.attendance_date) == filters.year)
			& ~(Attendance.status.isin(["Day Off", "Client Day Off"]))
			& (Attendance.roster_type == "Over-Time")
		)
		.orderby(Attendance.employee, Attendance.attendance_date)
	)

	if filters.get("project"):
		query = query.where(Attendance.project == filters.project)

	if filters.get("site"):
		query = query.where(Attendance.site == filters.site)

	return query.run(as_dict=True)

def get_ot_rows(employee_details, filters, attendance_map):
	records = []

	day_off_attendance_map = get_day_off_attendance_map(filters, "Over-Time")

	for employee, details in employee_details.items():
		employee_attendance = attendance_map.get(employee)
		employee_day_off_attendance = day_off_attendance_map.get(employee, {})
		if not employee_attendance:
			# no attendance records found for employee
			continue

		attendance_for_employee = get_attendance_status(filters, employee_attendance, employee_day_off_attendance, "Shift Hours")

		# set employee details in the first row
		for record in attendance_for_employee:
			record.update({
				"employee": details.name,
				"employee_id": details.employee_id,
				"employee_name": details.employee_name,
				"sale_item": details.sale_item
			})

		records.extend(attendance_for_employee)

	return records