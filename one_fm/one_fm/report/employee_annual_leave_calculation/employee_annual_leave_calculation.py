# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, date_diff, add_days, month_diff, formatdate, add_months
from erpnext.hr.doctype.leave_application.leave_application \
	import get_leave_balance_on, get_leaves_for_period

from erpnext.hr.report.employee_leave_balance_summary.employee_leave_balance_summary \
	import get_department_leave_approver_map

def execute(filters=None):
	# Get the list of  Paid annula leave Leave type
	leave_types = frappe.db.sql_list("select name from `tabLeave Type` where one_fm_is_paid_annual_leave=1 order by name asc")

	columns = get_columns(leave_types, filters)
	data = get_data(filters, leave_types)

	return columns, data

def get_columns(leave_types, filters):
	columns = [
		_("Employee") + ":Link.Employee:120",
		_("Employee ID") + "::120",
		_("Employee Name") + "::180",
		_("DOJ") + ":Date:100",
		_("Department") +"::150",
		_("Salary") +":Currency:100",
	]
	date_after_a_month_formated = formatdate(add_months(getdate(filters.from_date), 1))

	for leave_type in leave_types:
		columns.append(_("Opening ")+_(leave_type)+_(" Days") + ":Float:200")
		columns.append(_("Opening Leave Amount") + ":Currency:180")
		columns.append(_("Provision days as on {0}").format(date_after_a_month_formated) + ":Float:240")
		columns.append(_("Provision  Amount as on {0}").format(date_after_a_month_formated) + ":Currency:240")
		columns.append(_("Net leave days as on {0}").format(date_after_a_month_formated) + ":Float:240")
		columns.append(_("Net leave Amount as on {0}").format(date_after_a_month_formated) + ":Currency:240")
		columns.append(_("Leaves taken as on {0}").format(date_after_a_month_formated) + ":Float:240")
	columns.append(_("Total Period Till Date")+ ":Data:160")

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

def get_data(filters, leave_types):
	user = frappe.session.user
	conditions = get_conditions(filters)

	active_employees = frappe.get_all("Employee",
		filters=conditions,
		fields=["name", "employee_name", "department", "user_id", "leave_approver", "employee_id", "date_of_joining", "one_fm_basic_salary", "relieving_date"])

	department_approver_map = get_department_leave_approver_map(filters.get('department'))

	data = []

	# Iterating all active employees to get the annual leave allocations
	for employee in active_employees:
		from_date = getdate(filters.from_date)
		total_period_till_date = date_diff(from_date, employee.date_of_joining)

		leave_approvers = department_approver_map.get(employee.department_name, [])

		if employee.leave_approver:
			leave_approvers.append(employee.leave_approver)

		if (len(leave_approvers) and user in leave_approvers) or (user in ["Administrator", employee.user_id]) or ("HR Manager" in frappe.get_roles(user)):
			row = [employee.name, employee.employee_id, employee.employee_name, employee.date_of_joining, employee.department, employee.one_fm_basic_salary]
			# Calculating the salary per day, assuming that 30 days of month
			salary_per_day = employee.one_fm_basic_salary/30

			for leave_type in leave_types:
				# Get the leave balance upto the given date
				opening = get_leave_balance_on(employee.name, leave_type, filters.from_date)
				opening_leave_amount = opening * salary_per_day

				# Find the provision of days and amount for un allocated days
				provision_days_of_allocation = (30/365)*30 # It is the factor: 365 days of work => 30 dyas of paid leave.
				if employee.relieving_date:
					relieving_date = getdate(employee.relieving_date)
					month_difference_factor = month_diff(relieving_date, from_date)

					# To calculate provision_days_of_allocation, If the employee is relieving before the month ends
					if month_difference_factor > 0 and relieving_date < add_days(from_date, 30):
						day_diff = date_diff(add_days(from_date, 30), getdate(employee.relieving_date))
						provision_days_of_allocation = (30/365)*day_diff
						total_period_till_date = date_diff(employee.relieving_date, employee.date_of_joining)

					# If the relieving date is greater than the given date, then there will not be any provision for allocation
					elif month_difference_factor <=0 :
						provision_days_of_allocation = 0
				provision_days_of_allocation_amount = provision_days_of_allocation * salary_per_day

				# Get the leaves taken in between joining date and the given date
				leaves_taken = get_leaves_for_period(employee.name, leave_type,
					employee.date_of_joining, filters.from_date) * -1

				net_leave_days = opening + provision_days_of_allocation
				net_leave_days_amount = net_leave_days * salary_per_day

				if total_period_till_date > 0:
					year_from_no_of_days = find_year_from_no_of_days(total_period_till_date)
				else:
					year_from_no_of_days = "0 Years 0 Months 0 Days"

				row += [opening, opening_leave_amount, provision_days_of_allocation, provision_days_of_allocation_amount,
					net_leave_days, net_leave_days_amount, leaves_taken, year_from_no_of_days]

			data.append(row)

	return data

def find_year_from_no_of_days(number_of_days):
	year = int(number_of_days / 365)
	month = int((number_of_days % 365)/30)
	days = (number_of_days % 365) % 30
	year_from_no_of_days = str(year)+" Years "+str(month)+" Months "+str(days)+" Days"
	return year_from_no_of_days
