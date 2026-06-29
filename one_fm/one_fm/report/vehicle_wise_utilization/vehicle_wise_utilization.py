# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	report_summary = get_report_summary(data)

	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"fieldname": "vehicle_no",
			"label": _("Vehicle No"),
			"fieldtype": "Link",
			"options": "Vehicle",
			"width": 160,
		},
		{
			"fieldname": "vehicle_category",
			"label": _("Vehicle Category"),
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"fieldname": "license_plate",
			"label": _("License Plate"),
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"fieldname": "total_trips_executed",
			"label": _("Total Trips Executed"),
			"fieldtype": "Int",
			"width": 160,
		},
		{
			"fieldname": "active_driving_time",
			"label": _("Active Driving Time"),
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"fieldname": "idle_standby_time",
			"label": _("Idle Standby Time"),
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"fieldname": "assigned_driver_name",
			"label": _("Assigned Driver Name"),
			"fieldtype": "Data",
			"width": 200,
		},
	]


def get_data(filters):
	TM = DocType("Transportation Manifest")
	TMD = DocType("Transportation Manifest Details")

	query = (
		frappe.qb.from_(TM)
		.join(TMD).on(TMD.parent == TM.name)
		.select(
			TM.vehicle_no,
			TM.schedule_date,
			TMD.trip_id,
			TMD.trip_time,
		)
	)

	query = apply_filters(query, filters, TM, TMD)
	raw_data = query.run(as_dict=True)

	if not raw_data:
		return []

	# Group by vehicle_no, de-duplicate trip_time per trip_id,
	# and track distinct active days for the 24h operational window
	vehicle_data = {}
	for row in raw_data:
		vehicle = row.vehicle_no
		if not vehicle:
			continue

		if vehicle not in vehicle_data:
			vehicle_data[vehicle] = {
				"trip_ids": set(),
				"trip_times": {},
				"active_days": set(),
			}

		trip_id = row.trip_id or ""
		if trip_id:
			vehicle_data[vehicle]["trip_ids"].add(trip_id)

		# Track distinct schedule dates this vehicle was active
		if row.schedule_date:
			vehicle_data[vehicle]["active_days"].add(str(row.schedule_date))

		# Store first non-empty trip_time per trip_id to avoid double-counting
		if trip_id and trip_id not in vehicle_data[vehicle]["trip_times"] and row.trip_time:
			vehicle_data[vehicle]["trip_times"][trip_id] = row.trip_time

	# Fetch vehicle master data in bulk
	vehicle_names = list(vehicle_data.keys())
	if not vehicle_names:
		return []

	Vehicle = DocType("Vehicle")
	Employee = DocType("Employee")

	vehicle_info = (
		frappe.qb.from_(Vehicle)
		.left_join(Employee).on(Vehicle.employee == Employee.name)
		.select(
			Vehicle.name,
			Vehicle.license_plate,
			Vehicle.one_fm_vehicle_category,
			Vehicle.employee,
			Employee.employee_name,
		)
		.where(Vehicle.name.isin(vehicle_names))
	).run(as_dict=True)

	vehicle_map = {v.name: v for v in vehicle_info}

	# Total Operational Window = 24 hours per active day
	DAILY_WINDOW_MINUTES = 24 * 60  # 1440 minutes

	# Build result rows
	result = []
	for vehicle_no, vdata in vehicle_data.items():
		v_info = vehicle_map.get(vehicle_no, {})

		# Sum driving time across unique trips
		driving_minutes = 0.0
		for trip_time_str in vdata["trip_times"].values():
			driving_minutes += parse_time_to_minutes(trip_time_str)

		# Total operational window = 24h × number of distinct active days
		active_days = len(vdata["active_days"])
		total_window_minutes = flt(active_days * DAILY_WINDOW_MINUTES, 2)

		# Idle = Total Operational Window − Active Driving Time
		idle_minutes = max(total_window_minutes - driving_minutes, 0.0)

		result.append({
			"vehicle_no": vehicle_no,
			"vehicle_category": v_info.get("one_fm_vehicle_category", ""),
			"license_plate": v_info.get("license_plate", ""),
			"total_trips_executed": len(vdata["trip_ids"]),
			"active_driving_time": format_minutes(driving_minutes),
			"idle_standby_time": format_minutes(idle_minutes),
			"assigned_driver_name": v_info.get("employee_name", ""),
		})

	# Sort by total trips descending
	result.sort(key=lambda x: x["total_trips_executed"], reverse=True)
	return result


def apply_filters(query, filters, TM, TMD):
	if filters.get("from_date"):
		query = query.where(TM.schedule_date >= filters["from_date"])

	if filters.get("to_date"):
		query = query.where(TM.schedule_date <= filters["to_date"])

	if filters.get("vehicle_no"):
		query = query.where(TM.vehicle_no == filters["vehicle_no"])

	if filters.get("operations_site"):
		query = query.where(TMD.operations_site == filters["operations_site"])

	return query


def parse_time_to_minutes(time_str):
	"""Parse a time/duration string into total minutes.

	Handles formats: HH:MM:SS, HH:MM, plain numeric (treated as minutes),
	and timedelta objects. Returns 0.0 for empty or unparseable values.
	"""
	if not time_str:
		return 0.0

	# Handle timedelta objects (MariaDB may return these for Time fields)
	if hasattr(time_str, "total_seconds"):
		return flt(time_str.total_seconds() / 60.0, 2)

	time_str = str(time_str).strip()
	if not time_str:
		return 0.0

	# HH:MM:SS or HH:MM
	if ":" in time_str:
		parts = time_str.split(":")
		try:
			hours = int(parts[0])
			minutes = int(parts[1]) if len(parts) > 1 else 0
			seconds = int(parts[2]) if len(parts) > 2 else 0
			return flt(hours * 60 + minutes + seconds / 60.0, 2)
		except (ValueError, IndexError):
			return 0.0

	# Plain number — treat as minutes
	try:
		return flt(float(time_str), 2)
	except ValueError:
		return 0.0


def format_minutes(total_minutes):
	"""Format total minutes as 'Xh Ym' string. Returns empty if zero."""
	if total_minutes <= 0:
		return ""

	hours = int(total_minutes // 60)
	minutes = int(total_minutes % 60)

	if hours and minutes:
		return "{0}h {1}m".format(hours, minutes)
	elif hours:
		return "{0}h".format(hours)
	else:
		return "{0}m".format(minutes)


def get_chart(data):
	"""Bar chart showing top 10 vehicles by total trips."""
	if not data:
		return None

	top_vehicles = [d for d in data if d["total_trips_executed"] > 0][:10]
	if not top_vehicles:
		return None

	return {
		"data": {
			"labels": [d["vehicle_no"] for d in top_vehicles],
			"datasets": [{
				"name": _("Total Trips"),
				"values": [d["total_trips_executed"] for d in top_vehicles],
			}],
		},
		"type": "bar",
		"colors": ["#5e64ff"],
	}


def get_report_summary(data):
	"""Summary cards displayed above the report grid."""
	if not data:
		return []

	total_vehicles = len(data)
	total_trips = sum(d["total_trips_executed"] for d in data)

	return [
		{
			"value": total_vehicles,
			"label": _("Total Vehicles"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": total_trips,
			"label": _("Total Trips"),
			"datatype": "Int",
			"indicator": "green",
		},
	]
