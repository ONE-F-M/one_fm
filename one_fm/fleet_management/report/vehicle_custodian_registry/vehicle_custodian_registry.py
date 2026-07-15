# Copyright (c) 2026, One FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import cint, flt, getdate

# Child table field on Vehicle that stores the custodian history.
CUSTODIAN_TABLE_FIELD = "custom_vehicle_custodian_history"


def execute(filters=None):
	"""Vehicle Custodian Registry.

	Produces one row per custodian assignment (child row of the Vehicle Custodian
	History table), joined with the parent Vehicle attributes. Vehicles without any
	custodian history are shown as a single row with blank custodian columns.
	"""
	filters = frappe._dict(filters or {})

	columns = get_columns()
	data = get_data(filters)
	report_summary = get_report_summary(data)

	return columns, data, None, None, report_summary


def get_columns():
	return [
		{
			"fieldname": "vehicle_id",
			"label": _("Vehicle ID"),
			"fieldtype": "Link",
			"options": "Vehicle",
			"width": 140,
		},
		{
			"fieldname": "license_plate",
			"label": _("License Plate No"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "brand",
			"label": _("Brand"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "model",
			"label": _("Model"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "vehicle_type",
			"label": _("Vehicle Type"),
			"fieldtype": "Link",
			"options": "Vehicle Type",
			"width": 130,
		},
		{
			"fieldname": "employee_id",
			"label": _("Employee ID"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 130,
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 170,
		},
		{
			"fieldname": "acquisition_date",
			"label": _("Acquisition Date"),
			"fieldtype": "Date",
			"width": 130,
		},
		{
			"fieldname": "handover_date",
			"label": _("Handover Date"),
			"fieldtype": "Date",
			"width": 130,
		},
		{
			"fieldname": "mileage_at_handover",
			"label": _("Mileage at Handover"),
			"fieldtype": "Int",
			"width": 150,
		},
		{
			"fieldname": "mileage_covered",
			"label": _("Mileage Covered"),
			"fieldtype": "Int",
			"width": 130,
		},
		{
			# Hidden flag consumed by the client-side formatter to bold the row of
			# the current/active custodian. Not shown as a column.
			"fieldname": "is_active_custodian",
			"label": _("Active Custodian"),
			"fieldtype": "Check",
			"width": 100,
			"hidden": 1,
		},
	]


def get_data(filters):
	vehicles = get_vehicles(filters)
	if not vehicles:
		return []

	vehicle_names = [v.name for v in vehicles]
	history_by_vehicle = get_custodian_history(vehicle_names)

	# A child-level filter narrows to specific custodian rows, so vehicles with no
	# matching row must be dropped rather than shown as a blank row.
	child_filter_active = bool(
		filters.get("employee") or filters.get("from_handover_date") or filters.get("to_handover_date")
	)

	data = []
	for vehicle in vehicles:
		all_rows = history_by_vehicle.get(vehicle.name, [])
		active_key = get_active_row_key(all_rows)
		display_rows = [row for row in all_rows if row_matches_filters(row, filters)]

		if display_rows:
			for row in display_rows:
				data.append(build_row(vehicle, row, is_active=(row.name == active_key)))
		elif not child_filter_active:
			# Vehicle with no custodian history — show parent details, blank custodian columns.
			data.append(build_row(vehicle, None, is_active=False))

	return data


def get_vehicles(filters):
	"""Fetch parent Vehicle attributes, applying vehicle-level filters."""
	Vehicle = DocType("Vehicle")
	Contract = DocType("Vehicle Leasing Contract")

	query = (
		frappe.qb.from_(Vehicle)
		.left_join(Contract)
		.on(Vehicle.vehicle_leasing_contract == Contract.name)
		.select(
			Vehicle.name,
			Vehicle.license_plate,
			Vehicle.make.as_("brand"),
			Vehicle.model,
			Vehicle.one_fm_vehicle_type.as_("vehicle_type"),
			Vehicle.acquisition_date,
			Vehicle.custom_status.as_("vehicle_status"),
		)
		.orderby(Vehicle.name)
	)

	if filters.get("vehicle"):
		query = query.where(Vehicle.name == filters.get("vehicle"))

	if filters.get("vehicle_category"):
		query = query.where(Vehicle.one_fm_vehicle_category == filters.get("vehicle_category"))

	if filters.get("leasing_company"):
		query = query.where(Contract.lessor_name.like(f"%{filters.get('leasing_company')}%"))

	return query.run(as_dict=True)


def get_custodian_history(vehicle_names):
	"""Return custodian history rows grouped by parent Vehicle, sorted by handover date ascending.

	The full (unfiltered) history is fetched so the current/active custodian — the
	latest handover — can be identified correctly even when a date filter hides it.
	"""
	rows = frappe.get_all(
		"Vehicle Custodian History",
		filters={
			"parenttype": "Vehicle",
			"parentfield": CUSTODIAN_TABLE_FIELD,
			"parent": ["in", vehicle_names],
		},
		fields=[
			"name",
			"parent",
			"employee_id",
			"employee_name",
			"handover_date",
			"mileage_at_handover",
			"mileage_covered",
			"idx",
		],
		order_by="parent asc, handover_date asc, idx asc",
	)

	grouped = {}
	for row in rows:
		grouped.setdefault(row.parent, []).append(row)

	return grouped


def get_active_row_key(rows):
	"""The active custodian is the row with the latest handover date (idx breaks ties)."""
	if not rows:
		return None

	def sort_key(row):
		return (getdate(row.handover_date) if row.handover_date else getdate("1900-01-01"), row.idx)

	return max(rows, key=sort_key).name


def row_matches_filters(row, filters):
	if filters.get("employee") and row.employee_id != filters.get("employee"):
		return False

	if not row.handover_date:
		# A row with no handover date cannot satisfy a date-range filter.
		return not (filters.get("from_handover_date") or filters.get("to_handover_date"))

	handover = getdate(row.handover_date)
	if filters.get("from_handover_date") and handover < getdate(filters.get("from_handover_date")):
		return False

	if filters.get("to_handover_date") and handover > getdate(filters.get("to_handover_date")):
		return False

	return True


def build_row(vehicle, custodian, is_active):
	row = {
		"vehicle_id": vehicle.name,
		"license_plate": vehicle.license_plate,
		"brand": vehicle.brand,
		"model": vehicle.model,
		"vehicle_type": vehicle.vehicle_type,
		"acquisition_date": vehicle.acquisition_date,
		"employee_id": None,
		"employee_name": None,
		"handover_date": None,
		"mileage_at_handover": None,
		"mileage_covered": None,
		"is_active_custodian": 0,
	}

	if custodian:
		row.update(
			{
				"employee_id": custodian.employee_id,
				"employee_name": custodian.employee_name,
				"handover_date": custodian.handover_date,
				"mileage_at_handover": cint(custodian.mileage_at_handover),
				"mileage_covered": cint(custodian.mileage_covered),
				"is_active_custodian": 1 if is_active else 0,
			}
		)

	return row


def get_report_summary(data):
	if not data:
		return []

	# Total active vehicles: distinct vehicles in the report whose lifecycle status is Active.
	vehicle_ids = list({row["vehicle_id"] for row in data if row.get("vehicle_id")})
	active_statuses = frappe.get_all(
		"Vehicle",
		filters={"name": ["in", vehicle_ids], "custom_status": "Active"},
		pluck="name",
	)
	active_vehicles = set(active_statuses)

	total_mileage = sum(flt(row.get("mileage_covered")) for row in data)

	return [
		{
			"value": len(active_vehicles),
			"label": _("Total Active Vehicles"),
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"value": cint(total_mileage),
			"label": _("Total Mileage Covered (KM)"),
			"datatype": "Int",
			"indicator": "blue",
		},
	]
