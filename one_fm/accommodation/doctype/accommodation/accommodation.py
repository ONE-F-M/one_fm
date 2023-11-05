# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import functools
from frappe.model.document import Document

class Accommodation(Document):
	def autoname(self):
		self.name = get_latest_accommodation_code(self)

	def onload(self):
		set_contact_list(self)

def get_latest_accommodation_code(doc):
	accommodation_code = frappe.db.sql("select name+1 from `tabAccommodation` order by name desc limit 1")
	new_accommodation_code = accommodation_code[0][0] if accommodation_code else 1
	return str(int(new_accommodation_code)).zfill(2)

def set_contact_list(doc):
	contact_list_fields = {
		'owner_contact_list': 'owner_contact',
		'legal_representative_contact_list': 'legal_representative_contact',
		'other_primary_point_of_contact_list': 'other_primary_point_of_contact',
		'legal_authorization_contact_list': 'legal_authorization_contact'
		}
	for list_field in contact_list_fields:
		contact_list = []
		contact_list = frappe.get_all("Contact", filters={'name': doc.get(contact_list_fields[list_field])}, fields=["*"])
		for contact in contact_list:
			contact["email_ids"] = frappe.get_list("Contact Email", filters={
					"parenttype": "Contact",
					"parent": contact.name,
					"is_primary": 0
				}, fields=["email_id"])

			contact["phone_nos"] = frappe.get_list("Contact Phone", filters={
					"parenttype": "Contact",
					"parent": contact.name,
					"is_primary_phone": 0,
					"is_primary_mobile_no": 0
				}, fields=["phone"])

			if contact.address:
				from frappe.contacts.doctype.address.address import get_condensed_address
				address = frappe.get_doc("Address", contact.address)
				contact["address"] = get_condensed_address(address)

		contact_list = sorted(contact_list,
			key = functools.cmp_to_key(lambda a, b:
				(int(a.is_primary_contact - b.is_primary_contact)) or
				(1 if a.modified - b.modified else 0)), reverse=True)

		doc.set_onload(list_field, contact_list)

def accommodation_contact_update(doc, method):
	link_name = doc.get_link_for('Accommodation')
	if link_name and doc.one_fm_doc_contact_field:
		frappe.db.set_value('Accommodation', link_name, doc.one_fm_doc_contact_field, doc.name)
