# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from datetime import datetime
import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	columns = [
			   {
				   'fieldname': 'accommodation',
				   'label': _('Accommodation'),
				   'fieldtype': 'Link',
				   'options': 'Accommodation',
				   'width': 80
			   },
			   {
				   'fieldname': 'accommodation_unit',
				   'label': _('Unit'),
				   'fieldtype': 'Link',
				   'options': 'Accommodation Unit',
				   'width': 120,
			   },
			   {
				   'fieldname': 'accommodation_space',
				   'label': _('Space'),
				   'fieldtype':'Link',
				   'options': 'Accommodation Space',
				   'width': 120,
			   },
			   {
				   'fieldname': 'bed',
				   'label': _('Bed'),
				   'fieldtype': 'Link',
				   'width': 120,
				   'options': "Bed",
			   },
			   {
				   'fieldname': 'full_name',
				   'label': _('Employee Name'),
				   'fieldtype': 'Data',
				   'width': 180,
			   },
			   {
				   'fieldname': 'civil_id',
				   'label': _('Civil ID'),
				   'fieldtype': 'Data',
				   'width': 120,
			   },
			   {
				   'fieldname': 'checkin_checkout_date_time',
				   'label': _('Checkin'),
				   'fieldtype': 'Datetime',
				   'width': 120,
			   },
			   {
				   'fieldname': 'checkin_ref',
				   'label': _('Checkin Ref'),
				   'fieldtype': 'Link',
				   'width': 120,
				   'options': 'Accommodation Checkin Checkout'
			   },
		]

	if not filters.get('current_list_only'):
		columns += [
				{
					'fieldname': 'checkout_date',
					'label': _('Checkout'),
					'fieldtype': 'Datetime',
					'width': 120,
				},
				{
					'fieldname': 'checkout',
					'label': _('Checkout Ref'),
					'fieldtype': 'Link',
					'width': 120,
					'options': 'Accommodation Checkin Checkout'
				},
			]
	columns += [
		{
			'fieldname': 'tenant_category',
			'label': _('Tenant Category'),
			'fieldtype': 'Data',
			'width': 120,
		},
		{
			'fieldname': 'designation',
			'label': _('designation'),
			'fieldtype': 'Data',
			'width': 120,
		},
		{
			'fieldname': 'project',
			'label': _('Project'),
			'fieldtype': 'Data',
			'width': 120,
		},
		{
			'fieldname': 'nationality',
			'label': _('Nationality'),
			'fieldtype': 'Data',
			'width': 120,
		},
		{
			'fieldname': 'employee_status',
			'label': _('Employee Status'),
			'fieldtype': 'Data',
			'width': 120,
		},
	]

	return columns


def get_conditions(filters):
	conditions = ""
	fields = ['accommodation', 'accommodation_unit', 'accommodation_space', 'bed', 'employee', 'tenant_category']
	for field in fields:
		if filters.get(field):
			conditions += " and {0}='{1}' ".format(field, filters.get(field))
	return conditions

def get_data(filters):
	data=[]
	current_list_only = filters.get('current_list_only')
	conditions = get_conditions(filters)
	leave_data = get_leave_data()
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
			row = {
				'employee':acc.employee,
				'accommodation':acc.accommodation,
				'accommodation_unit':acc.accommodation_unit,
				'accommodation_space':acc.accommodation_space,
				'bed':acc.bed,
				'full_name':acc.full_name,
				'civil_id':acc.civil_id,
				'checkin_checkout_date_time':acc.checkin_checkout_date_time,
				'checkin_ref':acc.name,
				'tenant_category':acc.tenant_category,
				'designation':designation,
				'project':project,
				'nationality':nationality,
				'employee_status':employee_status
			}
			if not current_list_only:
				row = {**row, **{
					'checkout_date':checkout_date,
					'checkout':checkout
				}}
			if row.get('employee_status') and leave_data and leave_data.get(row.get('employee_status')):
				row['employee_status'] = f"<i style='color:red'>{leave_data.get(row.get('employee_status'))}</i>"
			data.append(row)

	return data


def get_leave_data():
	query = frappe.db.get_list(
		"Leave Application",
		filters={
			'from_date': ['<=', datetime.today().date()],
			'to_date': ['>=', datetime.today().date()],
			'workflow_state':'Approved'
		},
		fields = ['employee', 'leave_type',]
	)

	result_dict = {}
	for i in query:
		result_dict[i.employee] = i.leave_type

	return result_dict
