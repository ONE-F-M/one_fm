# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AccommodationMeterReadingRecord(Document):
	def on_submit(self):
		self.set_last_reading_details()

	def set_last_reading_details(self):
		query = """
			update
				`tabAccommodation Meter Reading`
			set
				last_reading = %(current_reading)s, last_reading_date = %(reading_date)s
			where
				parenttype = %(reference_doctype)s and parent = %(reference_name)s
				and meter_reference = %(meter_reference)s
		"""
		return frappe.db.sql(query,
			{
				'current_reading': self.current_reading,
				'reading_date': self.reading_date,
				'reference_doctype': self.reference_doctype,
				'reference_name': self.reference_name,
				'meter_reference': self.meter_reference
			}
		)

def filter_meter_ref(doctype, txt, searchfield, start, page_len, filters):
	query = """
		select
			meter_reference
		from
			`tabAccommodation Meter Reading`
		where
			meter_reference like %(txt)s
	"""
	if filters.get('meter_type'):
		query += " and meter_type = %(meter_type)s"
	if filters.get('reference_doctype') and filters.get('reference_name'):
		query += " and parenttype = %(reference_doctype)s and parent = %(reference_name)s"
	query += " limit %(start)s, %(page_len)s"
	return frappe.db.sql(query,
		{
			'reference_doctype': filters.get("reference_doctype"),
			'reference_name': filters.get("reference_name"),
			'meter_type': filters.get("meter_type"),
			'start': start,
			'page_len': page_len,
			'txt': "%%%s%%" % txt
		}
	)

@frappe.whitelist()
def get_accommodation_meter_details(meter_reference):
	meter = frappe.get_doc('Accommodation Meter', meter_reference)
	reading = frappe.get_doc('Accommodation Meter Reading', {'meter_reference': meter_reference})
	return {'meter': meter, 'reading': reading}

@frappe.whitelist()
def get_accommodation_meter(meter_type, reference_doctype, reference_name):
	filters = {'parenttype': reference_doctype, 'parent': reference_name, 'meter_type': meter_type}
	if frappe.db.exists('Accommodation Meter Reading', filters):
		return frappe.get_doc('Accommodation Meter Reading', filters)
