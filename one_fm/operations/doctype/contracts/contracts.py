# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr,month_diff,today,getdate,date_diff,add_years, cint, add_to_date, get_first_day, get_last_day, get_datetime
from frappe import _

class Contracts(Document):
	def validate(self):
		self.calculate_contract_duration()
		if self.overtime_rate == 0:
			frappe.msgprint(_("Overtime rate not set."), alert=True, indicator='orange')

	def calculate_contract_duration(self):
		duration_in_days = date_diff(self.end_date, self.start_date)
		self.duration_in_days = cstr(duration_in_days)
		full_months = month_diff(self.end_date, self.start_date)
		years = int(full_months / 12)
		months = int(full_months % 12)
		if(years > 0):
			self.duration = cstr(years) + ' year'
		if(years > 0 and months > 0):
			self.duration += ' and ' + cstr(months) + ' month'
		if(years < 1 and months > 0):
			self.duration = cstr(months) + ' month'

	@frappe.whitelist()
	def generate_sales_invoice(self):

		items_amounts = get_service_items_invoice_amounts(self)
		try:
			print("creating sales invoice...")
			sales_invoice_doc = frappe.new_doc("Sales Invoice")
			sales_invoice_doc.customer = self.client
			
			date = cstr(getdate())
			temp_invoice_year = date.split("-")[0]
			temp_invoice_month = date.split("-")[1]
			invoice_date = temp_invoice_year + "-" + temp_invoice_month + "-" + cstr(self.due_date)

			sales_invoice_doc.due_date = invoice_date
			sales_invoice_doc.project = self.project
			sales_invoice_doc.contracts = self.name
			sales_invoice_doc.ignore_pricing_rule = 1

			income_account = frappe.db.get_value("Project", self.project, ["income_account"])

			for item in items_amounts:
				print('appending item: ', item)
				sales_invoice_doc.append('items', {
					'item_code': item["item_code"],
					'item_name': item["item_code"],
					'description': item["item_description"],
					'qty': item["qty"],
					'uom': item["uom"],
					'rate': item["rate"],
					'amount': item["amount"],
					'income_account': income_account
				})
				print('added item: ', item)

			print('saving sales invoice...')
			sales_invoice_doc.save()
			frappe.db.commit()
			
			return sales_invoice_doc
		
		except Exception as error:
			frappe.throw(_(error))

	def on_cancel(self):
		frappe.throw("Contracts cannot be cancelled. Please try to ammend the existing record.")

@frappe.whitelist()
def get_contracts_asset_items(contracts):
	contracts_item_list = frappe.db.sql("""
		SELECT ca.item_code, ca.count as qty, ca.uom
		FROM `tabContract Asset` ca , `tabContracts` c
		WHERE c.name = ca.parent and ca.parenttype = 'Contracts'
		and c.frequency = 'Monthly'
		and ca.docstatus = 0 and ca.parent = %s order by ca.idx asc 
	""", (contracts), as_dict=1)	
	return contracts_item_list

@frappe.whitelist()
def get_contracts_items(contracts):
	contracts_item_list = frappe.db.sql("""
		SELECT ca.item_code,ca.count as qty, uom, price_list_rate, days_off
		FROM `tabContract Item` ca , `tabContracts` c
		WHERE c.name = ca.parent and ca.parenttype = 'Contracts'
		and ca.docstatus = 0 and ca.parent = %s order by ca.idx asc 
	""", (contracts), as_dict=1)	
	return contracts_item_list

@frappe.whitelist()
def insert_login_credential(url, user_name, password, client):
	password_management_name = client+'-'+user_name
	password_management = frappe.new_doc('Password Management')
	password_management.flags.ignore_permissions  = True
	password_management.update({
		'password_management':password_management_name,
		'password_category': 'Customer Portal',
		'url': url,
		'username':user_name,
		'password':password
	}).insert()

	frappe.msgprint(msg = 'Online portal credentials are saved into password management',
       title = 'Notification',
       indicator = 'green'
    )

	return 	password_management

#renew contracts by one year
def auto_renew_contracts():
	filters = {
		'end_date' : today(),
		'is_auto_renewal' : 1
	}
	contracts_list = frappe.db.get_list('Contracts', fields="name", filters=filters, order_by="start_date")
	for contract in contracts_list:
		contract_doc = frappe.get_doc('Contracts', contract)
		contract_doc.end_date = add_years(contract_doc.end_date, 1)
		contract_doc.save()
		frappe.db.commit()

def get_service_items_invoice_amounts(contract):
	first_day_of_month = cstr(get_first_day(getdate()))
	last_day_of_month = cstr(get_last_day(getdate()))

	temp_invoice_year = first_day_of_month.split("-")[0]
	temp_invoice_month = first_day_of_month.split("-")[1]

	invoice_date = temp_invoice_year + "-" + temp_invoice_month + "-" + cstr(contract.due_date)

	project = contract.project
	contract_overtime_rate = contract.overtime_rate

	master_data = []
    
	for item in contract.items:
		item_group = str(item.subitem_group)

		if item_group.lower() == "service":
			uom = str(item.uom)

			if uom.lower() == "hourly":
				data = get_item_hourly_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate)
				master_data.append(data)

			elif uom.lower() == "daily":
				data = get_item_daily_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate)
				master_data.append(data)

			elif uom.lower() == "monthly":
				data = get_item_monthly_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate)
				master_data.append(data)

	return master_data

def get_item_hourly_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate):
	""" This method computes the total number of hours worked by employees for a particular service item by referring to
		the attendance for days prior to invoice due date and employee schedules ahead of the invoice due date, 
		hence calculating the amount for the service amount.

	Args:
		item: item object
		project: project linked with contract
		first_day_of_month: date of first day of the month
		last_day_of_month: date of last day of the month
		invoice_date: date of invoice due
		contract_overtime_rate: hourly overtime rate specified for the contract

	Returns:
		dict: item amount and item data
	"""
	item_code = item.item_code
	
	days_in_month = int(last_day_of_month.split("-")[2])

	item_price = item.item_price
	item_rate = item.rate

	shift_hours = item.shift_hours
	working_days_in_month = days_in_month - (int(item.days_off) * 4)

	item_hours = 0
	expected_item_hours = working_days_in_month * shift_hours * cint(item.count)
	amount = 0

	# Get post types with sale item as item code
	post_type_list = frappe.db.get_list("Post Type", pluck='name', filters={'sale_item': item_code}) # ==> list of post type names : ['post type A', 'post type B', ...]

	# Get attendances in date range and post type
	attendances = frappe.db.get_list("Attendance", 
		{
			'attendance_date': ['between', (first_day_of_month, add_to_date(invoice_date, days=-1))],
			'post_type': ['in', post_type_list],
			'project': project,
			'status': "Present"
		}, 
		["operations_shift", "in_time", "out_time", "working_hours"]
	)

	# Compute working hours
	for attendance in attendances:
		hours = 0
		if attendance.working_hours:
			hours += attendance.working_hours
		
		elif attendance.in_time and attendance.out_time:
			hours += round((get_datetime(attendance.in_time) - get_datetime(attendance.out_time)).total_seconds() / 3600, 1)

		# Use working hours as duration of shift if no in-out time available in attendance
		elif attendance.operations_shift:
			hours += float(frappe.db.get_value("Operations Shift", {'name': attendance.operations_shift}, ["duration"]))
	
		item_hours += hours
			
	# Get employee schedules for remaining days of the month from the invoice due date if due date is before last day
	if invoice_date < last_day_of_month:
		employee_schedules = frappe.db.get_list("Employee Schedule", 
			{
				'project': project,
				'post_type': ['in', post_type_list],
				'employee_availability': 'Working',
				'date': ['between', (invoice_date, last_day_of_month)],
			},
			["shift"]
		)

		# Use item hours as duration of shift
		for es in employee_schedules:
			item_hours += float(frappe.db.get_value("Operations Shift", {'name': es.shift}, ["duration"]))

	# If total item hours exceed expected hours, apply overtime rate on extra hours
	if item_hours > expected_item_hours:
		normal_amount = item_rate * expected_item_hours
		overtime_amount = contract_overtime_rate * (item_hours - expected_item_hours)

		amount = round(normal_amount + overtime_amount, 3)

	else:
		amount = round(item_hours * item_rate, 3)

	return {
		'item_code': item_code,
		'item_description': item_price,
		'qty': item_hours,
		'uom': item.uom,
		'rate': item_rate,
		'amount': amount,
	}

def get_item_daily_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate):
	""" This method computes the total number of days worked by employees for a particular service item by referring to
		the attendance for days prior to invoice due date and employee schedules ahead of the invoice due date, 
		hence calculating the amount for the service amount.

	Args:
		item: item object
		project: project linked with contract
		first_day_of_month: date of first day of the month
		last_day_of_month: date of last day of the month
		invoice_date: date of invoice due
		contract_overtime_rate: hourly overtime rate specified for the contract

	Returns:
		dict: item amount and item data
	"""
	item_code = item.item_code
	item_price = item.item_price
	item_rate = item.rate
	shift_hours = item.shift_hours
	days_in_month = int(last_day_of_month.split("-")[2])

	working_days_in_month = days_in_month - (int(item.days_off) * 4)

	item_days = 0
	expected_item_days = working_days_in_month * cint(item.count)
	amount = 0

	# Get post types with sale item as item code
	post_type_list = frappe.db.get_list("Post Type", pluck='name', filters={'sale_item': item_code}) # ==> list of post type names : ['post type A', 'post type B', ...]

	# Get attendances in date range and post type
	attendances = len(frappe.db.get_list("Attendance", pluck='name',
		filters={
			'attendance_date': ['between', (first_day_of_month, add_to_date(invoice_date, days=-1))],
			'post_type': ['in', post_type_list],
			'project': project,
			'status': "Present"
		}
	))

	item_days += attendances
			
	# Get employee schedules for remaining days of the month from the invoice due date if due date is before last day
	if invoice_date < last_day_of_month:
		employee_schedules = len(frappe.db.get_list("Employee Schedule", pluck='name',
			filters={
				'project': project,
				'post_type': ['in', post_type_list],
				'employee_availability': 'Working',
				'date': ['between', (invoice_date, last_day_of_month)],
			}
		))

		item_days += employee_schedules

	# If total item days exceed expected days, apply overtime rate on extra days
	if item_days > expected_item_days:
		normal_amount = item_rate * expected_item_days
		
		overtime_days = item_days - expected_item_days
		overtime_amount = contract_overtime_rate * shift_hours * overtime_days

		amount = round(normal_amount + overtime_amount, 3)

	else:
		amount = round(item_days * item_rate, 3)

	return {
		'item_code': item_code,
		'item_description': item_price,
		'qty': item_days,
		'uom': item.uom,
		'rate': item_rate,
		'amount': amount,
	}

def get_item_monthly_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate):
	""" This method computes the total number of hours worked by employees for a particular service item by referring to
		the attendance for days prior to invoice due date and employee schedules ahead of the invoice due date.
		If the number of days worked for this item is equal to the expected number of days, amount is directly applied as monthly rate.
		If the number of days worked for this item exceeds to the expected number of days, overtime rate is applied for extra days
		the number of days worked for this item is less than the expected number of days, daily rate is computed and deducted from monthly rate.

	Args:
		item: item object
		project: project linked with contract
		first_day_of_month: date of first day of the month
		last_day_of_month: date of last day of the month
		invoice_date: date of invoice due
		contract_overtime_rate: hourly overtime rate specified for the contract

	Returns:
		dict: item amount and item data
	"""
	item_code = item.item_code
	item_price = item.item_price
	item_rate = item.rate
	shift_hours = item.shift_hours
	days_in_month = int(last_day_of_month.split("-")[2])

	working_days_in_month = days_in_month - (int(item.days_off) * 4)

	item_days = 0
	expected_item_days = working_days_in_month * cint(item.count)
	amount = 0

	# Get post types with sale item as item code
	post_type_list = frappe.db.get_list("Post Type", pluck='name', filters={'sale_item': item_code}) # ==> list of post type names : ['post type A', 'post type B', ...]

	# Get attendances in date range and post type
	attendances = len(frappe.db.get_list("Attendance", pluck='name',
		filters={
			'attendance_date': ['between', (first_day_of_month, add_to_date(invoice_date, days=-1))],
			'post_type': ['in', post_type_list],
			'project': project,
			'status': "Present"
		}
	))

	item_days += attendances
			
	# Get employee schedules for remaining days of the month from the invoice due date if due date is before last day
	if invoice_date < last_day_of_month:
		employee_schedules = len(frappe.db.get_list("Employee Schedule", pluck='name',
			filters={
				'project': project,
				'post_type': ['in', post_type_list],
				'employee_availability': 'Working',
				'date': ['between', (invoice_date, last_day_of_month)],
			}
		))

		item_days += employee_schedules

	# If total item days exceed expected days, apply overtime rate on extra days
	if item_days > expected_item_days:
		overtime_days = item_days - expected_item_days
		overtime_amount = contract_overtime_rate * shift_hours * overtime_days

		amount = round((item_rate + overtime_amount) * cint(item.count), 3)

	elif item_days < expected_item_days:
		daily_rate = item_rate / working_days_in_month
		missing_days = expected_item_days - item_days
		
		amount = round(cint(item.count) * item_rate - (daily_rate * missing_days), 3)

	elif item_days == expected_item_days:
		amount = item_rate * cint(item.count)

	return {
		'item_code': item_code,
		'item_description': item_price,
		'qty': cint(item.count),
		'uom': item.uom,
		'rate': item_rate,
		'amount': amount,
	}