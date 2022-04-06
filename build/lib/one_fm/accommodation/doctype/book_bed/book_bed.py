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

	def after_insert(self):
		self.update_bed_status()

	def update_bed_status(self):
		status = self.booking_status if self.booking_status != 'Cancelled' else 'Vacant'
		if self.booking_status == 'Temporary Booking':
			status = 'Temporarily Booked'
		elif self.booking_status == 'Permanent Booking':
			status = 'Booked'
		if self.book_for == 'Single':
			frappe.db.set_value('Bed', self.bed, 'status', status)
		elif self.book_for == 'Bulk' and slef.bulk_book_bed:
			for bed in self.bulk_book_bed:
				frappe.db.set_value('Bed', bed.bed, 'status', status)

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
				self.employee = employee.name
				self.full_name = employee.employee_name
				self.nationality = employee.one_fm_nationality
				self.religion = employee.one_fm_religion
				self.email = employee.personal_email
				self.contact_number = employee.cell_number
				self.civil_id = employee.one_fm_civil_id
				self.passport_number = employee.passport_number
			else:
				self.get_job_applicant_details()

	def get_job_applicant_details(self):
		filters = {}
		if self.passport_number:
			filters['one_fm_passport_number'] = self.passport_number
		if self.civil_id:
			filters['one_fm_civil_id'] = self.civil_id
		if filters and len(filters)>0:
			job_applicant_id = frappe.db.exists('Job Applicant', filters)
			if job_applicant_id:
				job_applicant = frappe.get_doc('Job Applicant', job_applicant_id)
				self.full_name = job_applicant.applicant_name
				# self.nationality = job_applicant.one_fm_nationality
				self.religion = job_applicant.one_fm_religion
				self.civil_id = job_applicant.one_fm_civil_id
				self.passport_number = job_applicant.one_fm_passport_number
				self.email = job_applicant.one_fm_email_id
				self.contact_number = job_applicant.one_fm_contact_number

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
