# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, re
from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact, delete_contact_and_address
from frappe import _
from frappe.utils import getdate, today
from one_fm.one_fm.doctype.demand_letter.demand_letter import get_valid_demand_letter
from one_fm.one_fm.doctype.agency_contract.agency_contract import get_valid_agency_contract

class Agency(Document):
	def validate(self):
		self.validate_active_agency()
		if self.agency_website:
			validate_website_adress(self.agency_website)

	def after_insert(self):
		supplier = self.create_supplier_if_not_created()
		if supplier:
			self.supplier_code = supplier.name
		self.save(ignore_permissions=True)

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)

	def on_trash(self):
		delete_contact_and_address('Customer', self.name)

	def create_supplier_if_not_created(self):
		if not self.supplier_code:
			return create_supplier_for_agency(self)

	def validate_active_agency(self):
		if self.active:
			active_details = is_agency_active(self)
			if not active_details['active']:
				frappe.throw(_(active_details['message']))

@frappe.whitelist()
def validate_website_adress(website):
	regex = re.compile(
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

	if(bool(re.match(regex, website))==True):
		return True
	return False

def create_supplier_for_agency(agency):
	supplier = frappe.new_doc('Supplier')
	supplier.supplier_name = agency.agency
	supplier.country = agency.country
	supplier.website = agency.agency_website
	supplier.save(ignore_permissions=True)
	return supplier

def is_agency_active(agency):
	active = True
	msg = "Active"
	if not agency.attach_copy_of_agency_license:
		active = False
		msg = "Attach Copy of Agency Lisence to Make Agency Active"
	elif not agency.verify_copy_of_agency_license:
		active = False
		msg = "Please Verify if the Agency has an Country Authorized Licences"
	elif getdate(today()) > getdate(agency.license_validity_date):
		active = False
		msg = "Agency Lisence Validity is Expired"
	elif not get_valid_agency_contract(agency.name):
		active = False
		msg = "Agency has no Active or Valid Contract"
	elif not get_valid_demand_letter(agency.name):
		active = False
		msg = "Agency has no Valid Demand Letter"

	return {'active': active, 'message': msg}

def make_agency_active(agency):
	if is_agency_active(agency)['active']:
		agency.active = True
		agency.save(ignore_permissions=True)
