# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import *

def execute(filters=None):
	print(filters)
	if not filters: filters = {}

	if not (filters.month and filters.year):
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

	payroll_cycle = get_payroll_cycle(filters)
	ot_dict = frappe._dict({})
	attendance_by_project = get_attendance(payroll_cycle)
	for i in ot_query:
		ot_dict[i.employee_id] = i.working_days
	for i in query:
		if ot_dict.get(i.employee_id):
			i.ot = ot_dict.get(i.employee_id)
		if payroll_cycle.get(i.project):
			i.start_date = payroll_cycle.get(i.project)['start_date']
			i.end_date = payroll_cycle.get(i.project)['end_date']
			if attendance_by_project.get('employee'):
				att_project = attendance_by_project.get('employee')
				i.working_days = att_project['working_days']
				i.ot = att_project['ot']
	if not query:
		frappe.msgprint(("No Payroll Submitted this month!"), alert=True, indicator="Blue")
	return query



def get_payroll_cycle(filters):
	settings = frappe.get_doc("HR and Payroll Additional Settings").project_payroll_cycle
	payroll_cycle = {}
	for row in settings:
		if row.payroll_start_day == 'Month Start':
			row.payroll_start_day = 1
		payroll_cycle[row.project] = {
			'start_date':f'{filters.year}-{filters.month}-{row.payroll_start_day}',
			'end_date':add_days(add_months(f'{filters.year}-{filters.month}-{row.payroll_start_day}', 1), -1)
		}
	return payroll_cycle


def get_attendance(projects):
	attendance_dict = {}
	ot_dict = {}
	for key, value in projects.items():
		start_date = projects[key]['start_date']
		end_date = projects[key]['end_date']
		attendance_list = frappe.db.sql("""
			SELECT employee,  COUNT(employee) as working_days FROM `tabAttendance` 
			WHERE attendance_date BETWEEN '{start_date}' AND '{end_date}' 
			AND project='{key}' AND status in ('Present', 'Work From Home', 'On Leave') 
			AND roster_type='Basic'
			GROUP BY employee
		""", as_dict=1)
		attendance_list_ot = frappe.db.sql("""
			SELECT employee,  COUNT(employee) as ot FROM `tabAttendance` 
			WHERE attendance_date BETWEEN '{start_date}' AND '{end_date}' 
			AND project='{key}' AND status in ('Present', 'Work From Home', 'On Leave') 
			AND roster_type='Over-Time'
			GROUP BY employee
		""", as_dict=1)

		for row in attendance_list_ot:
			if ot_dict.get(row.employee):
				ot_dict[row.employee] += row.ot
			else:
				ot_dict[row.employee] = row.ot

		for row in attendance_list:
			if attendance_dict.get(row.employee):
				attendance_dict[row.employee]['working_days'] += row.working_days
			else:
				attendance_dict[row.employee] = {'working_days': row.working_days, 'ot': 0}
			if ot_dict.get(row.employee):
				attendance_dict[row.employee]['ot'] += ot_dict.get(row.employee)

	return attendance_dict

@frappe.whitelist()
def get_attendance_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(attendance_date) from tabAttendance ORDER BY YEAR(attendance_date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)