# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

import frappe
import json
from datetime import datetime
from frappe import msgprint, _

def execute(filters=None):

	#List of Doctypes that need to be in the report
	doctypes = ['Request for Material', 'Request for Purchase', 'Purchase Order']
	
	columns = get_columns()
	data = get_data(doctypes)
	if not data:
		msgprint(_("No record found"), alert=True, indicator="orange")
	return columns, data

def get_columns():
	#Create Column Name
	columns = [
		{
			"label": ("DocType"),
			"fieldtype": "Data",
			"fieldname": "doctype",
			"width": 150
		},
		{
			"label": ("DocName"),
			"fieldtype": "Dynamic Link",
			"fieldname": "docname",
			"options": "doctype",
			"width": 150
		},
		{
			"label": ("Status"),
			"fieldtype": "Data",
			"fieldname": "status",
			"width": 150
		},
		{
			"label": ("Approved At"),
			"fieldtype": "Data",
			"fieldname": "approved_at",
			"width": 180
		}
	]
	return columns

def get_data(doctypes):
	"""This Function create list of rows consisting of value that will be filled in the table.

	Args:
		doctypes (Array/List): List of Doctypes

	Returns:
		[Data]: List of fetched value top display in the report
	"""
	data = []

	data_list = get_doc_list(doctypes)

	#create list of data
	for d in data_list:
		ref_docname , ref_doctype, approved_at = frappe.get_value("Version", d, ["docname","ref_doctype","modified"])
		status = frappe.get_value(ref_doctype, ref_docname,["status"] )
		row = [ref_doctype,ref_docname, status, approved_at.strftime("%d-%m-%Y %H:%M:%S")]
		data.append(row)
	return data

def get_doc_list(doctypes):
	"""This Function fetches the doc list that list the changes of Doc from "Draft" to "Approved".

	Args:
		doctypes (Array/List): List of Doctypes

	Returns:
		doc list: List of Version Doc that has the required Changes
	"""
	doc_list = []
	#list of doc modified/created by user and is taken place in required Doctype
	data_list = frappe.db.get_list("Version",{'modified_by':frappe.session.user,'ref_doctype':('in',doctypes)},["*"])
	for data in data_list:
		dictionary = json.loads(data.data)

		#get the list of changes
		changes = dictionary.get('changed')
		if changes:
			for change in changes:
				#if the doc had changes in status from Draft to Approved.
				if change[0] == "status" and change[2] == "Approved":
					doc_list.append(data.name)
	return doc_list
