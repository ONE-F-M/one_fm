# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, getdate, flt, add_days
from datetime import datetime
import datetime
# import operator
import re
from datetime import date
from dateutil.relativedelta import relativedelta

def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	return [
		_("Training Program Name") + ":Link/Training Program:250",
		_("Employee") + ":Link/Employee:250",
		_("Employee Name") + ":Link/Employee:300",
		_("Issue Date") + ":Date:150",
		_("Expiry Date") + ":Date:150"
	]

def get_conditions(filters=None):
	conditions = {}
	if filters:
		if filters.get("training_program_name"):
			conditions.update({'training_program_name': filters.get("training_program_name")})

	return conditions

def get_data(filters=None):
	conditions = get_conditions(filters)
	data = []
	training_program_certificate_list = frappe.db.get_list("Training Program Certificate", conditions)
	for training_program_certificate in training_program_certificate_list:
		training_program_certificate_doc = frappe.get_doc("Training Program Certificate", training_program_certificate.name)
		row = [
			training_program_certificate_doc.training_program_name,
			training_program_certificate_doc.employee,
			get_employee_name(training_program_certificate_doc.employee),
			training_program_certificate_doc.issue_date,
			training_program_certificate_doc.expiry_date
		]
		data.append(row)

	return data


def get_employee_name(employee_code):
	return frappe.db.get_value("Employee", employee_code, "employee_name")	