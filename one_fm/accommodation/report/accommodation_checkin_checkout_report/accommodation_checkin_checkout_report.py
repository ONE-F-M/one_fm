# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	columns = [
		_("Accommodation") + ":Link/Accommodation:80",
		_("Unit") + ":Link/Accommodation Unit:80",
		_("Space") + ":Link/Accommodation Space:120",
		_("Bed") + ":Link/Bed:120",
		_("Employee ID") + ":Data:120",
		_("Employee Name") + ":Data:180",
		_("CIVIL ID") + ":Data:100",
		_("Checkin") + ":Date:100",
		_("Checkin Ref") + ":Link/Accommodation Checkin Checkout:120"
	]

	if not filters.get('current_list_only'):
		columns.append(_("Checkout") + ":Date:100")
		columns.append(_("Checkout Ref") + ":Link/Accommodation Checkin Checkout:120")

	columns.append(_("Tenant Category") + ":Data:120")
	columns.append(_("Designation") + ":Data:120")
	columns.append(_("Project") + ":Data:120")
	columns.append(_("Nationality") + ":Data:120")
	columns.append(_("Employee Status") + ":Data:180")

	return columns

def get_conditions(filters):
	conditions = ""
	fields = ['accommodation', 'accommodation_unit', 'accommodation_space', 'bed', 'employee', 'employee_id', 'tenant_category']
	for field in fields:
		if filters.get(field):
			conditions += " and {0}='{1}' ".format(field, filters.get(field))
	return conditions

def get_data(filters):
	data=[]
	current_list_only = filters.get('current_list_only')
	conditions = get_conditions(filters)
	acc_list=frappe.db.sql("""select * from `tabAccommodation Checkin Checkout` where type='IN' {0}""".format(conditions), as_dict=1)
	for acc in acc_list:
		checkout_date = ''
		checkout = ''
		designation = ''
		project = ''
		nationality = ''
		employee_status = ''
		if acc.employee:
			employee = frappe.get_doc('Employee', acc.employee)
			designation = employee.designation
			project = employee.project
			employee_status = employee.status
			nationality = employee.one_fm_nationality
		if acc.checked_out and not current_list_only:
			checkout = frappe.db.exists('Accommodation Checkin Checkout', {'checkin_reference': acc.name})
			if checkout:
				checkout_date = frappe.db.get_value('Accommodation Checkin Checkout', checkout, 'checkin_checkout_date_time')
		if acc.checked_out and current_list_only:
			pass
		else:
			row = [
				acc.accommodation,
				acc.accommodation_unit,
				acc.accommodation_space,
				acc.bed,
				acc.employee_id,
				acc.full_name,
				acc.civil_id,
				acc.checkin_checkout_date_time,
				acc.name,
				checkout_date,
				checkout,
				acc.tenant_category,
				designation,
				project,
				nationality,
				employee_status
			]
			data.append(row)

	return data
