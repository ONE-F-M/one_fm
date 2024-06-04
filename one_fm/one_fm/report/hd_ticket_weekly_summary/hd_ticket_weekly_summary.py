# Copyright (c) 2024, omar jaber and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	start_date = filters.get('start_date')
	end_date = filters.get('end_date')

	total_tickets_count = frappe.db.count('HD Ticket', {
		"opening_date": ["between", [start_date, end_date]],
	})

	open_tickets_count = frappe.db.count('HD Ticket', {
		"opening_date": ["between", [start_date, end_date]],
		"status": "Open"
	})

	closed_tickets_count = frappe.db.count('HD Ticket', {
		"opening_date": ["between", [start_date, end_date]],
		"status": "Closed"
	})

	resolved_tickets_count = frappe.db.count('HD Ticket', {
		"opening_date": ["between", [start_date, end_date]],
		"status": "Resolved"
	})

	other_tickets_count = total_tickets_count - (open_tickets_count + closed_tickets_count + resolved_tickets_count)

	columns = [
		{
			"fieldname": "total",
			"fieldtype": "Data",
			"label": "Total Tickets",
			"width": 200
		},
		{
			"fieldname": "open",
			"fieldtype": "Data",
			"label": "Open",
			"width": 200
		},
		{
			"fieldname": "closed",
			"fieldtype": "Data",
			"label": "Closed",
			"width": 200
		},
		{
			"fieldname": "resolved",
			"fieldtype": "Data",
			"label": "Resolved",
			"width": 200
		},
		{
			"fieldname": "other",
			"fieldtype": "Data",
			"label": "Other",
			"width": 200
		},
	]
	
	data = [
		{
			"total": total_tickets_count,
			"open": open_tickets_count,
			"closed": closed_tickets_count,
			"resolved": resolved_tickets_count,
			"other": other_tickets_count,
		}
	]

	chart = {
		"data": {
			"labels": ["Open","Closed","Resolved","Other"],
			"datasets": [
				{
					"name": "HD Ticket Weekly Summary",
					"values": [open_tickets_count, closed_tickets_count, resolved_tickets_count, other_tickets_count]
				}
			]
		},
		"type": "pie",
    	"colors": ['#AACCFF', '#4CBB17', '#90EE90', '#FF9933']
	}
	return columns, data, None, chart, None
