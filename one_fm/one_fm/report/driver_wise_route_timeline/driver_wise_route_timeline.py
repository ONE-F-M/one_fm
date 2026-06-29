import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import flt, get_datetime


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	report_summary = get_report_summary(data)

	return columns, data, None, None, report_summary


def get_columns():
	return [
		{
			"fieldname": "driver_name",
			"label": _("Driver Name"),
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"fieldname": "schedule_date",
			"label": _("Schedule Date"),
			"fieldtype": "Date",
			"width": 130,
		},
		{
			"fieldname": "vehicle_active_log",
			"label": _("Vehicle Active Log"),
			"fieldtype": "Link",
			"options": "Vehicle",
			"width": 150,
		},
		{
			"fieldname": "route_stop_location",
			"label": _("Route Stop Location"),
			"fieldtype": "Data",
			"width": 280,
		},
		{
			"fieldname": "total_duty_duration",
			"label": _("Total Duty Duration"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "rambo_relief_event",
			"label": _("Rambo Relief Event"),
			"fieldtype": "Data",
			"width": 200,
		},
	]


def get_data(filters):
	"""Build tree-structured report data grouped by effective driver."""
	manifest_rows = fetch_manifest_rows(filters)
	if not manifest_rows:
		return []

	# Determine effective driver per row and group
	driver_groups = build_driver_groups(manifest_rows)

	# Gather all unique effective drivers + dates for batch queries
	driver_date_keys = list(driver_groups.keys())
	all_drivers = list({key[0] for key in driver_date_keys})
	all_dates = list({key[1] for key in driver_date_keys})

	# Batch fetch duty durations from Employee Schedule
	duty_map = fetch_duty_durations(all_drivers, all_dates)

	# Batch fetch Rambo Assignment statuses
	rambo_map = fetch_rambo_statuses(all_drivers, all_dates)

	# Batch fetch employee names
	employee_name_map = fetch_employee_names(all_drivers)

	# Apply optional driver_name filter (on effective driver)
	if filters.get("driver_name"):
		filter_emp = filters["driver_name"]
		driver_date_keys = [k for k in driver_date_keys if k[0] == filter_emp]

	# Sort by schedule_date then driver
	driver_date_keys.sort(key=lambda k: (k[1], employee_name_map.get(k[0], k[0])))

	# Build output rows
	data = []
	for driver_id, schedule_date in driver_date_keys:
		stops = driver_groups[(driver_id, schedule_date)]
		# Sort stops chronologically by scheduled_time
		stops.sort(key=lambda s: s.get("scheduled_time") or "")

		emp_name = employee_name_map.get(driver_id, driver_id)
		duty_hours = duty_map.get((driver_id, str(schedule_date)), 0)
		is_rambo = rambo_map.get((driver_id, str(schedule_date)), False)

		# Apply Rambo Relief Only filter
		if filters.get("rambo_relief_only") and not is_rambo:
			continue

		duration_label = format_duration(duty_hours)
		rambo_label = _("YES (Standby Deployment)") if is_rambo else _("NO")

		# Determine first vehicle for summary row
		first_vehicle = stops[0].get("vehicle_no", "")

		if len(stops) == 1:
			# Single stop — show directly on the summary row
			stop = stops[0]
			stop_display = format_stop_with_time(stop.get("stop_name"), stop.get("scheduled_time"))
			data.append({
				"driver_name": emp_name,
				"schedule_date": schedule_date,
				"vehicle_active_log": stop.get("vehicle_no", ""),
				"route_stop_location": stop_display,
				"total_duty_duration": duration_label,
				"rambo_relief_event": rambo_label,
				"indent": 0,
				"_is_rambo": is_rambo,
			})
		else:
			# Multiple stops — summary row + detail rows
			data.append({
				"driver_name": emp_name,
				"schedule_date": schedule_date,
				"vehicle_active_log": first_vehicle,
				"route_stop_location": _("Expanded Timeline Below:"),
				"total_duty_duration": duration_label,
				"rambo_relief_event": rambo_label,
				"indent": 0,
				"_is_rambo": is_rambo,
			})

			for stop in stops:
				stop_display = format_stop_with_time(stop.get("stop_name"), stop.get("scheduled_time"))
				data.append({
					"driver_name": "↳",
					"schedule_date": schedule_date,
					"vehicle_active_log": stop.get("vehicle_no", ""),
					"route_stop_location": stop_display,
					"total_duty_duration": "--",
					"rambo_relief_event": "--",
					"indent": 1,
				})

	return data


def fetch_manifest_rows(filters):
	"""Fetch all relevant Transportation Manifest Detail rows for the date range."""
	TMD = DocType("Transportation Manifest Details")
	TM = DocType("Transportation Manifest")

	query = (
		frappe.qb.from_(TMD)
		.join(TM).on(TMD.parent == TM.name)
		.select(
			TM.name.as_("manifest"),
			TM.schedule_date,
			TM.vehicle_no,
			TMD.employee,
			TMD.employee_name,
			TMD.reliever_employee,
			TMD.attendance_status,
			TMD.stop_name,
			TMD.scheduled_time,
			TMD.rambo_assignment,
		)
		.orderby(TM.schedule_date)
		.orderby(TMD.scheduled_time)
	)

	if filters.get("from_date"):
		query = query.where(TM.schedule_date >= filters["from_date"])

	if filters.get("to_date"):
		query = query.where(TM.schedule_date <= filters["to_date"])

	return query.run(as_dict=True)


def build_driver_groups(manifest_rows):
	"""Group manifest rows by (effective_driver, schedule_date).

	Effective driver is the reliever_employee if the original is Absent
	and a reliever is assigned, otherwise the original employee.
	"""
	groups = {}

	for row in manifest_rows:
		effective_driver = None

		if row.attendance_status == "Absent" and row.reliever_employee:
			effective_driver = row.reliever_employee
		elif row.employee:
			effective_driver = row.employee

		if not effective_driver:
			continue

		key = (effective_driver, row.schedule_date)
		groups.setdefault(key, []).append({
			"stop_name": row.stop_name,
			"scheduled_time": row.scheduled_time,
			"vehicle_no": row.vehicle_no,
			"rambo_assignment": row.rambo_assignment,
		})

	return groups


def fetch_duty_durations(drivers, dates):
	"""Batch fetch total duty hours from Employee Schedule per (driver, date).

	Sums shift duration across all roster types (Basic + Over-Time).
	"""
	if not drivers or not dates:
		return {}

	ES = DocType("Employee Schedule")

	schedules = (
		frappe.qb.from_(ES)
		.select(
			ES.employee,
			ES.date,
			ES.start_datetime,
			ES.end_datetime,
		)
		.where(ES.employee.isin(drivers))
		.where(ES.date.isin(dates))
		.where(ES.start_datetime.isnotnull())
		.where(ES.end_datetime.isnotnull())
	).run(as_dict=True)

	duration_map = {}
	for s in schedules:
		key = (s.employee, str(s.date))
		start = get_datetime(s.start_datetime)
		end = get_datetime(s.end_datetime)
		hours = flt((end - start).total_seconds() / 3600, 1)
		if hours > 0:
			duration_map[key] = duration_map.get(key, 0) + hours

	return duration_map


def fetch_rambo_statuses(drivers, dates):
	"""Batch check if any driver has a submitted Rambo Assignment per (driver, date)."""
	if not drivers or not dates:
		return {}

	RA = DocType("Rambo Assignment")

	rambos = (
		frappe.qb.from_(RA)
		.select(
			RA.employee,
			RA.date,
		)
		.where(RA.employee.isin(drivers))
		.where(RA.date.isin(dates))
		.where(RA.docstatus == 1)
	).run(as_dict=True)

	rambo_map = {}
	for r in rambos:
		rambo_map[(r.employee, str(r.date))] = True

	return rambo_map


def fetch_employee_names(employee_ids):
	"""Batch fetch employee_name for a list of employee IDs."""
	if not employee_ids:
		return {}

	Emp = DocType("Employee")

	employees = (
		frappe.qb.from_(Emp)
		.select(Emp.name, Emp.employee_name)
		.where(Emp.name.isin(employee_ids))
	).run(as_dict=True)

	return {e.name: e.employee_name for e in employees}


def format_stop_with_time(stop_name, scheduled_time):
	"""Format a stop as 'Stop Name (HH:MM AM/PM)'."""
	if not stop_name:
		return ""

	if not scheduled_time:
		return stop_name

	# scheduled_time is a timedelta object from the DB
	try:
		total_seconds = int(scheduled_time.total_seconds())
		hours = total_seconds // 3600
		minutes = (total_seconds % 3600) // 60
	except (AttributeError, TypeError):
		# Fallback: try parsing as string "HH:MM:SS"
		try:
			parts = str(scheduled_time).split(":")
			hours = int(parts[0])
			minutes = int(parts[1])
		except (ValueError, IndexError):
			return stop_name

	period = "AM" if hours < 12 else "PM"
	display_hour = hours % 12
	if display_hour == 0:
		display_hour = 12

	return "{stop} ({hour}:{minute:02d} {period})".format(
		stop=stop_name,
		hour=display_hour,
		minute=minutes,
		period=period,
	)


def format_duration(hours):
	"""Format hours as 'X.Y Hours'."""
	if not hours:
		return _("0 Hours")

	return "{hours} {label}".format(
		hours=flt(hours, 1),
		label=_("Hours"),
	)


def get_report_summary(data):
	"""Summary cards above the report: total drivers, rambo deployments, avg duration."""
	if not data:
		return []

	# Only count summary rows (indent=0)
	summary_rows = [row for row in data if row.get("indent") == 0]
	if not summary_rows:
		return []

	total_drivers = len(summary_rows)
	rambo_count = sum(1 for row in summary_rows if row.get("_is_rambo"))

	# Parse duty durations for average calculation
	duty_values = []
	for row in summary_rows:
		duration_str = row.get("total_duty_duration", "")
		try:
			val = flt(duration_str.split(" ")[0])
			duty_values.append(val)
		except (ValueError, IndexError, AttributeError):
			pass

	avg_duration = flt(sum(duty_values) / len(duty_values), 1) if duty_values else 0

	return [
		{
			"value": total_drivers,
			"label": _("Total Drivers"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": rambo_count,
			"label": _("Rambo Deployments"),
			"datatype": "Int",
			"indicator": "orange" if rambo_count else "green",
		},
		{
			"value": avg_duration,
			"label": _("Avg. Duty Duration (Hrs)"),
			"datatype": "Float",
			"indicator": "blue",
		},
	]
