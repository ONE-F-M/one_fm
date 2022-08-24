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
			"width": 120,
		},
		{
			"label": ("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 120,
		},
		{
			"label": ("Working Days"),
			"fieldname": "working_day",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": ("Work Permit Salary"),
			"fieldname": "work_permit_salary",
			"fieldtype": "Currency",
			"width": 210,
		},
		{
			"label": ("Base Salary"),
			"fieldname": "base",
			"fieldtype": "Currency",
			"width": 180,
		},
		{
			"label": ("Civil ID"),
			"fieldname": "civil_id",
			"options": "Journal Entry",
			"width": 140,
		},
		{
			"label": ("Shoon File"),
			"fieldname": "pam_file",
			"fieldtype": "Link",
			"options": "PAM File",
			"width": 120,
		},
		{
			"label": ("Bank Account"),
			"fieldname": "bank_account",
			"fieldtype": "Link",
			"options": "Bank Account",
			"width": 120,
		},
	]
def get_data(filters):
	data = []
	employee_details = frappe.db.sql(""" SELECT e.* from `tabPayroll Entry` AS p 
						JOIN `tabPayroll Employee Detail` AS e ON e.parent = p.name 
						WHERE MONTH(p.end_date) = %s"""%
						filters.get("month"),as_dict=1)
	
	if not employee_details:
		frappe.msgprint(("No Payroll Submitted this month!"), alert=True, indicator="Blue")
	
	for detail in employee_details:
		row = [
			detail.employee,
			detail.employee_name,
			frappe.get_value("Employee", detail.employee, ["project"]),
			detail.working_days,
			frappe.db.get_value('Employee', detail.employee, 'work_permit_salary'),
			detail.payment_amount,
			detail.civil_id_number,
			detail.mosal_id,
			detail.iban_number
		]
		data.append(row)
	return data

@frappe.whitelist()
def get_attendance_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(attendance_date) from tabAttendance ORDER BY YEAR(attendance_date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)