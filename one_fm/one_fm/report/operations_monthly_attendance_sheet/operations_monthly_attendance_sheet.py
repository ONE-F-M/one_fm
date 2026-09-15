# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Extract
from frappe.utils import cint, cstr, getdate, nowdate
from calendar import monthrange

status_map = {
	"Present": "P",
	"Absent": "A",
	"On Leave": "OL",
	"Holiday": "H",
	"Day Off": "DO"
}

day_abbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def execute(filters):
	filters = frappe._dict(filters or {})

	if not (filters.month and filters.year):
		frappe.throw(_("Please select month and year."))

	attendance_map = get_attendance_map(filters)
	if not attendance_map:
		frappe.msgprint(_("No attendance records found."), alert=True, indicator="orange")
		return [], []
	
	schedule_map = {}
	if filters.get("include_future_attendance"):
		schedule_map = get_schedule_map(filters)

	columns = get_columns(filters)
	data = get_data(filters, attendance_map, schedule_map)

	if not data:
		frappe.msgprint(_("No attendance records found for this criteria."), alert=True, indicator="orange")
		return columns, []
	
	message = get_message()

	return columns, data, message


def get_columns(filters):
	columns = [
		{
			"label": _("Employee ID"),
			"fieldname": "employee_id",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Shift"),
			"fieldname": "shift",
			"fieldtype": "Data",
			"width": 120
		},
	]

	columns.extend(get_columns_for_days(filters))

	return columns


def get_columns_for_days(filters):
	total_days = monthrange(cint(filters.year), cint(filters.month))[1]
	days = []

	for day in range(1, total_days + 1):
		day = cstr(day)
		# forms the dates from selected year and month from filters
		date = f"{cstr(filters.year)}-{cstr(filters.month)}-{day}"
		# gets abbr from weekday number
		weekday = day_abbr[getdate(date).weekday()]
		# sets days as 1 Mon, 2 Tue, 3 Wed
		label = f"{day} {weekday}"
		days.append({"label": label, "fieldtype": "Data", "fieldname": day, "width": 65})

	return days


def get_data(filters, attendance_map, schedule_map):
	employee_details = get_employee_details()
	data = get_rows(employee_details, filters, attendance_map, schedule_map)

	return data

def get_message():
	message = ""
	colors_map = { "P": "green","A": "red","OL": "red","H": "blue","DO": "blue","CDO": "blue" }
	legend_status_map = { **status_map, "Work From Home": "P", "Client Day Off": "CDO" }

	count = 0
	for status, abbr in legend_status_map.items():
		message += f"""
			<span style='border-left: 2px solid {colors_map[abbr]}; padding-right: 12px; padding-left: 5px; margin-right: 3px;'>
				{status} - {abbr}
			</span>
		"""
		count += 1

	return message


def get_attendance_map(filters):
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
		attendance_map[d.employee][d.shift][d.day_of_month] = d.status

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
		)
		.where(
			(Attendance.docstatus == 1)
			& (Extract("month", Attendance.attendance_date) == filters.month)
			& (Extract("year", Attendance.attendance_date) == filters.year)
			& ~(Attendance.status.isin(["Day Off", "Client Day Off"]))
		)
		.orderby(Attendance.employee, Attendance.attendance_date)
	)

	if filters.get("project"):
		query = query.where(Attendance.project == filters.project)

	if filters.get("site"):
		query = query.where(Attendance.site == filters.site)

	return query.run(as_dict=True)

def get_day_off_attendance_map(filters):
	Attendance = frappe.qb.DocType("Attendance")

	query = (
		frappe.qb.from_(Attendance)
		.select(
			Attendance.employee,
			Extract("day", Attendance.attendance_date).as_("day_of_month"),
			Attendance.status,
		)
		.where(
			(Attendance.docstatus == 1)
			& (Extract("month", Attendance.attendance_date) == filters.month)
			& (Extract("year", Attendance.attendance_date) == filters.year)
			& (Attendance.status.isin(["Day Off", "Client Day Off"]))
		)
		.orderby(Attendance.employee, Attendance.attendance_date)
	)

	day_off_records = query.run(as_dict=True)

	day_off_map = {}

	for record in day_off_records:
		day_off_map.setdefault(record.employee, {})[record.day_of_month] = record.status
		
	return day_off_map


def get_schedule_map(filters):
	"""Returns a dictionary of employee wise schedule map as per shifts for all the days of the month like
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
	non_day_off_schedule_records = get_non_day_off_schedule_records(filters)

	schedule_map = {}
	leave_map = {}

	for d in non_day_off_schedule_records:
		if d.status in ["Annual Leave"]:
			leave_map.setdefault(d.employee, {}).setdefault(d.shift, []).append(d.day_of_month)
			continue

		if d.shift is None:
			d.shift = ""

		schedule_map.setdefault(d.employee, {}).setdefault(d.shift, {})
		schedule_map[d.employee][d.shift][d.day_of_month] = d.status

	# leave is applicable for the entire day so all shifts should show the leave entry
	for employee, leave_days in leave_map.items():
		for assigned_shift, days in leave_days.items():
			# no schedule records exist except leaves
			if employee not in schedule_map:
				schedule_map.setdefault(employee, {}).setdefault(assigned_shift, {})

			for day in days:
				for shift in schedule_map[employee].keys():
					schedule_map[employee][shift][day] = "Annual Leave"

	return schedule_map

def get_non_day_off_schedule_records(filters):
	EmployeeSchedule = frappe.qb.DocType("Employee Schedule")
	OperationsShift = frappe.qb.DocType("Operations Shift")

	query = (
		frappe.qb.from_(EmployeeSchedule)
		.join(OperationsShift)
		.on(EmployeeSchedule.shift == OperationsShift.name)
		.select(
			EmployeeSchedule.employee,
			Extract("day", EmployeeSchedule.date).as_("day_of_month"),
			EmployeeSchedule.employee_availability.as_("status"),
			OperationsShift.shift_classification.as_("shift"),
		)
		.where(
			(EmployeeSchedule.date >= nowdate())
			& (Extract("month", EmployeeSchedule.date) == filters.month)
			& (Extract("year", EmployeeSchedule.date) == filters.year)
			& ~(EmployeeSchedule.employee_availability.isin(["Day Off", "Client Day Off"]))
		)
		.orderby(EmployeeSchedule.employee, EmployeeSchedule.date)
	)

	if filters.get("project"):
		query = query.where(EmployeeSchedule.project == filters.project)

	if filters.get("site"):
		query = query.where(EmployeeSchedule.site == filters.site)

	return query.run(as_dict=True)

def get_day_off_schedule_map(filters):
	EmployeeSchedule = frappe.qb.DocType("Employee Schedule")

	query = (
		frappe.qb.from_(EmployeeSchedule)
		.select(
			EmployeeSchedule.employee,
			Extract("day", EmployeeSchedule.date).as_("day_of_month"),
			EmployeeSchedule.employee_availability.as_("status"),
		)
		.where(
			(EmployeeSchedule.date >= nowdate())
			& (Extract("month", EmployeeSchedule.date) == filters.month)
			& (Extract("year", EmployeeSchedule.date) == filters.year)
			& (EmployeeSchedule.employee_availability.isin(["Day Off", "Client Day Off"]))
		)
		.orderby(EmployeeSchedule.employee, EmployeeSchedule.date)
	)

	day_off_records = query.run(as_dict=True)

	day_off_map = {}

	for record in day_off_records:
		day_off_map.setdefault(record.employee, {})[record.day_of_month] = record.status
		
	return day_off_map

def get_employee_details():
	Employee = frappe.qb.DocType("Employee")
	query = (
		frappe.qb.from_(Employee)
		.select(
			Employee.name,
			Employee.employee_id,
			Employee.employee_name,
		)
		.where(Employee.shift_working == 1)
	)

	employee_details = query.run(as_dict=True)

	emp_map = {}

	for emp in employee_details:
		emp_map[emp.name] = emp

	return emp_map


def get_rows(employee_details, filters, attendance_map, schedule_map):
	records = []

	day_off_attendance_map = get_day_off_attendance_map(filters)
	day_off_schedule_map = get_day_off_schedule_map(filters) if filters.get("include_future_attendance") else {}

	for employee, details in employee_details.items():

		employee_attendance = attendance_map.get(employee)
		employee_schedule = schedule_map.get(employee)

		employee_day_off_attendance = day_off_attendance_map.get(employee, {})
		employee_day_off_schedule = day_off_schedule_map.get(employee, {})

		if not (employee_attendance or employee_schedule):
			# no attendance or schedule records found for employee
			continue

		attendance_for_employee = get_attendance_status(filters, employee_attendance, employee_day_off_attendance, employee_schedule, employee_day_off_schedule)

		# set employee details in the first row
		for record in attendance_for_employee:
			record.update({"employee_id": details.employee_id, "employee_name": details.employee_name})

		records.extend(attendance_for_employee)

	return records

def get_attendance_status(filters, employee_non_day_off_attendance, employee_day_off_attendance, employee_non_day_off_schedule, employee_day_off_schedule):
	"""Returns list of shift-wise attendance status for employee
	[
			{'shift': 'Morning', 1: 'A', 2: 'P', 3: 'A'....},
			{'shift': 'Evening', 1: 'P', 2: 'A', 3: 'P'....}
	]
	"""
	total_days = monthrange(cint(filters.year), cint(filters.month))[1]
	attendance_values = []

	attendance_status_map = { 
		**status_map, 
		"Work From Home": "P", 
		"Working": "P", 
		"Client Day Off": "CDO",
		"Sick Leave": "OL",
		"Annual Leave": "OL",
		"Emergency Leave": "OL"
	}

	employee_non_day_off_attendance = employee_non_day_off_attendance or {}
	employee_non_day_off_schedule = employee_non_day_off_schedule or {}

	shifts = set(employee_non_day_off_attendance.keys()) | set(employee_non_day_off_schedule.keys())

	for shift in shifts:
		row = {"shift": shift}

		# Merge Attendance and Schedule statuses
		attendance_dict = { **employee_non_day_off_attendance.get(shift, {}), **employee_non_day_off_schedule.get(shift, {}) }

		working_days = 0
		off_days = 0

		for day in range(1, total_days + 1):
			status = attendance_dict.get(day)

			# if status is not found in non day attendance records, check day off attendance
			if not status:
				status = employee_day_off_attendance.get(day, "") or employee_day_off_schedule.get(day, "")

			if status in ["Present", "Working", "Work From Home"]:
				working_days += 1
			elif status in ["Day Off", "Client Day Off"]:
				off_days += 1

			abbr = attendance_status_map.get(status, "")
			row[cstr(day)] = abbr

		row["working_days"] = working_days
		row["off_days"] = off_days
		
		attendance_values.append(row)

	return attendance_values

@frappe.whitelist()
def get_attendance_years():
	"""Returns all the years for which attendance records exist"""
	Attendance = frappe.qb.DocType("Attendance")
	year_list = (
		frappe.qb.from_(Attendance).select(Extract("year", Attendance.attendance_date).as_("year")).distinct()
	).run(as_dict=True)

	if year_list:
		year_list.sort(key=lambda d: d.year, reverse=True)
	else:
		year_list = [frappe._dict({"year": getdate().year})]

	return "\n".join(cstr(entry.year) for entry in year_list)

@frappe.whitelist()
def get_report_additional_day_details(month, year):
	total_days = monthrange(cint(year), cint(month))[1]
	days = []

	for date in range(1, total_days + 1):
		weekday = day_abbr[getdate(f"{cstr(year)}-{cstr(month)}-{cstr(date)}").weekday()]
		days.append({"date": date, "weekday": weekday})

	return days

@frappe.whitelist()
def get_attendance_status_map():
	"""Returns the status map for attendance"""
	return status_map