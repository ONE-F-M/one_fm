# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class AccommodationCheckinCheckout(Document):
	def validate(self):
		if self.is_new():
			self.validate_checkin_checkout()
		self.set_accommodation_policy()

	def set_accommodation_policy(self):
		if self.employee:
			policy = frappe.db.get_value('Employee', self.employee, 'one_fm_accommodation_policy')
			if not self.attach_print_accommodation_policy and policy:
				self.attach_print_accommodation_policy = policy
			elif not policy and self.attach_print_accommodation_policy:
				frappe.db.set_value('Employee', self.employee, 'one_fm_accommodation_policy', self.attach_print_accommodation_policy)

	def validate_checkin_checkout(self):
		if self.type == 'IN':
			exists_checkin = frappe.db.exists('Accommodation Checkin Checkout', {
				'employee': self.employee,
				'type': 'IN',
				'checked_out': False
			})
			if exists_checkin:
				frappe.throw(_("{0} not checked out from bed <b><a href='#Form/Bed/{1}'>{1}</a></b>".format(
					self.full_name, frappe.db.get_value('Accommodation Checkin Checkout', exists_checkin, 'bed'))))

	def before_insert(self):
		if self.type == "IN":
			self.naming_series = "CHECKIN-.YYYY.-"
		elif self.type == "OUT":
			self.naming_series = "CHECKOUT-.YYYY.-"
		if self.employee_id and not self.employee:
			employee = frappe.db.exists('Employee', {'employee_id': self.employee_id})
			if employee:
				self.employee = employee

	def on_trash(self):
		exists_employee_checkin_checkout = frappe.db.exists('Accommodation Checkin Checkout', {
			'employee': self.employee,
			'type': 'IN',
			'checkin_checkout_date_time': ['>', self.checkin_checkout_date_time]
		})
		if not exists_employee_checkin_checkout:
			occupy = True if self.type == 'OUT' else False
			self.update_bed_details(occupy, True)
		self.onboard_employee_update(True)

	def on_update(self):
		occupy = True if self.type == 'IN' else False
		self.update_bed_details(occupy)


	def after_insert(self):
		self.update_checkin_reference()
		self.onboard_employee_update()

	def onboard_employee_update(self, on_trash=False):
		if self.type == 'IN':
			if on_trash:
				oe_name = frappe.db.exists('Onboard Employee', {'employee': self.employee, 'accommodation_provided': True, 'checkin_reference': self.name})
			else:
				oe_name = frappe.db.exists('Onboard Employee', {'employee': self.employee, 'accommodation_provided': False})
			if oe_name:
				oe = frappe.get_doc('Onboard Employee', oe_name)
				oe.accommodation_provided = False if on_trash else True
				oe.checkin_reference = '' if on_trash else self.name
				oe.save(ignore_permissions=True)

	def update_checkin_reference(self):
		if self.type == 'OUT' and self.checkin_reference:
			frappe.db.set_value('Accommodation Checkin Checkout', self.checkin_reference, 'checked_out', True)

	def update_bed_details(self, occupy, on_trash=False):
		bed = frappe.get_doc('Bed', self.bed)
		if ("Occupied" in bed.status and bed.employee == self.employee) or (occupy and not bed.employee):
			bed.status = 'Occupied' if occupy else 'Vacant'
			if occupy and not self.attach_print_accommodation_policy:
				bed.status = 'Occupied Temporarily'
			bed.employee = self.employee if occupy else ''
			if occupy and self.tenant_category:
				bed.passport_number =  self.passport_number
				bed.full_name = self.full_name
				bed.one_fm_nationality = self.nationality
				bed.civil_id = self.civil_id
			bed.save(ignore_permissions=True)
			if on_trash:
				self.update_checkin_reference()

	@frappe.whitelist()
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
		if self.employee:
			self.attach_print_accommodation_policy = frappe.db.get_value('Employee', self.employee, 'one_fm_accommodation_policy')
