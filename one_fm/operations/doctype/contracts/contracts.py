# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import date

class Contracts(Document):
	def on_update(self):
		add_contracts_items_item_price(self)
		add_contracts_assets_item_price(self)		

@frappe.whitelist()
def get_contracts_asset_items(contracts):
	contracts_item_list = frappe.db.sql("""select ca.item_code,ca.count as qty,ca.uom
	from `tabContract Asset` ca , `tabContracts` c
    where c.name = ca.parent and ca.parenttype = 'Contracts'
	and c.frequency = 'Monthly'
    and ca.docstatus = 0 and ca.parent = %s order by ca.idx asc """,(contracts),as_dict=1)
	
	return contracts_item_list

@frappe.whitelist()
def get_contracts_items(contracts):
	contracts_item_list = frappe.db.sql("""select ca.item_code,ca.head_count as qty
	from `tabContract Item` ca , `tabContracts` c
    where c.name = ca.parent and ca.parenttype = 'Contracts'
    and ca.docstatus = 0 and ca.parent = %s order by ca.idx asc """,(contracts),as_dict=1)
	
	return contracts_item_list

def add_contracts_items_item_price(self):
	for item in self.items:
		name = frappe.db.get_value('Item Price', {'price_list': self.price_list,'item_code':item.item_code
				,'uom':'Hours','selling':1}, ['name'])
		if name:
			target_doc = frappe.get_doc('Item Price', name)
			if target_doc.price_list_rate != item.unit_rate and target_doc.valid_from == date.today():
				target_doc.price_list_rate = item.unit_rate
				target_doc.save()
				frappe.db.commit()
			if target_doc.price_list_rate != item.unit_rate and target_doc.valid_from != date.today():
				item_price = frappe.new_doc('Item Price')
				item_price.item_code = item.item_code
				item_price.uom = 'Hours'
				item_price.price_list = self.price_list
				item_price.selling = 1
				item_price.price_list_rate = item.unit_rate 
				item_price.valid_from = date.today()
				item_price.note = "This rate is auto generated from contracts"
				item_price.reference = self.name
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

		else:
			item_price = frappe.new_doc('Item Price')
			item_price.item_code = item.item_code
			item_price.uom = 'Hours'
			item_price.price_list = self.price_list
			item_price.selling = 1
			item_price.price_list_rate = item.unit_rate 
			item_price.valid_from = date.today()
			item_price.note = "This rate is auto generated from contracts"
			item_price.reference = self.name
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
	return

def add_contracts_assets_item_price(self):
	if self.frequency == "Monthly":
		for item in self.assets:
			name = frappe.db.get_value('Item Price', {'price_list': self.price_list,'item_code':item.item_code
					,'uom':item.uom,'selling':1}, ['name'])
			if name:
				target_doc = frappe.get_doc('Item Price', name)
				if target_doc.price_list_rate != item.unit_rate and target_doc.valid_from == date.today():
					target_doc.price_list_rate = item.unit_rate
					target_doc.save()
					frappe.db.commit()
				if target_doc.price_list_rate != item.unit_rate and target_doc.valid_from != date.today():
					item_price = frappe.new_doc('Item Price')
					item_price.item_code = item.item_code
					item_price.uom = item.uom
					item_price.price_list = self.price_list
					item_price.selling = 1
					item_price.price_list_rate = item.unit_rate 
					item_price.valid_from = date.today()
					item_price.note = "This rate is auto generated from contracts"
					item_price.reference = self.name
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

			else:
				item_price = frappe.new_doc('Item Price')
				item_price.item_code = item.item_code
				item_price.uom = item.uom
				item_price.price_list = self.price_list
				item_price.selling = 1
				item_price.price_list_rate = item.unit_rate 
				item_price.valid_from = date.today()
				item_price.note = "This rate is auto generated from contracts"
				item_price.reference = self.name
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
		return

@frappe.whitelist()
def insert_login_credential(url,user_name,password,client):
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
