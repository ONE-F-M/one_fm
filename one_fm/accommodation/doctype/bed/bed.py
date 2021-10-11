# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class Bed(Document):
	def validate(self):
		# self.set_title()
		self.update_bed_in_space()
		self.update_occupancy_details()

	def update_occupancy_details(self):
		if self.status == 'Occupied' and self.nationality:
			if self.nationality == 'Kuwaiti':
				self.local_or_overseas = 'Local'
			else:
				self.local_or_overseas = 'Overseas'
		if self.status == 'Vacant':
			self.employee = ''
			self.local_or_overseas = ''
			self.passport_number =  ''
			self.full_name = ''
			self.one_fm_nationality = ''
			self.one_fm_religion = ''
			self.contact_number = ''
			self.visa_number = ''
			self.email = ''

	def update_bed_in_space(self):
		bed_in_space = frappe.db.exists('Accommodation Space Bed', {'bed': self.name})
		if bed_in_space:
			query = """
				update
					`tabAccommodation Space Bed`
				set
					disabled=%(disabled)s, bed_type=%(bed_type)s, gender=%(gender)s
				where
					bed=%(bed)s and name=%(bed_in_space)s
			"""
			filters = {
				'disabled': self.disabled, 'gender': self.gender, 'status': self.status,
				'bed_type': self.bed_type, 'bed': self.name, 'bed_in_space': bed_in_space
			}
			frappe.db.sql(query, filters)

	def set_title(self):
		self.title = '-'.join([self.accommodation_name, self.type,
			'Floor'+self.floor, self.accommodation_space_type, self.bed_code])

	def before_insert(self):
		self.validate_no_of_bed()

	def after_insert(self):
		self.update_no_of_bed_in_accommodation()

	def on_trash(self):
		self.validate_bed_used()
		self.delete_bed_reference_from_space()
		self.update_no_of_bed_in_accommodation()

	def delete_bed_reference_from_space(self):
		query = """
			delete from
				`tabAccommodation Space Bed`
			where
				bed = {0}
		"""
		frappe.db.sql(query.format(self.name))

	def validate_bed_used(self):
		if frappe.db.exists('Accommodation Checkin Checkout', {'bed': self.name}):
			frappe.throw(_("Bed can not be Deleted, you can disable the Bed"))

	def update_no_of_bed_in_accommodation(self):
		frappe.db.set_value('Accommodation', self.accommodation,
			'total_no_of_bed_space' ,frappe.db.count('Bed', {'accommodation': self.accommodation}))

	def validate_no_of_bed(self):
		allowed_no = frappe.db.get_value('Bed Space Type', self.bed_space_type, 'single_bed_capacity')
		if not allowed_no:
			frappe.throw(_("No Bed Space is Configured in Accommodation Space {0}"
				.format(self.accommodation_space)))
		elif frappe.db.count('Bed', {'accommodation_space': self.accommodation_space}) >= allowed_no:
			frappe.throw(_("Only {0} Bed is allowed in Accommodation Space {1}"
				.format(allowed_no, self.accommodation_space)))

	def autoname(self):
		self.set_bed_code()
		self.name = self.accommodation_space+self.bed_code

	def set_bed_code(self):
		if not self.bed_code:
			self.bed_code = get_latest_bed_code(self)

def get_latest_bed_code(doc):
	query = """
		select
			bed_code+1
		from
			`tabBed`
		where
			accommodation='{0}' and accommodation_unit='{1}' and accommodation_space='{2}'
		order by
			bed_code desc limit 1
	"""
	bed_code = frappe.db.sql(query.format(doc.accommodation, doc.accommodation_unit, doc.accommodation_space))
	new_bed_code = bed_code[0][0] if bed_code else 1
	return str(int(new_bed_code)).zfill(1)
