# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_conditions(filters):
	conditions = ""
	fields = ['shift_classification', 'site', 'project', 'governorate_area']
	for field in fields:
		if filters.get(field):
			conditions += " and {0}='{1}' ".format(field, filters.get(field))
	return conditions

def get_data(filters):
	result = []
	conditions = get_conditions(filters)
	operations_shifts=frappe.db.sql("""select * from `tabOperations Shift` where docstatus < 2 {0}""".format(conditions), as_dict=1)
	for operations_shift in operations_shifts:
		no_of_posts = frappe.db.count("Operations Post", {'site_shift': operations_shift.name})
		total_staffs = frappe.db.count("Employee Schedule",
			{'date': getdate(filters.get('date')), 'employee_availability': 'Working', 'shift': operations_shift.name}
		)
		shift_supervisor = get_shift_supervisor(operations_shift.name)
		shift_supervisor_name = frappe.db.get_value("Employee", shift_supervisor, "employee_name")
		if total_staffs > 0:
			row = [
				operations_shift.name,
				operations_shift.start_time,
				operations_shift.end_time,
				shift_supervisor,
				shift_supervisor_name,
				operations_shift.duration,
				operations_shift.shift_classification,
				operations_shift.service_type,
				operations_shift.site,
				operations_shift.project,
				operations_shift.governorate_area,
				total_staffs,
				no_of_posts
			]
			result.append(row)

	return result

def get_columns():
	return [
	    {
	     "fieldname": "operations_shift",
	     "fieldtype": "Link",
	     "label": "Operations Shift",
	     "options": "Operations Shift",
	     "width": 0
	    },
	    {
	     "fieldname": "start_time",
	     "fieldtype": "Time",
	     "label": "Start Time",
	     "width": 0
	    },
	    {
	     "fieldname": "end_time",
	     "fieldtype": "Time",
	     "label": "End Time",
	     "width": 0
	    },
	    {
	     "fieldname": "shift_supervisor",
	     "fieldtype": "Data",
	     "label": "Shift Supervisor",
	     "options": "Employee",
	     "width": 0
	    },
	    {
	     "fieldname": "supervisor_name",
	     "fieldtype": "Data",
	     "label": "Supervisor Name",
	     "width": 0
	    },
	    {
	     "fieldname": "duration",
	     "fieldtype": "Int",
	     "label": "Duration",
	     "width": 0
	    },
	    {
	     "fieldname": "classification",
	     "fieldtype": "Data",
	     "label": "Shift Classification",
	     "width": 0
	    },
	    {
	     "fieldname": "service_type",
	     "fieldtype": "Link",
	     "label": "Service Type",
	     "options": "Service Type",
	     "width": 0
	    },
	    {
	     "fieldname": "site",
	     "fieldtype": "Link",
	     "label": "Site",
	     "options": "Operations Site",
	     "width": 0
	    },
	    {
	     "fieldname": "project",
	     "fieldtype": "Link",
	     "label": "Project",
	     "options": "Project",
	     "width": 0
	    },
	    {
	     "fieldname": "governorate_area",
	     "fieldtype": "Link",
	     "label": "Governorate Area",
	     "options": "Governorate Area",
	     "width": 0
	    },
	    {
	     "fieldname": "total_staffs",
	     "fieldtype": "Int",
	     "label": "Total Staffs(Scheduled)",
	     "width": 0
	    },
	    {
	     "fieldname": "no_of_posts",
	     "fieldtype": "Int",
	     "label": "No of Posts",
	     "width": 0
	    }
	]
