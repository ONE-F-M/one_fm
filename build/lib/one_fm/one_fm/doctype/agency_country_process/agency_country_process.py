# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
# from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document
import functools

class AgencyCountryProcess(Document):
	def onload(self):
		"""Load address and contacts in `__onload`"""
		self.load_address_and_contact()

	def load_address_and_contact(self, key=None):
		"""Loads address list and contact list in `__onload`"""
		from frappe.contacts.doctype.address.address import get_address_display, get_condensed_address
		doc = frappe.get_doc('Agency', self.agency)

		filters = [
			["Dynamic Link", "link_doctype", "=", doc.doctype],
			["Dynamic Link", "link_name", "=", doc.name],
			["Dynamic Link", "parenttype", "=", "Address"],
		]
		address_list = frappe.get_all("Address", filters=filters, fields=["*"])

		address_list = [a.update({"display": get_address_display(a)})
			for a in address_list]

		address_list = sorted(address_list,
			key = functools.cmp_to_key(lambda a, b:
				(int(a.is_primary_address - b.is_primary_address)) or
				(1 if a.modified - b.modified else 0)), reverse=True)

		self.set_onload('addr_list', address_list)

		contact_list = []
		filters = [
			["Dynamic Link", "link_doctype", "=", doc.doctype],
			["Dynamic Link", "link_name", "=", doc.name],
			["Dynamic Link", "parenttype", "=", "Contact"],
		]
		contact_list = frappe.get_all("Contact", filters=filters, fields=["*"])

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
				address = frappe.get_doc("Address", contact.address)
				contact["address"] = get_condensed_address(address)

		contact_list = sorted(contact_list,
			key = functools.cmp_to_key(lambda a, b:
				(int(a.is_primary_contact - b.is_primary_contact)) or
				(1 if a.modified - b.modified else 0)), reverse=True)

		self.set_onload('contact_list', contact_list)
