# Copyright (c) 2026, One FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import getdate, today


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)

	message = None
	if not data:
		message = _("No reliever records found for the selected criteria.")

	report_summary = get_report_summary(data)

	return columns, data, message, None, report_summary


def get_columns():
	return [
		{
			"fieldname": "employee_schedule",
			"label": _("Employee Schedule"),
			"fieldtype": "Link",
			"options": "Employee Schedule",
			"width": 220,
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "employee",
			"label": _("Employee ID"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 150,
		},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 150,
		},
		{
			"fieldname": "operations_role",
			"label": _("Operations Role"),
			"fieldtype": "Link",
			"options": "Operations Role",
			"width": 150,
		},
		{
			"fieldname": "operations_site",
			"label": _("Operations Site"),
			"fieldtype": "Link",
			"options": "Operations Site",
			"width": 150,
		},
		{
			"fieldname": "shift_classification",
			"label": _("Shift Classification"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "reason_for_relief",
			"label": _("Reason for Relief"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "replaced_employee_schedule",
			"label": _("Replaced Employee Schedule"),
			"fieldtype": "Link",
			"options": "Employee Schedule",
			"width": 220,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 110,
		},
	]


def get_data(filters):
	records = get_raw_records(filters)

	if not records:
		return []

	# Collect all schedule names and replaced schedule IDs for batch lookups
	schedule_names = [r.schedule_name for r in records]
	replaced_schedule_ids = list(set([
		r.replaced_employee_schedule for r in records
		if r.replaced_employee_schedule
	]))

	# Batch fetch: reason for relief from replaced employee schedules
	reason_map = get_reason_for_relief_map(replaced_schedule_ids)

	# Batch fetch: shift assignments linked to these employee schedules
	shift_assignment_map = get_shift_assignment_map(schedule_names)

	# Get all shift assignment names for attendance/checkin lookups
	all_sa_names = list(shift_assignment_map.values())

	# Batch fetch: attendance records
	attendance_map = get_attendance_map(all_sa_names)

	# Batch fetch: employee checkins (only needed for today's records)
	checkin_map = get_checkin_map(all_sa_names)

	today_date = getdate(today())

	# Build the result rows with status
	result = []
	for record in records:
		schedule_date = getdate(record.date)
		sa_name = shift_assignment_map.get(record.schedule_name)

		# Derive status
		status = derive_status(schedule_date, today_date, sa_name, attendance_map, checkin_map)

		# Get reason for relief from the replaced employee's schedule
		reason = reason_map.get(record.replaced_employee_schedule, "")

		result.append({
			"employee_schedule": record.schedule_name,
			"employee_name": record.employee_name,
			"employee": record.employee,
			"project": record.project,
			"operations_role": record.operations_role,
			"operations_site": record.operations_site,
			"shift_classification": record.shift_classification,
			"date": record.date,
			"reason_for_relief": reason,
			"replaced_employee_schedule": record.replaced_employee_schedule,
			"status": status,
		})

	return result


def get_raw_records(filters):
	ES = DocType("Employee Schedule")
	OS = DocType("Operations Shift")

	query = (
		frappe.qb.from_(ES)
		.left_join(OS).on(ES.shift == OS.name)
		.select(
			ES.name.as_("schedule_name"),
			ES.employee,
			ES.employee_name,
			ES.date,
			ES.operations_role,
			ES.shift,
			OS.site.as_("operations_site"),
			OS.project,
			OS.shift_classification,
			ES.relieving_employee_schedule.as_("replaced_employee_schedule"),
		)
		.where(ES.is_relieving_schedule == 1)
		.orderby(ES.date)
	)

	query = apply_filters(query, filters, ES, OS)

	return query.run(as_dict=True)


def apply_filters(query, filters, ES, OS):
	if not filters:
		return query

	if filters.get("employee"):
		query = query.where(ES.employee == filters["employee"])

	if filters.get("project"):
		query = query.where(OS.project == filters["project"])

	if filters.get("operations_site"):
		query = query.where(OS.site == filters["operations_site"])

	if filters.get("from_date"):
		query = query.where(ES.date >= filters["from_date"])

	if filters.get("to_date"):
		query = query.where(ES.date <= filters["to_date"])

	return query


def get_reason_for_relief_map(schedule_ids):
	"""
	Fetch the employee_availability (Reason for Relief) from the
	replaced employee's Employee Schedule records.
	"""
	if not schedule_ids:
		return {}

	ES = DocType("Employee Schedule")
	records = (
		frappe.qb.from_(ES)
		.select(ES.name, ES.employee_availability)
		.where(ES.name.isin(schedule_ids))
	).run(as_dict=True)

	return {r.name: r.employee_availability for r in records}


def get_shift_assignment_map(schedule_names):
	"""
	Fetch Shift Assignment names linked to the given Employee Schedule names.
	Returns a map of {employee_schedule_name: shift_assignment_name}.
	"""
	if not schedule_names:
		return {}

	SA = DocType("Shift Assignment")
	records = (
		frappe.qb.from_(SA)
		.select(SA.employee_schedule, SA.name)
		.where(SA.employee_schedule.isin(schedule_names))
	).run(as_dict=True)

	return {r.employee_schedule: r.name for r in records}


def get_attendance_map(shift_assignment_names):
	"""
	Fetch Attendance records linked to the given Shift Assignment names.
	Returns a map of {shift_assignment_name: attendance_status}.
	"""
	if not shift_assignment_names:
		return {}

	Attendance = DocType("Attendance")
	records = (
		frappe.qb.from_(Attendance)
		.select(Attendance.shift_assignment, Attendance.status, Attendance.docstatus)
		.where(Attendance.shift_assignment.isin(shift_assignment_names))
		.where(Attendance.docstatus == 1)
	).run(as_dict=True)

	return {r.shift_assignment: r.status for r in records}


def get_checkin_map(shift_assignment_names):
	"""
	Fetch Employee Checkin records linked to the given Shift Assignment names.
	Returns a set of shift_assignment_names that have at least one checkin.
	"""
	if not shift_assignment_names:
		return set()

	EC = DocType("Employee Checkin")
	records = (
		frappe.qb.from_(EC)
		.select(EC.shift_assignment)
		.where(EC.shift_assignment.isin(shift_assignment_names))
		.groupby(EC.shift_assignment)
	).run(as_dict=True)

	return set(r.shift_assignment for r in records)


def derive_status(schedule_date, today_date, shift_assignment_name, attendance_map, checkin_map):
	"""
	Derive the status of a reliever assignment:
	- Planned: schedule date is in the future
	- Active: schedule date is today and check-in has been recorded
	- Absent: schedule date is past and attendance is Absent (or no attendance exists)
	- Completed: schedule date is past and attendance is Present
	"""
	if schedule_date > today_date:
		return _("Planned")

	if schedule_date == today_date:
		# Check if employee has checked in today
		if shift_assignment_name and shift_assignment_name in checkin_map:
			return _("Active")
		return _("Planned")

	# Past date — check attendance
	if shift_assignment_name and shift_assignment_name in attendance_map:
		att_status = attendance_map[shift_assignment_name]
		if att_status == "Present":
			return _("Completed")
		elif att_status == "Absent":
			return _("Absent")
		else:
			# Half Day or other statuses
			return _("Completed")

	# No attendance record for a past date
	return _("Absent")


def get_report_summary(data):
	if not data:
		return []

	total_records = len(data)
	completed = sum(1 for d in data if d.get("status") == _("Completed"))
	active = sum(1 for d in data if d.get("status") == _("Active"))
	absent = sum(1 for d in data if d.get("status") == _("Absent"))
	planned = sum(1 for d in data if d.get("status") == _("Planned"))

	return [
		{
			"value": total_records,
			"label": _("Total Records"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": completed,
			"label": _("Completed"),
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"value": active,
			"label": _("Active"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": absent,
			"label": _("Absent"),
			"datatype": "Int",
			"indicator": "red",
		},
		{
			"value": planned,
			"label": _("Planned"),
			"datatype": "Int",
			"indicator": "orange",
		},
	]
