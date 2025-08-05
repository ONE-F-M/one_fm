# Copyright (c) 2025, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Extract
from frappe.utils import cint, cstr, getdate
from calendar import monthrange

status_map = {
	"Present": "P",
	"Absent": "A",
	"Work From Home": "WFH",
	"On Leave": "OL",
	"Holiday": "H",
	"Day Off": "DO",
	"Client Day Off": "CDO"
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

	columns = get_columns(filters)
	data = get_data(filters, attendance_map)

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


def get_data(filters, attendance_map):
	employee_details = get_employee_details()
	data = get_rows(employee_details, filters, attendance_map)

	return data

def get_message():
	message = ""
	colors = ["green", "red", "green", "red", "blue", "blue", "blue"]

	count = 0
	for status, abbr in status_map.items():
		message += f"""
			<span style='border-left: 2px solid {colors[count]}; padding-right: 12px; padding-left: 5px; margin-right: 3px;'>
				{status} - {abbr}
			</span>
		"""
		count += 1

	return message


def get_attendance_map(filters):
	"""Returns a dictionary of employee wise attendance map as per shifts for all the days of the month like
	{
	    'employee1': {
	            'Morning Shift': {1: 'Present', 2: 'Absent', ...}
	            'Evening Shift': {1: 'Absent', 2: 'Present', ...}
	    },
	    'employee2': {
	            'Afternoon Shift': {1: 'Present', 2: 'Absent', ...}
	            'Night Shift': {1: 'Absent', 2: 'Absent', ...}
	    },
	    'employee3': {
	            None: {1: 'On Leave'}
	    }
	}
	"""
	attendance_list = get_attendance_records(filters)
	attendance_map = {}
	leave_map = {}

	for d in attendance_list:
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


def get_attendance_records(filters):
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
        )
        .orderby(Attendance.employee, Attendance.attendance_date)
    )

    if filters.get("project"):
        query = query.where(Attendance.project == filters.project)

    if filters.get("site"):
        query = query.where(Attendance.site == filters.site)

    return query.run(as_dict=1)

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


def get_rows(employee_details, filters, attendance_map):
	records = []

	for employee, details in employee_details.items():

		employee_attendance = attendance_map.get(employee)
		if not employee_attendance:
			continue

		attendance_for_employee = get_attendance_status(
			filters, employee_attendance
		)
		# set employee details in the first row
		for record in attendance_for_employee:
			record.update({"employee_id": details.employee_id, "employee_name": details.employee_name})

		records.extend(attendance_for_employee)

	return records

def get_attendance_status(filters, employee_attendance):
	"""Returns list of shift-wise attendance status for employee
	[
	        {'shift': 'Morning Shift', 1: 'A', 2: 'P', 3: 'A'....},
	        {'shift': 'Evening Shift', 1: 'P', 2: 'A', 3: 'P'....}
	]
	"""
	total_days = monthrange(cint(filters.year), cint(filters.month))[1]
	attendance_values = []

	for shift, status_dict in employee_attendance.items():
		row = {"shift": shift}

		working_days = 0
		off_days = 0

		for day in range(1, total_days + 1):
			status = status_dict.get(day)

			if status == "Present":
				working_days += 1
			elif status in ["Day Off", "Client Day Off"]:
				off_days += 1

			abbr = status_map.get(status, "")
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