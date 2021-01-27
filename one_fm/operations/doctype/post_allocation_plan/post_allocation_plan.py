# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PostAllocationPlan(Document):
	pass

@frappe.whitelist()
def filter_posts(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		SELECT post
		FROM `tabPost Schedule`
		WHERE 
			post_status="Planned"
		AND shift=%(shift)s
		AND date=%(date)s 
	""", {
		'shift': frappe.db.escape(filters.get("operations_shift")),
		'date': frappe.db.escape(filters.get("date"))
	})

@frappe.whitelist()
def get_table_data(operations_shift, date):
	print(operations_shift, date)
	employees = frappe.get_all("Employee Schedule", {'date': date, 'shift': operations_shift, 'employee_availability': 'Working'}, ["employee", "employee_name"])
	posts = frappe.get_all("Post Schedule", {'date': date, 'shift': operations_shift, 'post_status': 'Planned'})
	print(employees)
	print(posts)
	return {
		'employees': employees, 
		'posts': posts
	}