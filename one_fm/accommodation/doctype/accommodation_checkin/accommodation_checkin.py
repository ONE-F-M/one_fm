# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AccommodationCheckin(Document):
	def get_checkin_details_from_booking(self):
		if self.employee and not self.booking_reference:
			employee = frappe.get_doc('Employee', self.employee)
			self.full_name = employee.employee_name
			self.passport_number = employee.passport_number
			self.civil_id = employee.one_fm_civil_id
		if self.booking_reference:
			book_bed = frappe.get_doc('Book Bed', self.booking_reference)
			self.bed = book_bed.bed
			bed = frappe.get_doc('Bed', self.bed)
			self.accommodation = bed.accommodation
			self.accommodation_unit = bed.accommodation_unit
			self.floor = bed.floor_name
			self.full_name = book_bed.full_name
			self.passport_number = book_bed.passport_number
			self.civil_id = book_bed.civil_id
			filters = {}
			if self.passport_number:
				filters['passport_number'] = self.passport_number
			if self.civil_id:
				filters['one_fm_civil_id'] = self.civil_id
			if filters and len(filters)>0:
				self.employee = frappe.db.exists('Employee', filters)
