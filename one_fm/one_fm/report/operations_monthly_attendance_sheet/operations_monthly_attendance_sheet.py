# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, cint, cstr, date_diff, flt, getdate, nowdate

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

# The two things the day cells can show (WI-001791).
BY_ATTENDANCE_STATUS = "Attendance Status"
BY_SHIFT_HOURS = "Shift Hours"

OVERTIME = "Over-Time"
BASIC = "Basic"

# WI-001979: the summary block at the end of a row. Every day in the range increments
# exactly one of these, which is what makes them reconcilable - add them up and you get
# the days in the range, with no cell counting.
#
# `working_days` and `off_days` keep their fieldnames (the print format renders them by
# name); only the Present Days label changed.
SUMMARY_COUNTERS = (
	"working_days",
	"off_days",
	"absent_days",
	"annual_leave_days",
	"sick_leave_days",
	"leave_without_pay_days",
	"other_days",
	"missing_days",
)

# Statuses that count as a day present. Work From Home and Working already showed as "P"
# in the day cells, so they count here too - the column follows the cell.
PRESENT_STATUSES = ("Present", "Working", "Work From Home")

# Both kinds of day off share one column, per the AC.
DAY_OFF_STATUSES = ("Day Off", "Client Day Off")

# Leave Type -> its own column. A leave of any other type (Business Trip, Hajj Leave)
# counts as Other: naming it would mean a column per Leave Type on this site, which is
# eleven of them.
LEAVE_TYPE_COUNTERS = {
	"Annual Leave": "annual_leave_days",
	"Sick Leave": "sick_leave_days",
	"Leave Without Pay": "leave_without_pay_days",
}


# Which status stands when an employee has more than one record for the same day - two
# shifts, or a basic shift beside day-off overtime. Presence wins: they worked that day,
# whatever else was recorded against it. Anything not listed here ranks last, so a
# recognised status always beats an unrecognised one.
STATUS_PRECEDENCE = (
	"Present",
	"Working",
	"Work From Home",
	"Half Day",
	"On Leave",
	"Day Off",
	"Client Day Off",
	"Absent",
)


def more_significant(status, existing):
	"""Should `status` replace `existing` as the day's cell?"""
	if not existing:
		return True

	def rank(value):
		try:
			return STATUS_PRECEDENCE.index(value)
		except ValueError:
			return len(STATUS_PRECEDENCE)

	return rank(status) < rank(existing)


def summary_counter(status, leave_type=None):
	"""Which summary column one day belongs to (WI-001979).

	Total, rather than a chain of ifs with a gap at the end: a day with a status this
	does not name is Other, and a day with no status at all is Missing. Nothing falls
	through uncounted, so the row's figures always reconcile to the range.
	"""
	if not status:
		return "missing_days"

	if status in PRESENT_STATUSES:
		return "working_days"

	if status in DAY_OFF_STATUSES:
		return "off_days"

	if status == "Absent":
		return "absent_days"

	if status == "On Leave":
		return LEAVE_TYPE_COUNTERS.get(leave_type, "other_days")

	return "other_days"


def is_invalid_roster_combination(filters):
	"""Overtime asked for together with Day Off OT (WI-001791, Logic Rule 4).

	The acceptance criteria call this combination a logical error and require an empty
	report for it, so it is answered before any query runs.
	"""
	return filters.get("roster_type") == OVERTIME and cint(filters.get("day_off_ot"))


def apply_roster_type_filters(query, roster_type_field, day_off_ot_field, filters):
	"""The Roster Type / Day Off OT rules, shared by the Attendance and Employee
	Schedule queries so both answer a given filter pair identically (WI-001791).

	  Basic, unchecked    -> basic shifts only, with day-off OT actively excluded
	  Basic, checked      -> only basic shifts flagged as day-off OT
	  Overtime, unchecked -> overtime only, which already excludes both basic cases
	  Overtime, checked   -> never reaches a query (Logic Rule 4)
	"""
	roster_type = filters.get("roster_type")
	day_off_ot = cint(filters.get("day_off_ot"))

	if roster_type:
		query = query.where(roster_type_field == roster_type)

	if day_off_ot:
		query = query.where(day_off_ot_field == 1)
	elif roster_type == BASIC:
		# Rule 1's edge case: pure basic must not carry the day's day-off OT rows.
		# Left unconstrained for Overtime, whose own rule asks only that the basic
		# rows are hidden.
		query = query.where(day_off_ot_field != 1)

	return query


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


def validate_roster_type(filters):
	"""Roster Type is mandatory (WI-002017).

	Separate from validate_filters, which also vets a bare date range for the print
	template's day headers - those have no roster type and need none.

	Enforced on the server as well as on the filter because the report is reachable through
	frappe.desk.query_report.run, which never sees the form's `reqd`. Without a roster type
	the report answers with Basic and Over-Time rows added together, which is a payroll
	figure that is wrong rather than a report that is empty.
	"""
	if not filters.get("roster_type"):
		frappe.throw(_("Please select a Roster Type."))


def execute(filters):
	filters = frappe._dict(filters or {})

	validate_filters(filters)
	validate_roster_type(filters)
	dates = get_date_range(filters)

	# Logic Rule 4: Overtime and Day Off OT together is an invalid combination, so the
	# report answers with an empty state instead of a figure someone might act on.
	if is_invalid_roster_combination(filters):
		return get_columns(filters, dates), [], _(
			"<b>Overtime</b> with <b>Day Off OT</b> is not a valid combination. "
			"Clear one of them to generate the report."
		)

	attendance_map, hours_map, leave_type_map, attributes_map = get_attendance_map(filters)
	if not attendance_map:
		frappe.msgprint(_("No attendance records found."), alert=True, indicator="orange")
		return get_columns(filters, dates), []

	schedule_map = {}
	if filters.get("include_future_attendance"):
		schedule_map, schedule_hours_map, schedule_attributes = get_schedule_map(filters)
		# Schedule wins where both exist, the same precedence the statuses use below.
		hours_map = merge_hours_maps(hours_map, schedule_hours_map)
		attributes_map = merge_attribute_maps(attributes_map, schedule_attributes)

	columns = get_columns(filters, dates)
	data = get_data(
		filters, dates, attendance_map, schedule_map, hours_map, leave_type_map, attributes_map
	)

	if not data:
		frappe.msgprint(_("No attendance records found for this criteria."), alert=True, indicator="orange")
		return columns, []

	message = get_message(filters)

	return columns, data, message


def get_columns(filters, dates):
	# Narrow fixed columns: the AC asks the table to fit the screen, and every extra
	# pixel here is taken from the day cells.
	columns = [
		# Carried for the in-page filters, which match on the docname the Employee
		# filter returns; the badge number in Employee ID is a different value.
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "hidden": 1, "width": 0},
		{"label": _("Employee ID"), "fieldname": "employee_id", "fieldtype": "Data", "width": 90},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
		# WI-001980: hidden rather than dropped when Include Project is off. The client
		# formatter colours by column index and counts the hidden columns, so removing one
		# would shift the day cells out from under it.
		{
			"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project",
			**(
				{"width": 110}
				if cint(filters.get("include_project"))
				else {"hidden": 1, "width": 0}
			),
		},
		{"label": _("Status"), "fieldname": "employee_status", "fieldtype": "Data", "width": 80},
		{"label": _("Employment Type"), "fieldname": "employment_type", "fieldtype": "Data", "width": 110},
		{"label": _("Roster Type"), "fieldname": "roster_type", "fieldtype": "Data", "width": 80},
		{"label": _("Day Off OT"), "fieldname": "day_off_ot", "fieldtype": "Check", "width": 70},
		# No Shift column: WI-001790 lists the columns to display and shift is not one of
		# them. Rows are still grouped by shift (see row_group), so a day worked across two
		# shifts stays on its own row rather than being merged into one - the column is what
		# was asked for, not the grouping.
	]

	columns.extend(get_columns_for_days(dates))

	# WI-001979: every day in the range lands in exactly one of these, so a payroll
	# administrator can reconcile a row by adding them up instead of counting cells.
	# Fieldnames for the first two are left as they are: the print format renders
	# `working_days` and `off_days` by name, and renaming them there would blank those
	# cells rather than relabel them.
	columns.extend([
		{"label": _("Present Days"), "fieldname": "working_days", "fieldtype": "Float", "width": 90},
		{"label": _("Days Off"), "fieldname": "off_days", "fieldtype": "Float", "width": 70},
		{"label": _("Absent Days"), "fieldname": "absent_days", "fieldtype": "Float", "width": 85},
		{"label": _("Annual Leave"), "fieldname": "annual_leave_days", "fieldtype": "Float", "width": 90},
		{"label": _("Sick Leave"), "fieldname": "sick_leave_days", "fieldtype": "Float", "width": 80},
		{"label": _("Leave Without Pay"), "fieldname": "leave_without_pay_days", "fieldtype": "Float", "width": 120},
		# Days that carry a status none of the columns above name - On Hold, Holiday, a
		# leave of another type. Without it the row's parts do not add up to the range,
		# which is the whole point of the block (288 days were On Hold in July 2026 alone).
		{"label": _("Other"), "fieldname": "other_days", "fieldtype": "Float", "width": 70},
		{"label": _("Missing/Empty Days"), "fieldname": "missing_days", "fieldtype": "Float", "width": 120},
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


def get_data(
	filters, dates, attendance_map, schedule_map, hours_map, leave_type_map=None,
	attributes_map=None,
):
	employee_details = get_employee_details(filters)
	data = get_rows(
		employee_details, filters, dates, attendance_map, schedule_map, hours_map,
		leave_type_map, attributes_map,
	)

	return data


def merge_hours_maps(*maps):
	"""Merge {employee: {group: {date: hours}}} maps, later ones winning (WI-001791).

	The group is the row key from WI-001790 - shift, roster type and Day Off OT - so
	each row picks up the hours belonging to it rather than to the shift as a whole.
	"""
	merged = {}

	for hours_map in maps:
		for employee, groups in (hours_map or {}).items():
			for group, days in groups.items():
				merged.setdefault(employee, {}).setdefault(group, {}).update(days)

	return merged


def format_shift_hours(hours):
	"""The scheduled duration as the cell shows it: 8 rather than 8.0 (WI-001791)."""
	hours = flt(hours)
	if not hours:
		return ""

	return cstr(int(hours)) if hours == int(hours) else cstr(hours)

def get_message(filters=None):
	filters = filters or frappe._dict()

	# The status legend means nothing when the cells hold hours (WI-001791).
	if filters.get("generate_based_on") == BY_SHIFT_HOURS:
		return _("Each cell shows the scheduled duration of that day's shift, in hours.")

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


def row_group(record, include_project=False):
	"""The key a report row is grouped by (WI-001980).

	One row per employee, and that is all - shift, roster type and the Day Off OT flag no
	longer split it, so an employee who worked a basic shift and day-off overtime in the
	same period is one line, not three. With Include Project on, the project joins the key
	and the employee gets a row per project they worked on.

	The Roster Type and Day Off OT columns still carry a value when every record behind
	the row agrees on one; where they do not, the row leaves them blank rather than
	picking whichever was read last.
	"""
	return ((record.project or "") if include_project else "",)


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
	hours_map = {}
	leave_map = {}
	# Roster Type and Day Off OT used to be part of the row key, so a row always had one
	# of each. A row is an employee now (WI-001980), so they are collected and shown only
	# where every record behind the row agrees.
	attributes_map = {}
	# Keyed by day alone, not by group: a leave covers the whole day and is mirrored onto
	# every one of the employee's rows below, so its type cannot belong to one shift.
	leave_type_map = {}

	include_project = cint(filters.get("include_project"))

	for d in non_day_off_attendance_records:
		group = row_group(d, include_project)

		# The scheduled duration is recorded for every day that has a shift, including
		# the days spent on leave: it is what was rostered, not what was worked. Keyed
		# by the same group as the row it belongs to, so a shift split across roster
		# types keeps each part's hours with its own row.
		if d.shift_hours:
			hours_map.setdefault(d.employee, {}).setdefault(group, {})[d.day_key] = d.shift_hours

		collect_row_attributes(attributes_map, d.employee, group, d)

		if d.status == "On Leave":
			leave_map.setdefault(d.employee, {}).setdefault(group, []).append(d.day_key)
			leave_type_map.setdefault(d.employee, {})[d.day_key] = d.leave_type
			continue

		attendance_map.setdefault(d.employee, {}).setdefault(group, {})
		# A row can now cover several records for one day (WI-001980), so the day's cell
		# is decided rather than overwritten by whichever the query returned last.
		if more_significant(d.status, attendance_map[d.employee][group].get(d.day_key)):
			attendance_map[d.employee][group][d.day_key] = d.status

	# leave is applicable for the entire day so all shifts should show the leave entry
	for employee, leave_days in leave_map.items():
		for assigned_group, days in leave_days.items():
			# no attendance records exist except leaves
			if employee not in attendance_map:
				attendance_map.setdefault(employee, {}).setdefault(assigned_group, {})

			for day in days:
				for group in attendance_map[employee].keys():
					attendance_map[employee][group][day] = "On Leave"

	return attendance_map, hours_map, leave_type_map, attributes_map


def collect_row_attributes(attributes_map, employee, group, record):
	"""Remember the roster types and Day Off OT flags behind one row (WI-001980)."""
	attributes = attributes_map.setdefault(employee, {}).setdefault(
		group, {"roster_type": set(), "day_off_ot": set()}
	)
	attributes["roster_type"].add(record.roster_type or "")
	attributes["day_off_ot"].add(cint(record.day_off_ot))


def merge_attribute_maps(*maps):
	"""Union the attribute sets of {employee: {group: {...}}} maps."""
	merged = {}

	for attributes_map in maps:
		for employee, groups in (attributes_map or {}).items():
			for group, attributes in groups.items():
				target = merged.setdefault(employee, {}).setdefault(
					group, {"roster_type": set(), "day_off_ot": set()}
				)
				for key, values in attributes.items():
					target[key] |= values

	return merged


def only_value(values, default=""):
	"""The single value a set holds, or the default when it holds none or several.

	A row spanning both Basic and Over-Time cannot name one roster type, and naming
	whichever record was read last would be worse than leaving it blank.
	"""
	return next(iter(values)) if len(values or ()) == 1 else default


def get_non_day_off_attendance_records(filters):
	Attendance = frappe.qb.DocType("Attendance")
	OperationsShift = frappe.qb.DocType("Operations Shift")

	query = (
		frappe.qb.from_(Attendance)
		# Left, not inner: an attendance record with no Operations Shift is still a day
		# that was recorded, and an inner join drops it from the report entirely. 42,840
		# submitted records in 2026 alone have no shift - each one silently became a
		# "missing day" on the summary, and an absence that went uncounted (WI-001979).
		.left_join(OperationsShift)
		.on(Attendance.operations_shift == OperationsShift.name)
		.select(
			Attendance.employee,
			Attendance.attendance_date.as_("day_key"),
			Attendance.status,
			# WI-001979: which leave a day off work was taken under, for the per-type
			# summary columns.
			Attendance.leave_type,
			Attendance.roster_type,
			Attendance.day_off_ot,
			# WI-001980: the project the day was worked on, which is what the rows split
			# by - not the employee's own project, which is a single current posting.
			Attendance.project,
			OperationsShift.shift_classification.as_("shift"),
			# The shift's scheduled length, for "Shift Hours" mode. Deliberately not
			# Attendance.working_hours, which is what was actually clocked (WI-001791).
			OperationsShift.duration.as_("shift_hours"),
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

	query = apply_roster_type_filters(
		query, Attendance.roster_type, Attendance.day_off_ot, filters
	)

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
	hours_map = {}
	leave_map = {}
	attributes_map = {}

	include_project = cint(filters.get("include_project"))

	for d in non_day_off_schedule_records:
		group = row_group(d, include_project)

		if d.shift_hours:
			hours_map.setdefault(d.employee, {}).setdefault(group, {})[d.day_key] = d.shift_hours

		collect_row_attributes(attributes_map, d.employee, group, d)

		if d.status in ["Annual Leave"]:
			leave_map.setdefault(d.employee, {}).setdefault(group, []).append(d.day_key)
			continue

		schedule_map.setdefault(d.employee, {}).setdefault(group, {})
		if more_significant(d.status, schedule_map[d.employee][group].get(d.day_key)):
			schedule_map[d.employee][group][d.day_key] = d.status

	# leave is applicable for the entire day so all shifts should show the leave entry
	for employee, leave_days in leave_map.items():
		for assigned_group, days in leave_days.items():
			# no schedule records exist except leaves
			if employee not in schedule_map:
				schedule_map.setdefault(employee, {}).setdefault(assigned_group, {})

			for day in days:
				for group in schedule_map[employee].keys():
					schedule_map[employee][group][day] = "Annual Leave"

	return schedule_map, hours_map, attributes_map

def get_non_day_off_schedule_records(filters):
	EmployeeSchedule = frappe.qb.DocType("Employee Schedule")
	OperationsShift = frappe.qb.DocType("Operations Shift")

	query = (
		frappe.qb.from_(EmployeeSchedule)
		# Left, for the same reason as the attendance query above.
		.left_join(OperationsShift)
		.on(EmployeeSchedule.shift == OperationsShift.name)
		.select(
			EmployeeSchedule.employee,
			EmployeeSchedule.date.as_("day_key"),
			EmployeeSchedule.employee_availability.as_("status"),
			EmployeeSchedule.roster_type,
			EmployeeSchedule.day_off_ot,
			EmployeeSchedule.project,
			OperationsShift.shift_classification.as_("shift"),
			OperationsShift.duration.as_("shift_hours"),
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

	query = apply_roster_type_filters(
		query, EmployeeSchedule.roster_type, EmployeeSchedule.day_off_ot, filters
	)

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


def get_rows(
	employee_details, filters, dates, attendance_map, schedule_map, hours_map,
	leave_type_map=None, attributes_map=None,
):
	records = []
	leave_type_map = leave_type_map or {}
	attributes_map = attributes_map or {}

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
			hours_map.get(employee, {}),
			filters.get("generate_based_on"),
			leave_type_map.get(employee, {}),
			attributes_map.get(employee, {}),
		)

		# set employee details in the first row
		for record in attendance_for_employee:
			record.update({
				"employee": employee,
				"employee_id": details.employee_id,
				"employee_name": details.employee_name,
				"employee_status": details.employee_status,
				"employment_type": details.employment_type,
			})
			# With Include Project on the row already carries the project it was grouped
			# by; the employee's own project is a single current posting and would
			# overwrite it (WI-001980).
			record.setdefault("project", details.project)

		records.extend(attendance_for_employee)

	return records

def get_attendance_status(
	dates,
	employee_non_day_off_attendance,
	employee_day_off_attendance,
	employee_non_day_off_schedule,
	employee_day_off_schedule,
	employee_shift_hours=None,
	generate_based_on=BY_ATTENDANCE_STATUS,
	employee_leave_types=None,
	employee_attributes=None,
):
	"""Returns list of shift-wise attendance status for employee, keyed by ISO date
	[
			{'shift': 'Morning', '2026-08-01': 'A', '2026-08-02': 'P', ...},
			{'shift': 'Evening', '2026-08-01': 'P', '2026-08-02': 'A', ...}
	]

	Under "Shift Hours" the cells carry the shift's scheduled duration instead of the
	status abbreviation (WI-001791). The working day and day off counts are taken from
	the status either way, so the two modes always agree on the totals.
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
	employee_shift_hours = employee_shift_hours or {}
	employee_leave_types = employee_leave_types or {}
	employee_attributes = employee_attributes or {}
	by_shift_hours = generate_based_on == BY_SHIFT_HOURS

	groups = set(employee_non_day_off_attendance.keys()) | set(employee_non_day_off_schedule.keys())

	for group in groups:
		# Shift still separates the rows (see row_group) but is not carried into the row:
		# WI-001790 does not list it as a column, and an undeclared key is dead weight.
		(project,) = group
		attributes = employee_attributes.get(group, {})

		row = {
			# Blank where the row spans more than one, rather than whichever record was
			# read last. Filtering by Roster Type or Day Off OT makes them single-valued
			# again, which is when they say something.
			"roster_type": only_value(attributes.get("roster_type")),
			"day_off_ot": only_value(attributes.get("day_off_ot"), default=0),
		}
		if project:
			row["project"] = project

		# Merge Attendance and Schedule statuses
		attendance_dict = { **employee_non_day_off_attendance.get(group, {}), **employee_non_day_off_schedule.get(group, {}) }

		# WI-001979: one counter per summary column, and every day increments exactly one
		# of them - so the row's counters always add up to the days in the range.
		counts = dict.fromkeys(SUMMARY_COUNTERS, 0)

		for date in dates:
			status = attendance_dict.get(date)

			# if status is not found in non day attendance records, check day off attendance
			if not status:
				status = employee_day_off_attendance.get(date, "") or employee_day_off_schedule.get(date, "")

			counts[summary_counter(status, employee_leave_types.get(date))] += 1

			if by_shift_hours:
				# The scheduled duration of the shift, never the hours actually clocked.
				row[cstr(date)] = format_shift_hours(
					employee_shift_hours.get(group, {}).get(date)
				)
			else:
				row[cstr(date)] = attendance_status_map.get(status, "")

		row.update(counts)

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