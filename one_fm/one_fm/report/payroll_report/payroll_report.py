# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	if not filters: filters = {}

	if not (filters.get("month") and filters.get("year")):
		msgprint(_("Please select month and year"), raise_exception=1)
	
	columns, data =  get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	return [
		{
			"label": ("Employee ID"),
			"fieldname": "employee_id",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{
			"label": ("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": ("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 120,
		},
		{
			"label": ("Work Permit Salary"),
			"fieldname": "work_permit_salary",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": ("Base Salary"),
			"fieldname": "base",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": ("Civil ID"),
			"fieldname": "one_fm_civil_id",
			"options": "Journal Entry",
			"width": 140,
		},
		{
			"label": ("Shoon File"),
			"fieldname": "shoon_file",
			"fieldtype": "Link",
			"options": "PAM File",
			"width": 120,
		},
		{
			"label": ("Bank Account"),
			"fieldname": "bank_ac_no",
			"fieldtype": "Link",
			"options": "Bank Account",
			"width": 120,
		},
		{
			"label": ("Start Date"),
			"fieldname": "start_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": ("End Date"),
			"fieldname": "end_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": ("Day off Type"),
			"fieldname": "day_off_category",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": ("No. of Days Off"),
			"fieldname": "number_of_days_off",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": ("Attendance Days (basic)"),
			"fieldname": "working_days",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},

		{
			"label": ("Attendance Days (OT)"),
			"fieldname": "ot",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
	]
def get_data(filters):
	print(filters)
	data = []
	query = frappe.db.sql(f"""
		SELECT DISTINCT e.name as employee_id, e.employee_name, e.project, e.work_permit_salary, e.one_fm_civil_id, e.bank_ac_no,
		e.day_off_category, e.number_of_days_off, e.pam_file_number as shoon_file, ssa.base, pe.start_date, pe.end_date,
		COUNT(at.employee) as working_days
		FROM `tabEmployee` e JOIN `tabSalary Structure Assignment` ssa ON e.name=ssa.employee
			JOIN `tabPayroll Employee Detail` ped ON e.name=ped.employee 
			JOIN `tabPayroll Entry` pe ON pe.name=ped.parent
			JOIN `tabAttendance` at ON at.employee=e.name
		WHERE ssa.docstatus=1 AND pe.posting_date LIKE '{filters.year}-{str(filters.month).zfill(2)}%' 
			AND pe.docstatus=1
			AND at.attendance_date BETWEEN pe.start_date AND pe.end_date
			AND at.status in ('PRESENT', 'Work From Home', 'On Leave')
			AND at.roster_type='Basic'
		GROUP BY e.name
		ORDER BY e.name ASC
	""", as_dict=1)

	ot_query = frappe.db.sql(f"""
		SELECT DISTINCT e.name as employee_id, COUNT(at.employee) as working_days
		FROM `tabEmployee` e JOIN `tabSalary Structure Assignment` ssa ON e.name=ssa.employee
			JOIN `tabPayroll Employee Detail` ped ON e.name=ped.employee 
			JOIN `tabPayroll Entry` pe ON pe.name=ped.parent
			JOIN `tabAttendance` at ON at.employee=e.name
		WHERE ssa.docstatus=1 AND pe.posting_date LIKE '{filters.year}-{str(filters.month).zfill(2)}%' 
			AND pe.docstatus=1
			AND at.attendance_date BETWEEN pe.start_date AND pe.end_date
			AND at.status in ('PRESENT', 'Work From Home', 'On Leave')
			AND at.roster_type='Over-Time'
		GROUP BY e.name
		ORDER BY e.name ASC
	""", as_dict=1)
	ot_dict = frappe._dict({})
	for i in ot_query:
		ot_dict[i.employee_id] = i.working_days
	for i in query:
		if ot_dict.get(i.employee_id):
			i.ot = ot_dict.get(i.employee_id)

	if not query:
		frappe.msgprint(("No Payroll Submitted this month!"), alert=True, indicator="Blue")
	return query
