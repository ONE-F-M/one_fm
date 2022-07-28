# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

from datetime import datetime
import frappe
from frappe import _
from frappe.utils import today, add_days

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data


def get_data(filters):
	results = []
	use_attendance = False
	to_date = f"{filters.year}-{filters.month}-31"
	live_today = today()
	add_schedule = False

	if (int(filters.month) == int(datetime.today().month)) and (int(filters.year) == int(datetime.today().year)):
		if datetime.today().day != 1:
			use_attendance = True
			to_date = add_days(live_today, -1)
			add_schedule = True
	else:
		live_today = f"{filters.year}-{filters.month}-01"
		use_attendance = True

	contracts = frappe.db.get_list('Contracts')
	for contracts in contracts:
		es_query = f"""
			SELECT con.client, con.project, con_item.item_code, con_item.count, con_item.rate, 
			con_item.count*con_item.rate as total_rate, COUNT(es.name) as projection
			FROM `tabContracts` con
			LEFT JOIN `tabContract Item` con_item ON con_item.parent=con.name
			LEFT JOIN `tabEmployee Schedule` es ON es.project=con.project
			LEFT JOIN `tabPost Type` pt ON pt.name=es.post_type
			WHERE con.name = \"{contracts.name}\"
			AND es.employee_availability='Working'
			AND con_item.item_code=pt.sale_item
			AND es.date BETWEEN "{filters.year}-{filters.month}-01" AND "{filters.year}-{filters.month}-31"
			GROUP BY con_item.item_code
		"""
		ps_query = f"""
			SELECT con.client, con.project, con_item.item_code, con_item.count, con_item.rate, 
			con_item.count*con_item.rate as total_rate, COUNT(ps.name) as projection
			FROM `tabContracts` con
			LEFT JOIN `tabContract Item` con_item ON con_item.parent=con.name
			LEFT JOIN `tabPost Schedule` ps ON ps.project=con.project
			LEFT JOIN `tabPost Type` pt ON pt.name=ps.post_type
			WHERE con.name = \"{contracts.name}\"
			AND ps.post_status='Planned'
			AND con_item.item_code=pt.sale_item
			AND ps.date BETWEEN "{filters.year}-{filters.month}-01" AND "{filters.year}-{filters.month}-31"
			GROUP BY con_item.item_code
		"""
		es_data = frappe.db.sql(es_query, as_dict=1)
		ps_data = frappe.db.sql(ps_query, as_dict=1)
		ps_data_dict = {}
		at_data_dict = {}
		for i in ps_data:
			ps_data_dict[i.project+'-'+i.item_code] = i

		for i in es_data:
			ps_key = ps_data_dict.get(i.project+'-'+i.item_code)
			if ps_key:
				i.projection = i.projection/ps_key.projection
				i.projection_rate = i.rate*i.projection
				i.ps_projection = ps_key.projection
			else:
				i.projection = 0
				i.projection_rate = 0
				i.ps_projection = 0

		# 	# Compute live projection
		if es_data and use_attendance:
			attendance_data = get_live_attendance_query(contracts, filters, to_date)

			if attendance_data:
				for i in attendance_data:
					at_data_dict[i.project+'-'+i.item_code] = i
				if add_schedule:
					schedule_data = get_live_schedule_query(contracts, filters, live_today)
					if schedule_data:
						for i in schedule_data:
							sdt_key = at_data_dict.get(i.project+'-'+i.item_code)
							if sdt_key:
								sdt_key.attendance += i.projection


				for i in es_data:
					at_key = at_data_dict.get(i.project+'-'+i.item_code)
					if at_key:
						i.live_projection = at_key.attendance/i.ps_projection if i.ps_projection else 0
						i.live_projection_rate = i.live_projection * i.rate
					else:
						i.live_projection = 0
						i.live_projection_rate = 0


		if es_data:
			results+=es_data

	return results

def get_live_schedule_query(contracts, filters, start_date):
	schedule_query = f"""
		SELECT con.client, con.project, con_item.item_code, con_item.count, con_item.rate, 
		con_item.count*con_item.rate as total_rate, COUNT(es.name) as projection
		FROM `tabContracts` con
		LEFT JOIN `tabContract Item` con_item ON con_item.parent=con.name
		LEFT JOIN `tabEmployee Schedule` es ON es.project=con.project
		LEFT JOIN `tabPost Type` pt ON pt.name=es.post_type
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
		LEFT JOIN `tabPost Type` pt ON pt.name=at.post_type
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
			'width': 100
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
