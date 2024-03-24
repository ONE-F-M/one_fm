# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt
"""
	THIS REPORT GENERATES LIST OF USERS WITH NO ATTENDANCE
	THIS MEAN THAT THEY NEITHER HAVE LEAVE, WORK FROM HOME, TIMESHEETNOR HOLIDAY
	IF USER IS NOT HR, THE REPORT IS LOCKED TO THE USER RECORD AS THE SUPERVISOR
"""

import frappe
from frappe import _


def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data


def get_data(filters):
	conditions = f""" sa.start_date='{filters.date}' AND sa.company="{filters.company}" """
	if filters.supervisor:
		conditions += f""" AND os.employee='{filters.supervisor}'"""
	# query = frappe.db.sql(f"""
	# 	SELECT sa.employee, sa.employee_name, sa.start_date, os.supervisor, os.supervisor_name,
	# 	sa.name as shift_assignment, sa.shift as operations_shift, em.employee_id
	# 	FROM `tabShift Assignment` sa RIGHT JOIN `tabOperations Shift` os ON os.name=sa.shift
	# 	RIGHT JOIN `tabEmployee` em ON sa.employee=em.name
	# 	WHERE {conditions}
	# 	AND sa.employee IN (
	# 		SELECT employee FROM `tabAttendance`
	# 		WHERE attendance_date='{filters.date}' AND status='Absent'
	# 	)
	# 	ORDER BY sa.employee_name
	# """, as_dict=1)
	query = frappe.db.sql(f"""
		SELECT sa.employee, sa.employee_name, sa.start_date, os.employee as supervisor, os.employee_name as supervisor_name,
		sa.name as shift_assignment, sa.shift as operations_shift, em.employee_id
		FROM `tabShift Assignment` sa RIGHT JOIN `tabOperations Shift Supervisors` os ON os.parent=sa.shift
		RIGHT JOIN `tabEmployee` em ON sa.employee=em.name
		WHERE {conditions}
		AND sa.employee IN (
			SELECT employee FROM `tabAttendance`
			WHERE attendance_date='{filters.date}' AND status='Absent'
		)
		ORDER BY sa.employee_name
	""", as_dict=1)
	return query

def get_columns():
	return [
		{
			'fieldname': 'employee',
			'label': _('Employee'),
			'fieldtype': 'Link',
			'options': 'Employee',
			'width': 150
		},
		{
			'fieldname': 'employee_name',
			'label': _('Employee Name'),
			'fieldtype': 'Data',
			'width': 200
		},
		{
			'fieldname': 'employee_id',
			'label': _('Employee ID'),
			'fieldtype': 'Data',
			'width': 120
		},
		{
			'fieldname': 'start_date',
			'label': _('Date'),
			'fieldtype': 'Date',
			'width': 120,
		},
		{
			'fieldname': 'supervisor',
			'label': _('Supervisor'),
			'fieldtype': 'Link',
			'options': 'Employee',
			'width': 120,
		},
		{
			'fieldname': 'supervisor_name',
			'label': _('Supervisor Name'),
			'fieldtype': 'Data',
			'width': 200,
		},
		{
			'fieldname': 'shift_assignment',
			'label': _('Shift Assignment'),
			'fieldtype': 'Link',
			'options': 'Shift Assignment',
			'width': 280,
		},
		{
			'fieldname': 'operations_shift',
			'label': _('Operations Shift'),
			'fieldtype': 'Link',
			'options': 'Operations Shift',
			'width': 350,
		},
	]



def get_supervisors():
	frappe.db.sql("""
		SELECT DISTINCT employee as supervisor, employee_name as  supervisor_name
		FROM `tabOperations Shift Supervisors`
		WHERE employee NOT IN ('')
	""", as_dict=1)


@frappe.whitelist()
def get_filter_supervisor():
	#  for the browser filters
	return [i.supervisor for i in get_supervisors()]