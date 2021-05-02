# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, date_diff, add_days, month_diff
from erpnext.hr.doctype.leave_application.leave_application \
	import get_leave_balance_on, get_leaves_for_period

from erpnext.hr.report.employee_leave_balance_summary.employee_leave_balance_summary \
	import get_department_leave_approver_map

def execute(filters=None):
	leave_types = frappe.db.sql_list("select name from `tabLeave Type` where one_fm_is_paid_annual_leave=1 order by name asc")

	columns = get_columns(leave_types)
	data = get_data(filters, leave_types)

	return columns, data

def get_columns(leave_types):
	columns = [
		_("Employee") + ":Link.Employee:120",
		_("Employee ID") + "::120",
		_("Employee Name") + "::180",
		_("DOJ") + ":Date:100",
		_("Department") +"::150",
		_("Salary") +":Currency:100",
	]

	for leave_type in leave_types:
		# columns.append(_(leave_type) + " " + _("Opening") + ":Float:160")
		# columns.append(_(leave_type) + " " + _("Taken") + ":Float:160")
		# columns.append(_(leave_type) + " " + _("Balance") + ":Float:160")
		columns.append(_("Opening ")+_(leave_type)+_(" Days") + ":Float:160")
		columns.append(_("Opening Leave Amount") + ":Currency:160")
		columns.append(_("Provision days for December 2020 ")+ ":Float:160")
		columns.append(_("Provision  Amount for December 2020") + ":Currency:160")

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
	for employee in active_employees:
		leave_approvers = department_approver_map.get(employee.department_name, [])
		if employee.leave_approver:
			leave_approvers.append(employee.leave_approver)

		if (len(leave_approvers) and user in leave_approvers) or (user in ["Administrator", employee.user_id]) or ("HR Manager" in frappe.get_roles(user)):
			row = [employee.name, employee.employee_id, employee.employee_name, employee.date_of_joining, employee.department, employee.one_fm_basic_salary]
			salary_per_day = employee.one_fm_basic_salary/30
			allocation_per_month = (30/365)*30
			for leave_type in leave_types:
				# leaves taken
				leaves_taken = get_leaves_for_period(employee.name, leave_type,
					employee.date_of_joining, filters.from_date) * -1

				# opening balance
				opening = get_leave_balance_on(employee.name, leave_type, filters.from_date)

				# closing balance
				closing = max(opening - leaves_taken, 0)
				closing_leave_amount = closing * salary_per_day

				provision_days_of_alloc = (30/365)*30
				if employee.relieving_date:
					relieving_date = getdate(employee.relieving_date)
					from_date = getdate(filters.from_date)
					# if relieving_date > from_date:
					month_diff_factor = month_diff(relieving_date, from_date)
					# else:
					# 	month_diff_factor = month_diff(from_date, relieving_date)
					print("\n\n\n\n######\n\n\n")
					print(month_diff_factor)
					if month_diff_factor > 0 and relieving_date < add_days(from_date, 30):
						day_diff = date_diff(add_days(from_date, 30), getdate(employee.relieving_date))
						provision_days_of_alloc = (30/365)*day_diff
					elif month_diff_factor <=0 :
						provision_days_of_alloc = 0
				provision_days_of_alloc_amount = provision_days_of_alloc * salary_per_day

				# row += [opening, leaves_taken, closing]
				row += [closing, closing_leave_amount, provision_days_of_alloc, provision_days_of_alloc_amount]


			data.append(row)

	return data
