# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, date_diff, add_days, month_diff, formatdate, add_months

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_columns(filters):
	formated_date = formatdate(getdate(filters.from_date))
	date_after_a_month_formated = formatdate(add_months(getdate(filters.from_date), 1))
	columns = [
		_("Employee") + ":Link.Employee:120",
		_("Employee ID") + "::120",
		_("Employee Name") + "::180",
		_("DOJ") + ":Date:100",
		_("Department") +"::150",
		_("Salary") +":Currency:100",
		_("Accumulated Indemnity as on {0}").format(formated_date) + ":Float:280",
		_("Accumulated Amount as on {0}").format(formated_date) + ":Currency:260",
		_("Provision Indemnity as on {0}").format(date_after_a_month_formated) + ":Float:260",
		_("Provision Amount as on {0}").format(date_after_a_month_formated) + ":Currency:260",
		_("Total Indemnity")+ ":Float:160",
		_("Total Amount")+ ":Currency:160",
		_("Total Period Till Date")+ ":Data:160"
	]

	return columns

def get_conditions(filters):
	conditions = {
		"status": "Active"
	}
	if filters.get("department"):
		conditions.update({"department": filters.get("department")})
	if filters.get("employee"):
		conditions.update({"employee": filters.get("employee")})

	return conditions

def get_data(filters):
	user = frappe.session.user
	conditions = get_conditions(filters)

	active_employees = frappe.get_all("Employee",
		filters=conditions,
		fields=["name", "employee_name", "department", "user_id", "leave_approver", "employee_id",
			"date_of_joining", "one_fm_basic_salary", "relieving_date"])

	data = []
	for employee in active_employees:
		from_date = getdate(filters.from_date)
		if from_date >= getdate(employee.date_of_joining):
			indemnity_allcn = frappe.db.exists('Indemnity Allocation', {'employee': employee.name, 'expired': False})
			if indemnity_allcn:
				if (user in ["Administrator", employee.user_id]) or ("HR Manager" in frappe.get_roles(user)):
					row = [employee.name, employee.employee_id, employee.employee_name, employee.date_of_joining, employee.department, employee.one_fm_basic_salary]
					salary_per_day = employee.one_fm_basic_salary/30
					indemnity_as_on = frappe.db.get_value('Indemnity Allocation', indemnity_allcn, 'total_indemnity_allocated')
					amount_as_on = indemnity_as_on * salary_per_day
					provision_indemnity = (30/365)*30

					total_period_till_date = date_diff(from_date, employee.date_of_joining)
					if employee.relieving_date:
						relieving_date = getdate(employee.relieving_date)
						month_diff_factor = month_diff(relieving_date, from_date)
						if month_diff_factor > 0 and relieving_date < add_days(from_date, 30):
							day_diff = date_diff(add_days(from_date, 30), getdate(employee.relieving_date))
							total_period_till_date = date_diff(employee.relieving_date, employee.date_of_joining)
							provision_indemnity = (30/365)*day_diff
						elif month_diff_factor <=0 :
							provision_indemnity = 0
					provision_amount = provision_indemnity * salary_per_day

					total_indemnity = indemnity_as_on+provision_indemnity
					total_amount = amount_as_on+provision_amount
					if total_period_till_date > 0:
						year_from_no_of_days = find_year_from_no_of_days(total_period_till_date)
					else:
						year_from_no_of_days = "0 Years 0 Months 0 Days"
					row += [indemnity_as_on, amount_as_on, provision_indemnity, provision_amount, total_indemnity, total_amount, year_from_no_of_days]


				data.append(row)

	return data

def find_year_from_no_of_days(number_of_days):
	year = int(number_of_days / 365)
	month = int((number_of_days % 365)/30)
	days = (number_of_days % 365) % 30
	year_from_no_of_days = str(year)+" Years "+str(month)+" Months "+str(days)+" Days"
	return year_from_no_of_days
