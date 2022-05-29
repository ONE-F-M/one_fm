# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import pandas as pd
from frappe.utils import getdate, get_first_day, get_last_day

def execute(filters=None):
	if filters:
		date = str(getdate())

		first_day_of_month = str(get_first_day(date))
		last_day_of_month = str(get_last_day(date))

		filters["start_date"] = first_day_of_month
		filters["end_date"] = last_day_of_month

	return RosterProjection(filters).run()


class RosterProjection(object):
	def __init__(self, filters=None):
		self.filters  = frappe._dict(filters or {})


	def run(self):
		self.get_columns()
		self.get_data()

		return self.columns, self.data, None, self.chart
	
	def get_columns(self):
		self.columns = [{
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 150
        }]

		self.columns.append({
            "label": _("Project"),
            "fieldname": "project",
            "fieldtype": "Link",
			"options": "Project",
            "width": 250
        })

		self.columns.append({
			"label": _("Sale Item"),
            "fieldname": "sale_item",
            "fieldtype": "Data",
            "width": 250
		})

		self.columns.append({
			"label": _("Unit Rate"),
            "fieldname": "unit_rate",
            "fieldtype": "float",
            "width": 100
		})

		self.columns.append({
			"label": _("Quantity"),
            "fieldname": "qty",
            "fieldtype": "int",
            "width": 150
		})

		self.columns.append({
			"label": _("Projection"),
            "fieldname": "projection",
            "fieldtype": "float",
            "width": 150
		})

		self.columns.append({
			"label": _("Live Projection"),
            "fieldname": "live_projection",
            "fieldtype": "float",
            "width": 150
		})

	def get_data(self):
		self.data = []
		labels = []

		datasets = [
			{"name": "Projection\n\n\n", "values": []},
			{"name": "Live Projection\n\n\n", "values": []}
		]

		self.chart = {}

		if self.filters:
			contract_name = self.filters['contract_name']
			contract_doc = frappe.get_doc("Contracts", contract_name)

			project = contract_doc.project
			
			for date in pd.date_range(start=self.filters['start_date'], end=self.filters['end_date']):

				for item in contract_doc.items:
					item_group = str(item.subitem_group)

					if item_group.lower() == "service":
						item_projection = get_item_projection(item, project, date)
						item_live_projection = get_item_live_projection(item, project, date)

						row = [
							str(date).split(" ")[0],
							project,
							item.item_code,
							item.rate,
							item.count,
							item_projection,
							item_live_projection
						]

						self.data.append(row)

						# Add data to chart
						labels.append("...")
						datasets[0]['values'].append(item_projection)
						datasets[1]['values'].append(item_live_projection)

			self.chart = {
                "data": {
                    "labels": labels,
                    "datasets": datasets
                }
            }

			self.chart["type"] = "line"



def get_item_projection(item, project, date):

	# Get post types with sale item as item code
	post_type_list = frappe.db.get_list("Post Type", pluck='name', filters={'sale_item': item.item_code})
	
	# Get employee schedules
	es_filters = {
			'project': project,
			'post_type': ['in', post_type_list],
			'employee_availability': 'Working',
			'date': date
		}

	employee_schedules_count = len(frappe.db.get_list("Employee Schedule", es_filters))

	return employee_schedules_count


def get_item_live_projection(item, project, date):
	
	# Get post types with sale item as item code
	post_type_list = frappe.db.get_list("Post Type", pluck='name', filters={'sale_item': item.item_code}) # ==> list of post type names : ['post type A', 'post type B', ...]

	attendance_filters = {
		'attendance_date': date,
		'post_type': ['in', post_type_list],
		'project': project,
		'status': "Present"
	}

	# Get attendances in date range and post type
	attendance_count = len(frappe.db.get_list("Attendance", attendance_filters))

	return attendance_count