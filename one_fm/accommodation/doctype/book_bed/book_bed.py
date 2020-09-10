# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.model.document import Document
from six import string_types

class BookBed(Document):
	def before_insert(self):
		if self.booking_status == "Temporary Booking":
			self.naming_series = "TBB-.YYYY.-"

	def on_update(self):
		self.update_bed_status()

	def update_bed_status(self):
		status = self.booking_status if self.booking_status != 'Cancelled' else 'Vacant'
		frappe.db.set_value('Bed', self.bed, 'status', status)

	def get_employee_details(self):
		filters = {}
		if self.passport_number:
			filters['passport_number'] = self.passport_number
		if self.civil_id:
			filters['one_fm_civil_id'] = self.civil_id
		if self.employee:
			filters['name'] = self.employee
		if filters and len(filters)>0:
			employee_id = frappe.db.exists('Employee', filters)
			if employee_id:
				employee = frappe.get_doc('Employee', employee_id)
				self.full_name = employee.employee_name
				self.nationality = employee.one_fm_nationality
				self.religion = employee.one_fm_religion
				self.email = employee.personal_email
				self.contact_number = employee.cell_number

@frappe.whitelist()
def get_accommodation_bed_space(filters):
	if isinstance(filters, string_types):
		filters = json.loads(filters)
	return frappe.get_all('Bed', filters=filters, fields=["*"])

@frappe.whitelist()
def get_nearest_accommodation(filters, location=False):
	filters = json.loads(filters)
	accommodation_list = frappe.get_all('Accommodation', filters=filters, fields=["*"])
	for accommodation in accommodation_list:
		filters = {'status': 'Vacant', 'accommodation': accommodation.name, 'disabled': False}
		accommodation_bed_space = get_accommodation_bed_space(filters)
		if accommodation_bed_space and len(accommodation_bed_space) > 0:
			accommodation['vacant_bed'] = len(accommodation_bed_space)
		else:
			accommodation['vacant_bed'] = 'No Vacant Bed'
	return accommodation_list


from math import cos, asin, sqrt

def distance(lat1, lon1, lat2, lon2):
    p = 0.017453292519943295
    a = 0.5 - cos((lat2-lat1)*p)/2 + cos(lat1*p)*cos(lat2*p) * (1-cos((lon2-lon1)*p)) / 2
    return 12742 * asin(sqrt(a))

def closest(data, v):
    return min(data, key=lambda p: distance(v['lat'],v['lon'],p['lat'],p['lon']))

tempDataList = [{'lat': 39.7612992, 'lon': -86.1519681},
                {'lat': 39.762241,  'lon': -86.158436 },
                {'lat': 39.7622292, 'lon': -86.1578917}]

v = {'lat': 39.7622290, 'lon': -86.1519750}
print(closest(tempDataList, v))
