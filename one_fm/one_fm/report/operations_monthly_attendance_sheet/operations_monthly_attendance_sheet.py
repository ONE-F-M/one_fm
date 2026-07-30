# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, cint, cstr, date_diff, getdate, nowdate

status_map = {
	"Present": "P",
	"Absent": "A",
	"On Leave": "OL",
	"Holiday": "H",
	"Day Off": "DO"
}

day_abbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# A payroll extract can legitimately span a part-month or cross a month boundary, but
# one column per day has to stop somewhere: past this the table is unreadable and the
# query set grows without bound (WI-001790).
MAX_RANGE_DAYS = 62


def get_date_range(filters):
	"""The days the report covers, as date objects.

	Columns, both source queries and every per-day lookup are keyed off this one
	list, so the range is derived in a single place.
	"""
	from_date, to_date = getdate(filters.from_date), getdate(filters.to_date)
	return [add_days(from_date, offset) for offset in range(date_diff(to_date, from_date) + 1)]


def validate_filters(filters):
	if not (filters.get("from_date") and filters.get("to_date")):
		frappe.throw(_("Please select a From Date and a To Date."))

	from_date, to_date = getdate(filters.from_date), getdate(filters.to_date)
	if from_date > to_date:
		frappe.throw(_("From Date cannot be after To Date."))

	days = date_diff(to_date, from_date) + 1
	if days > MAX_RANGE_DAYS:
		frappe.throw(
			_("The selected range covers {0} days. Please choose {1} days or fewer.").format(
				days, MAX_RANGE_DAYS
			)
		)


def execute(filters):
	filters = frappe._dict(filters or {})

	# The report opens empty and is built only when Generate is clicked; a payroll
	# extract over every employee is too expensive to run on each filter change.
	if not cint(filters.get("generate")):
		return get_columns(filters, dates=[]), [], _(
			"Choose your filters, then click <b>Generate</b>."
		)

	validate_filters(filters)
	dates = get_date_range(filters)

	attendance_map = get_attendance_map(filters)
	if not attendance_map:
		frappe.msgprint(_("No attendance records found."), alert=True, indicator="orange")
		return get_columns(filters, dates), []

	schedule_map = {}
	if filters.get("include_future_attendance"):
		schedule_map = get_schedule_map(filters)

	columns = get_columns(filters, dates)
	data = get_data(filters, dates, attendance_map, schedule_map)

	if not data:
		frappe.msgprint(_("No attendance records found for this criteria."), alert=True, indicator="orange")
		return columns, []

	message = get_message()

	return columns, data, message


def get_columns(filters, dates):
	# Narrow fixed columns: the AC asks the table to fit the screen, and every extra
	# pixel here is taken from the day cells.
	columns = [
		{"label": _("Employee ID"), "fieldname": "employee_id", "fieldtype": "Data", "width": 90},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 110},
		{"label": _("Status"), "fieldname": "employee_status", "fieldtype": "Data", "width": 80},
		{"label": _("Employment Type"), "fieldname": "employment_type", "fieldtype": "Data", "width": 110},
		{"label": _("Roster Type"), "fieldname": "roster_type", "fieldtype": "Data", "width": 80},
		{"label": _("Day Off OT"), "fieldname": "day_off_ot", "fieldtype": "Check", "width": 70},
		{"label": _("Shift"), "fieldname": "shift", "fieldtype": "Data", "width": 90},
	]

	columns.extend(get_columns_for_days(dates))

	columns.extend([
		{"label": _("Working Days"), "fieldname": "working_days", "fieldtype": "Float", "width": 80},
		{"label": _("Days Off"), "fieldname": "off_days", "fieldtype": "Float", "width": 70},
	])

	return columns


def get_columns_for_days(dates):
	"""One column per day in the range, keyed by ISO date.

	Keyed by the date rather than the day-of-month it used to use: a range may cross a
	month boundary, where two different days would otherwise collide on the same key.
	"""
	days = []

	for date in dates:
		# e.g. "3 Aug Mon" - the month is needed once a range spans more than one.
		label = f"{date.day} {date.strftime('%b')} {day_abbr[date.weekday()]}"
		days.append(
			{"label": label, "fieldtype": "Data", "fieldname": cstr(date), "width": 65}
		)

	return days


def get_data(filters, dates, attendance_map, schedule_map):
	employee_details = get_employee_details(filters)
	data = get_rows(employee_details, filters, dates, attendance_map, schedule_map)

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
			leave_map.setdefault(d.employee, {}).setdefault(d.shift, []).append(d.day_key)
			continue

		if d.shift is None:
			d.shift = ""

		attendance_map.setdefault(d.employee, {}).setdefault(d.shift, {})
		attendance_map[d.employee][d.shift][d.day_key] = d.status

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
			Attendance.attendance_date.as_("day_key"),
			Attendance.status,
			OperationsShift.shift_classification.as_("shift"),
		)
		.where(
			(Attendance.docstatus == 1)
			& Attendance.attendance_date.between(filters.from_date, filters.to_date)
			& ~(Attendance.status.isin(["Day Off", "Client Day Off"]))
		)
		.orderby(Attendance.employee, Attendance.attendance_date)
	)

	if filters.get("project"):
		query = query.where(Attendance.project == filters.project)

	if filters.get("site"):
		query = query.where(Attendance.site == filters.site)

	if filters.get("roster_type"):
		query = query.where(Attendance.roster_type == filters.roster_type)

	if filters.get("day_off_ot"):
		query = query.where(Attendance.day_off_ot == 1)

	return query.run(as_dict=True)

def get_day_off_attendance_map(filters):
	Attendance = frappe.qb.DocType("Attendance")

	query = (
		frappe.qb.from_(Attendance)
		.select(
			Attendance.employee,
			Attendance.attendance_date.as_("day_key"),
			Attendance.status,
		)
		.where(
			(Attendance.docstatus == 1)
			& Attendance.attendance_date.between(filters.from_date, filters.to_date)
			& (Attendance.status.isin(["Day Off", "Client Day Off"]))
		)
		.orderby(Attendance.employee, Attendance.attendance_date)
	)

	day_off_records = query.run(as_dict=True)

	day_off_map = {}

	for record in day_off_records:
		day_off_map.setdefault(record.employee, {})[record.day_key] = record.status
		
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
			leave_map.setdefault(d.employee, {}).setdefault(d.shift, []).append(d.day_key)
			continue

		if d.shift is None:
			d.shift = ""

		schedule_map.setdefault(d.employee, {}).setdefault(d.shift, {})
		schedule_map[d.employee][d.shift][d.day_key] = d.status

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
			EmployeeSchedule.date.as_("day_key"),
			EmployeeSchedule.employee_availability.as_("status"),
			OperationsShift.shift_classification.as_("shift"),
		)
		.where(
			(EmployeeSchedule.date >= nowdate())
			& EmployeeSchedule.date.between(filters.from_date, filters.to_date)
			& ~(EmployeeSchedule.employee_availability.isin(["Day Off", "Client Day Off"]))
		)
		.orderby(EmployeeSchedule.employee, EmployeeSchedule.date)
	)

	if filters.get("project"):
		query = query.where(EmployeeSchedule.project == filters.project)

	if filters.get("site"):
		query = query.where(EmployeeSchedule.site == filters.site)

	if filters.get("roster_type"):
		query = query.where(EmployeeSchedule.roster_type == filters.roster_type)

	if filters.get("day_off_ot"):
		query = query.where(EmployeeSchedule.day_off_ot == 1)

	return query.run(as_dict=True)

def get_day_off_schedule_map(filters):
	EmployeeSchedule = frappe.qb.DocType("Employee Schedule")

	query = (
		frappe.qb.from_(EmployeeSchedule)
		.select(
			EmployeeSchedule.employee,
			EmployeeSchedule.date.as_("day_key"),
			EmployeeSchedule.employee_availability.as_("status"),
		)
		.where(
			(EmployeeSchedule.date >= nowdate())
			& EmployeeSchedule.date.between(filters.from_date, filters.to_date)
			& (EmployeeSchedule.employee_availability.isin(["Day Off", "Client Day Off"]))
		)
		.orderby(EmployeeSchedule.employee, EmployeeSchedule.date)
	)

	day_off_records = query.run(as_dict=True)

	day_off_map = {}

	for record in day_off_records:
		day_off_map.setdefault(record.employee, {})[record.day_key] = record.status
		
	return day_off_map

def get_employee_details(filters):
	Employee = frappe.qb.DocType("Employee")
	query = (
		frappe.qb.from_(Employee)
		.select(
			Employee.name,
			Employee.employee_id,
			Employee.employee_name,
			Employee.project,
			Employee.status.as_("employee_status"),
			Employee.employment_type,
		)
		.where(Employee.shift_working == 1)
	)

	if filters.get("employee"):
		query = query.where(Employee.name == filters.employee)

	# Unset means every status, so a payroll run can include leavers.
	if filters.get("employee_status"):
		query = query.where(Employee.status == filters.employee_status)

	if filters.get("employment_type"):
		query = query.where(Employee.employment_type == filters.employment_type)

	if filters.get("project"):
		query = query.where(Employee.project == filters.project)

	employee_details = query.run(as_dict=True)

	emp_map = {}

	for emp in employee_details:
		emp_map[emp.name] = emp

	return emp_map


def get_rows(employee_details, filters, dates, attendance_map, schedule_map):
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

		attendance_for_employee = get_attendance_status(
			dates,
			employee_attendance,
			employee_day_off_attendance,
			employee_schedule,
			employee_day_off_schedule,
		)

		# set employee details in the first row
		for record in attendance_for_employee:
			record.update({
				"employee_id": details.employee_id,
				"employee_name": details.employee_name,
				"project": details.project,
				"employee_status": details.employee_status,
				"employment_type": details.employment_type,
			})

		records.extend(attendance_for_employee)

	return records

def get_attendance_status(
	dates,
	employee_non_day_off_attendance,
	employee_day_off_attendance,
	employee_non_day_off_schedule,
	employee_day_off_schedule,
):
	"""Returns list of shift-wise attendance status for employee, keyed by ISO date
	[
			{'shift': 'Morning', '2026-08-01': 'A', '2026-08-02': 'P', ...},
			{'shift': 'Evening', '2026-08-01': 'P', '2026-08-02': 'A', ...}
	]
	"""
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

		for date in dates:
			status = attendance_dict.get(date)

			# if status is not found in non day attendance records, check day off attendance
			if not status:
				status = employee_day_off_attendance.get(date, "") or employee_day_off_schedule.get(date, "")

			if status in ["Present", "Working", "Work From Home"]:
				working_days += 1
			elif status in ["Day Off", "Client Day Off"]:
				off_days += 1

			abbr = attendance_status_map.get(status, "")
			row[cstr(date)] = abbr

		row["working_days"] = working_days
		row["off_days"] = off_days
		
		attendance_values.append(row)

	return attendance_values

@frappe.whitelist()
def get_report_additional_day_details(from_date, to_date):
	"""Day headers for the print template, over the selected range."""
	validate_filters(frappe._dict(from_date=from_date, to_date=to_date))

	days = []
	for date in get_date_range(frappe._dict(from_date=from_date, to_date=to_date)):
		days.append({
			"date": date.day,
			"month": date.strftime("%b"),
			"weekday": day_abbr[date.weekday()],
			"key": cstr(date),
		})

	return days

@frappe.whitelist()
def get_attendance_status_map():
	"""Returns the status map for attendance"""
	return status_map