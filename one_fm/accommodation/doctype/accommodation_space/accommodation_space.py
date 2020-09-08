# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class AccommodationSpace(Document):
	def validate(self):
		self.set_title()
		self.update_bed_status()

	def update_bed_status(self):
		if self.bed_space_available:
			if not self.is_new():
				self.create_beds_in_space()
			if self.beds:
				for bed in self.beds:
					frappe.db.set_value('Bed', bed.bed, 'disabled', bed.disabled)

	def after_insert(self):
		self.set("beds", [])
		self.create_beds_in_space()
		self.save(ignore_permissions=True)

	def set_title(self):
		self.title = '-'.join([self.accommodation_name, self.type,
			self.floor_name+' Floor', self.accommodation_space_type, self.accommodation_space_code])

	def before_insert(self):
		self.validate_no_of_accommodation_space()

	def validate_no_of_accommodation_space(self):
		allowed_no = frappe.db.get_value('Accommodation Unit Space Type', {'parent': self.accommodation_unit,
			'space_type': self.accommodation_space_type}, 'total_number')
		if not allowed_no:
			frappe.throw(_("No {0} is Configured in Accommodation Unit {1}"
				.format(self.accommodation_space_type, self.accommodation_unit)))
		elif frappe.db.count('Accommodation Space',
			{'accommodation_unit': self.accommodation_unit,
				'accommodation_space_type': self.accommodation_space_type}) >= allowed_no:
			frappe.throw(_("Only {0} {1} is allowed in Accommodation Unit {2}"
				.format(allowed_no, self.accommodation_space_type, self.accommodation_unit)))

	def autoname(self):
		self.set_accommodation_space_code()
		self.name = self.accommodation_unit+self.accommodation_space_code

	def set_accommodation_space_code(self):
		if not self.accommodation_space_code:
			self.accommodation_space_code = self.accommodation_unit_code+get_latest_accommodation_space_code(self)

	def create_beds_in_space(self):
		if self.bed_space_available and self.bed_space_type and self.single_bed_capacity:
			beds_to_create = self.single_bed_capacity - (len(self.beds) if self.beds else 0)
			if beds_to_create > 0:
				for x in range(beds_to_create):
					bed = frappe.new_doc('Bed')
					bed.accommodation_space = self.name
					bed.disabled = False
					bed.bed_space_type = self.bed_space_type
					bed.save(ignore_permissions=True)
					bed_in_space = self.append('beds')
					bed_in_space.bed = bed.name
					bed_in_space.disabled = bed.disabled

def get_latest_accommodation_space_code(doc):
	query = """
		select
			accommodation_space_code+1
		from
			`tabAccommodation Space`
		where
			accommodation='{0}' and accommodation_unit='{1}'
		order by
			accommodation_space_code desc limit 1
	"""
	accommodation_space_code = frappe.db.sql(query.format(doc.accommodation, doc.accommodation_unit))
	new_accommodation_space_code = accommodation_space_code[0][0] if accommodation_space_code else 1
	return str(int(new_accommodation_space_code))[-1]

def filter_floor(doctype, txt, searchfield, start, page_len, filters):
	query = """
		select
			floor_name
		from
			`tabAccommodation Unit`
		where
			accommodation = %(accommodation)s and floor_name like %(txt)s
			limit %(start)s, %(page_len)s"""
	return frappe.db.sql(query,
		{
			'accommodation': filters.get("accommodation"),
			'start': start,
			'page_len': page_len,
			'txt': "%%%s%%" % txt
		}
	)
