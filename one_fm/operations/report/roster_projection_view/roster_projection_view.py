# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

from datetime import datetime
import frappe
from frappe import _
from frappe.utils import today, add_days, getdate, get_last_day

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data


def get_data(filters):
	results = []
	month_start = getdate().replace(day=1, month=int(filters.month), year=int(filters.year))
	month_end = get_last_day(getdate())
	today = getdate()
	yesterday = add_days(today, -1)
	schedules = 0
	use_schedule = True
	if today.month > month_end.month and today.year <= month_start.year:
		yesterday = month_end
		use_schedule = False

	contracts_detail = frappe.db.sql(
		"""
			SELECT
				con.client, con.project, con_item.item_code, con_item.count, con_item.rate,
				con_item.count*con_item.rate as total_rate
			FROM
				`tabContracts` con
			LEFT JOIN
				`tabContract Item` con_item
				ON
					con_item.parent = con.name
			WHERE
				con.workflow_state = 'Active' and (
					(%(start_date)s between con.start_date and con.end_date)
					or (%(end_date)s between con.start_date and con.end_date)
					or (con.start_date between %(start_date)s and %(end_date)s)
					or (con.end_date between %(start_date)s and %(end_date)s)
				)
		""",{
			"start_date": month_start,
			"end_date": month_end
		},
		as_dict=True,
	)
	for row in contracts_detail:
		# get projection
		# Projection = Employee Schedule / Post Schedule
		row.projection = 0
		row.projection_rate = 0
		# Live = [Employee Attendance(From Start of Month till Yesterday) + Employee Schedule (From Today to End of Month)] / Post Schedule
		row.live_projection = 0
		row.live_projection_rate = 0
		roles = [i.name for i in frappe.db.sql(f"""
			SELECT name FROM `tabOperations Role`
			WHERE sale_item="{row.item_code}" AND project="{row.project}"
		""", as_dict=1)]
		if roles:
			post_schedule = frappe.db.count("Post Schedule", filters={
				'project':row.project,
				'operations_role': ['IN', roles],
				'date': ['BETWEEN', [month_start, month_end]]}
			)
			employee_schedule = frappe.db.count("Employee Schedule", filters={
				'project':row.project,
				'operations_role': ['IN', roles],
				'employee_availability': 'Working',
				'date': ['BETWEEN', [month_start, month_end]]}
			)
			if post_schedule and employee_schedule:
				row.projection = employee_schedule/post_schedule
				row.projection_rate = row.rate*row.projection

			# get schedules
			if today == month_start:
				attendance = 0
			else:
				attendance = frappe.db.count("Attendance", filters={
					'docstatus': 1,
					'project':row.project,
					'operations_role': ['IN', roles],
					'status': ['IN', ['Present', 'Work From Home', 'On Leave']],
					'attendance_date': ['BETWEEN', [month_start, yesterday]]},
				)
			if use_schedule and post_schedule:
				schedules = frappe.db.count("Employee Schedule", filters={
					'project':row.project,
					'operations_role': ['IN', roles],
					'employee_availability': 'Working',
					'date': ['BETWEEN', [today, month_end]]}
				)
				row.live_projection = (attendance + schedules)/post_schedule
				row.live_projection_rate = row.live_projection * row.rate



	results = contracts_detail
	return results

def get_live_schedule_query(contracts, filters, start_date):
	schedule_query = f"""
		SELECT con.client, con.project, con_item.item_code, con_item.count, con_item.rate,
		con_item.count*con_item.rate as total_rate, COUNT(es.name) as projection
		FROM `tabContracts` con
		LEFT JOIN `tabContract Item` con_item ON con_item.parent=con.name
		LEFT JOIN `tabEmployee Schedule` es ON es.project=con.project
		LEFT JOIN `tabOperations Role` pt ON pt.name=es.operations_role
		WHERE con.name = \"{contracts.name}\"
		AND es.employee_availability='Working'
		AND con_item.item_code=pt.sale_item
		AND es.date BETWEEN "{start_date}" AND "{filters.year}-{filters.month}-31"
		GROUP BY con.project
	"""
	data = frappe.db.sql(schedule_query, as_dict=1)
	return data

def get_live_attendance_query(contracts, filters, to_date):
	attendance_query = f"""
		SELECT con.client, con.project, con_item.item_code, con_item.count, con_item.rate,
		con_item.count*con_item.rate as total_rate, COUNT(at.name) as attendance
		FROM `tabContracts` con
		LEFT JOIN `tabContract Item` con_item ON con_item.parent=con.name
		LEFT JOIN `tabAttendance` at ON at.project=con.project
		LEFT JOIN `tabOperations Role` pt ON pt.name=at.operations_role
		WHERE con.name = \"{contracts.name}\"
		AND at.status !='Absent'
		AND con_item.item_code=pt.sale_item
		AND at.attendance_date BETWEEN "{filters.year}-{filters.month}-01" AND "{to_date}"
		GROUP BY con.project
	"""
	data = frappe.db.sql(attendance_query, as_dict=1)
	return data

def get_columns():
	return [
		{
			'fieldname': 'client',
			'label': _('Client'),
			'fieldtype': 'Link',
			'options': 'Customer',
			'width': 200
		},
		{
			'fieldname': 'project',
			'label': _('Project'),
			'fieldtype': 'Link',
			'options': 'Project',
			'width': 180
		},
		{
			'fieldname': 'item_code',
			'label': _('Item Code'),
			'fieldtype': 'Link',
			'options': 'Item',
			'width': 260,
		},
		{
			'fieldname': 'count',
			'label': _('Count'),
			'fieldtype': 'Int',
			'width': 70,
		},
		{
			'fieldname': 'rate',
			'label': _('Rate'),
			'fieldtype': 'Currency',
			'width': 100,
		},
		{
			'fieldname': 'total_rate',
			'label': _('Total Rate'),
			'fieldtype': 'Currency',
			'width': 120,
		},
		{
			'fieldname': 'projection',
			'label': _('Projection'),
			'fieldtype': 'Float',
			'width': 100,
			'precision':2
		},
		{
			'fieldname': 'projection_rate',
			'label': _('Projection Rate'),
			'fieldtype': 'Currency',
			'width': 100
		},
		{
			'fieldname': 'live_projection',
			'label': _('Live Projection'),
			'fieldtype': 'Float',
			'width': 100
		},
		{
			'fieldname': 'live_projection_rate',
			'label': _('Projection Rate'),
			'fieldtype': 'Currency',
			'width': 100
		},
	]
