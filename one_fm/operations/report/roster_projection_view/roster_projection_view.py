# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

from datetime import datetime
import frappe
from frappe import _
from frappe.utils import today, add_days, getdate, get_last_day
from one_fm.utils import get_week_start_end

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data


def get_data(filters):
	results = []
	month_start = getdate().replace(day=1, month=int(filters.get('month')), year=int(filters.get('year')))
	month_end = get_last_day(month_start)
	today = getdate()

	shift_types_list = frappe.db.get_list("Shift Type", fields=['name', 'duration'])
	shift_types_dict = {}
	for i in shift_types_list:
		shift_types_dict[i.name] = i.duration
	# Get active contracts in the given month of the given year
	contracts_detail = frappe.db.sql(
		"""
			SELECT
				con.client, con.project, con_item.item_code, con_item.count, con_item.rate, con_item.rate_type, con_item.rate_type_off,
				con_item.days_off_category, con_item.no_of_days_off, con_item.count*con_item.rate as total_rate
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
		if row.rate_type=='Monthly':
			row.start_date = month_start
			row.employee_schedule = 0
			row.post_schedule = 0
			row.projection = 0
			row.projection_rate = 0
			row.live_projection = 0
			row.live_projection_rate = 0
			row.es_qty = 0 # employee schedule qty
			row.ps_qty = 0 # post schedule qty
			row.ea_qty = 0 # employee attendance qty
			working_days = 0 # total number of working days for each item
			working_days_type = ''
			if row.rate_type_off=='Full Month': # working days is number of days in the current month
				row.end_date = month_end
				working_days = month_end.day
				working_days_type = 'Monthly'
			elif row.rate_type_off=='Days Off':
				if row.days_off_category=='Monthly':
					working_days_type = 'Monthly'
					working_days = month_end.day - row.no_of_days_off
					row.end_date = month_end
				elif row.days_off_category=='Weekly':
					working_days_type = 'Weekly'
					working_days = 7 - row.no_of_days_off
					row.end_date = add_days(month_start, 27)# for weekly rate, start day to 28th day from start date
					month_end = row.end_date

			roles = [i.name for i in frappe.db.sql(f"""
				SELECT name FROM `tabOperations Role`
				WHERE sale_item="{row.item_code}" AND project="{row.project}"
			""", as_dict=1)]
			if roles:
				# Find post schedule from month/week start to month/week end
				post_schedule = frappe.db.count("Post Schedule", filters={
					'project':row.project,
					'operations_role': ['IN', roles],
					'date': ['BETWEEN', [month_start, month_end]]}
				)
				# Find employee schedule from month start to month end
				employee_schedule_list = frappe.db.get_list("Employee Schedule", filters={
					'project':row.project,
					'operations_role': ['IN', roles],
					'employee_availability': 'Working',
					'date': ['BETWEEN', [month_start, month_end]]},
					fields=['name', 'shift_type']
				)
				employee_schedule = len(employee_schedule_list)

				attendance = frappe.db.count("Attendance", filters={
					'docstatus': 1,
					'project':row.project,
					'operations_role': ['IN', roles],
					'status': ['IN', ['Present', 'Work From Home', 'On Leave']],
					'attendance_date': ['BETWEEN', [month_start, month_end]]},
				)
				
				
				row.es_qty = round(employee_schedule / working_days if working_days else 0, 2)
				row.ps_qty = round(post_schedule / working_days if working_days else 0, 2)
				row.ea_qty = round(attendance/working_days if working_days else 0, 2)
				row.projection = round((row.es_qty/row.ps_qty) * row.count if (row.es_qty and row.ps_qty) else 0, 2)
				row.projection_rate = round(row.projection * row.rate, 2)
				row.live_projection = round(((row.es_qty+row.ea_qty)/row.ps_qty)*row.count if (row.es_qty and row.ps_qty) else 0, 2)
				row.live_projection_rate = round(row.live_projection * row.rate, 2)

				# clear days_off_type
				row.days_off_cat =  ''
				if row.rate_type=='Monthly':
					row.days_off_cat = row.days_off_category
				else: row.days_off_cat = ''
				# row.employee_schedule = employee_schedule/working_days  if working_days else 0
				# row.post_schedule = post_schedule/working_days if working_days else 0
				# if post_schedule and employee_schedule:
				# 	# Projection = Employee Schedule / Post Schedule
				# 	row.projection = employee_schedule/post_schedule
				# 	row.projection_rate = row.rate*row.projection

				# # Find live projection, if today is in the selected month
				# if today > month_start and today < month_end and post_schedule:
				# 	yesterday = add_days(today, -1)
				# 	# Find attendance from month start to yesterday
				# 	attendance = frappe.db.count("Attendance", filters={
				# 		'docstatus': 1,
				# 		'project':row.project,
				# 		'operations_role': ['IN', roles],
				# 		'status': ['IN', ['Present', 'Work From Home', 'On Leave']],
				# 		'attendance_date': ['BETWEEN', [month_start, yesterday]]},
				# 	)
				# 	# Find employee schedules from today to month end
				# 	schedules = frappe.db.count("Employee Schedule", filters={
				# 		'project':row.project,
				# 		'operations_role': ['IN', roles],
				# 		'employee_availability': 'Working',
				# 		'date': ['BETWEEN', [today, month_end]]}
				# 	)
				# 	if schedules and attendance:
				# 		'''
				# 			Live Projection = [Employee Attendance(From Start of Month till Yesterday)
				# 				+
				# 				Employee Schedule (From Today to End of Month)] / Post Schedule
				# 		'''
				# 		row.live_projection = (attendance + schedules)/post_schedule
				# 		row.live_projection_rate = row.live_projection * row.rate

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
			'fieldname': 'start_date',
			'label': _('Start Date'),
			'fieldtype': 'Date',
			'width': 100,
		},
		{
			'fieldname': 'end_date',
			'label': _('End Date'),
			'fieldtype': 'Date',
			'width': 100,
		},
		{
			'fieldname': 'es_qty',
			'label': _('Employee Schedule QTY'),
			'fieldtype': 'Int',
			'width': 150,
			'precision':2
		},
		{
			'fieldname': 'ea_qty',
			'label': _('Employee Attendance QTY'),
			'fieldtype': 'Int',
			'width': 150,
			'precision':2
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
			'width': 150
		},
		{
			'fieldname': 'live_projection',
			'label': _('Live Projection'),
			'fieldtype': 'Float',
			'width': 150
		},
		{
			'fieldname': 'live_projection_rate',
			'label': _('Live Projection Rate'),
			'fieldtype': 'Currency',
			'width': 150
		},
		{
			'fieldname': 'rate_type',
			'label': _('Rate Type'),
			'fieldtype': 'Data',
			'width': 150
		},
		{
			'fieldname': 'days_off_cat',
			'label': _('Days Of Category'),
			'fieldtype': 'Data',
			'width': 100,
			'default': ''
		},
	]
