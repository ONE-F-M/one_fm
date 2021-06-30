# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr,month_diff,today,getdate,date_diff,add_years

class Contracts(Document):
	def validate(self):
		self.calculate_contract_duration()

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
		SELECT ca.item_code,ca.head_count as qty
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