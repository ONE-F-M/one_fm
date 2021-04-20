# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr,month_diff,today,getdate

class Contracts(Document):
	def validate(self):
		self.calculate_contract_duration()

	def on_update(self):
		add_contracts_assets_item_price(self)

	def calculate_contract_duration(self):
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

def add_contracts_assets_item_price(self):
	if self.frequency == "Monthly":
		for item in self.assets:
			item_price_list = frappe.get_list("Item Price", {"price_list": self.price_list, "item_code": item.item_code, 
					"uom": item.uom, "selling": 1}, "name", order_by="valid_from desc")
			if item_price_list:
				item_price = item_price_list[0].name
				target_doc = frappe.get_doc('Item Price', item_price)
				if target_doc.price_list_rate != item.unit_rate and target_doc.valid_from == getdate(today()):
					target_doc.price_list_rate = item.unit_rate
					target_doc.save()
					frappe.db.commit()
				if target_doc.price_list_rate != item.unit_rate and target_doc.valid_from != getdate(today()):
					add_item_price_detail(item, self.price_list, self.name)
			else:
				add_item_price_detail(item, self.price_list, self.name)

def add_item_price_detail(item, price_list, contracts):
	item_price = frappe.new_doc('Item Price')
	item_price.item_code = item.item_code
	item_price.uom = item.uom
	item_price.price_list = price_list
	item_price.selling = 1
	item_price.price_list_rate = item.unit_rate 
	item_price.valid_from = today()
	item_price.note = "This rate is auto generated from contracts"
	item_price.reference = contracts
	item_price.flags.ignore_permissions  = True
	item_price.update({
		'item_code': item_price.item_code,
		'uom': item_price.uom,
		'price_list': item_price.price_list,
		'selling': item_price.selling,
		'price_list_rate': item_price.price_list_rate,
		'valid_from': item_price.valid_from,
		'note': item_price.note,
		'reference': item_price.reference
	}).insert()

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
