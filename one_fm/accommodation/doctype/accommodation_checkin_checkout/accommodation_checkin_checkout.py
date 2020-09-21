# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AccommodationCheckinCheckout(Document):
	def before_insert(self):
		if self.type == "IN":
			self.naming_series = "CHECKIN-.YYYY.-"
		elif self.type == "OUT":
			self.naming_series = "CHECKOUT-.YYYY.-"

	def after_insert(self):
		self.set_bed_status()

	def on_trash(self):
		self.set_bed_status()

	def set_bed_status(self):
		if self.type == 'IN':
			frappe.db.set_value('Bed', self.bed, 'status', 'Occupied')
		if self.type == 'OUT':
			frappe.db.set_value('Bed', self.bed, 'status', 'Vacant')

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
		if self.checkin_reference:
			checkin = frappe.get_doc('Accommodation Checkin Checkout', self.checkin_reference)
			self.bed = checkin.bed
			self.employee = checkin.employee
			self.accommodation = checkin.accommodation
			self.accommodation_unit = checkin.accommodation_unit
			self.floor = checkin.floor
			self.full_name = checkin.full_name
			self.passport_number = checkin.passport_number
			self.civil_id = checkin.civil_id
			self.new_or_current_resident = checkin.new_or_current_resident
			self.attach_print_accommodation_policy = checkin.attach_print_accommodation_policy
			self.attach_asset_receiving_declaration = checkin.attach_asset_receiving_declaration
