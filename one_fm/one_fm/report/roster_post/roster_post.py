# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cstr, cint, getdate, add_to_date
from calendar import monthrange
from frappe import msgprint
import pandas as pd


post_types_not_filled = set()

def execute(filters=None):
	if filters:
		days_in_month = monthrange(cint(filters.year), cint(filters.month))[1]
		filters["start_date"] = filters.year + "-" + filters.month + "-" + "1"
		filters["end_date"] = add_to_date(filters["start_date"], days = days_in_month-1)
	columns = get_columns(filters) 
	data, chart_data = get_data(filters)
	return columns, data, None, chart_data

def get_columns(filters):
	return [
		_("Date") + ":Date:150",
		_("Active Posts") + ":Int:150",
		_("Posts Off") + ":Int:250",
		_("Posts Filled") + ":Int:250",
		_("Posts Not Filled") + ":Int:250",
		_("Result") + ":Data:150"
	]

def get_data(filters):
	data = []
	labels = []
	datasets = [
		{"name": "Active Posts\n\n\n", "values": []},
		{"name": "Posts Off\n\n\n", "values": []},
		{"name": "Posts Filled\n\n\n", "values": []},
		{"name": "Posts Not Filled\n\n\n", "values": []},
	]
	chart = {}

	if filters:
		for date in pd.date_range(start=filters["start_date"], end=filters["end_date"]):
			active_posts = len(frappe.db.get_list("Post Schedule", {'post_status': 'Planned', 'date': date}, ["post_type"]))
			posts_off = len(frappe.db.get_list("Post Schedule", {'post_status': 'Post Off', 'date': date}))

			posts_filled_count = 0
			posts_not_filled_count = 0

			post_types = frappe.db.get_list("Post Schedule", ["distinct post_type", "post_abbrv"])
			for post_type in post_types:
				# For each post type, get all post schedules and employee schedules assigned to the post type
				posts_count = len(frappe.db.get_list("Post Schedule", {'post_type': post_type.post_type, 'date': date, 'post_status': 'Planned'}))
				posts_fill_count = len(frappe.db.get_list("Employee Schedule", {'post_type': post_type.post_type, 'date': date, 'employee_availability': 'Working'}))

				# Compare count of post schedule vs employee schedule for the given post type, compute post filled/not filled count
				if posts_count == posts_fill_count:
					posts_filled_count = posts_filled_count + posts_fill_count
				elif posts_count > posts_fill_count:
					posts_filled_count = posts_filled_count + posts_fill_count
					posts_not_filled_count = posts_not_filled_count + (posts_count - posts_fill_count)
					global post_types_not_filled
					post_types_not_filled.add(post_type.post_type)

			result = "OK"
			if posts_not_filled_count > 0:
				result = "NOT OK"

			row = [
				cstr(date).split(" ")[0],
				active_posts,
				posts_off,
				posts_filled_count,
				posts_not_filled_count,
				result
			]

			data.append(row)

			labels.append("...")
			datasets[0]["values"].append(active_posts)
			datasets[1]["values"].append(posts_off)
			datasets[2]["values"].append(posts_filled_count)
			datasets[3]["values"].append(posts_not_filled_count)

		chart = {
			"data": {
				"labels": labels,
				"datasets": datasets
			}
		}

		chart["type"] = "line"

	return data, chart


def get_active_posts(date):
	return frappe.db.get_list("Post Schedule", {'post_status': 'Planned', 'date': date}, ["post_type"])

def get_posts_off(date):
	return frappe.db.get_list("Post Schedule", {'post_status': 'Post Off', 'date': date})

@frappe.whitelist()
def get_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(date) from `tabEmployee Schedule` ORDER BY YEAR(date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)


@frappe.whitelist()
def get_post_types_not_filled():
	return post_types_not_filled	