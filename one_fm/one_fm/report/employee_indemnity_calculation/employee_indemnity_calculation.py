# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, date_diff, add_days, month_diff, formatdate, add_months, get_last_day
from one_fm.one_fm.hr_utils import get_total_indemnity, get_per_day_indemnity_amount
from calendar import monthrange

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_columns(filters):
	formated_date = getdate(filters.to_date)
	date_after_a_month_formated = get_last_day(formated_date)
	columns = [
		_("Employee") + ":Link.Employee:120",
		_("Employee ID") + "::120",
		_("Employee Name") + "::180",
		_("DOJ") + ":Date:100",
		_("Department") +"::150",
		_("Indemnity Amount") +":Currency:100",
		_("Accumulated Indemnity as on {0}").format(formated_date) + ":Float:280",
		_("Provision Indemnity as on {0}").format(date_after_a_month_formated) + ":Float:260",
		_("Total Indemnity")+ ":Currency:160",
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
		to_date = getdate(filters.to_date)
		provision_date = get_last_day(to_date) #last date of a given month
		if to_date >= getdate(employee.date_of_joining):
			indemnity_allcn = frappe.db.exists('Indemnity Allocation', {'employee': employee.name, 'expired': False})
			if indemnity_allcn:
				if (user in ["Administrator", employee.user_id]) or ("HR Manager" in frappe.get_roles(user)):
					indemnity_amount = frappe.get_value("Salary Structure Assignment",{"employee":employee.name},["indemnity_amount"])
					row = [employee.name, employee.employee_id, employee.employee_name, employee.date_of_joining, employee.department, indemnity_amount]
					salary_per_day = indemnity_amount/26
					indemnity_as_on = get_total_indemnity(employee.date_of_joining, to_date, indemnity_amount)
					provision_indemnity = get_per_day_indemnity_amount(employee.date_of_joining, provision_date, indemnity_amount) * monthrange(to_date.year, to_date.month)[1]

					total_period_till_date = date_diff(to_date, employee.date_of_joining)
					if employee.relieving_date:
						relieving_date = getdate(employee.relieving_date)
						month_diff_factor = month_diff(relieving_date, to_date)
						if month_diff_factor > 0 and relieving_date < add_days(to_date, 30):
							day_diff = date_diff(add_days(to_date, 30), getdate(employee.relieving_date))
							total_period_till_date = date_diff(employee.relieving_date, employee.date_of_joining)
							provision_indemnity = get_per_day_indemnity_amount(employee.date_of_joining, employee.relieving_date, indemnity_amount) * day_diff
						elif month_diff_factor <=0 :
							provision_indemnity = 0

					total_indemnity = get_total_indemnity(employee.date_of_joining, provision_date, indemnity_amount)
					if total_period_till_date > 0:
						year_from_no_of_days = find_year_from_no_of_days(total_period_till_date)
					else:
						year_from_no_of_days = "0 Years 0 Months 0 Days"
					row += [indemnity_as_on, provision_indemnity, total_indemnity, year_from_no_of_days]


				data.append(row)

	return data

def find_year_from_no_of_days(number_of_days):
	year = int(number_of_days / 365)
	month = int((number_of_days % 365)/30)
	days = (number_of_days % 365) % 30
	year_from_no_of_days = str(year)+" Years "+str(month)+" Months "+str(days)+" Days"
	return year_from_no_of_days
