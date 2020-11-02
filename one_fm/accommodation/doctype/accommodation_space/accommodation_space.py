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
		self.validate_space_type()
		self.update_bed_status()

	def validate_space_type(self):
		bed_space_type = frappe.db.get_value('Accommodation Space', self.name, 'bed_space_type')
		if bed_space_type != self.bed_space_type:
			# if frappe.db.count('Bed', {'status': 'Occupied', 'disabled': False, 'accommodation_space': self.name}) > 0:
			# 	frappe.throw(_("There are Occupied Bed in this Space. To change Bed Space Type, Please make all Bed Vacant"))
			# elif frappe.db.count('Bed', {'status': 'Booked', 'disabled': False, 'accommodation_space': self.name}) > 0:
			# 	frappe.throw(_("There are Booked Bed in this Space. To change Bed Space Type, Please make all Bed Vacant"))
			# elif frappe.db.count('Bed', {'status': 'Temporarily Booked', 'disabled': False, 'accommodation_space': self.name}) > 0:
			# 	frappe.throw(_("There are Temporarily Booked Bed in this Space. To change Bed Space Type, Please make all Bed Vacant"))
			# else:
			# 	self.disable_rest_of_beds()
			self.disable_rest_of_beds()

	def disable_rest_of_beds(self):
		bed_space_capacity = frappe.db.get_value('Accommodation Space', self.name, 'single_bed_capacity')
		if self.single_bed_capacity < bed_space_capacity:
			no_beds_to_disable = bed_space_capacity - self.single_bed_capacity
			disabled_beds = frappe.db.count('Bed', {'disabled': True, 'accommodation_space': self.name})
			fraction = no_beds_to_disable - disabled_beds
			if fraction > 0:
				beds_to_disable = sorted(self.beds,
					key=lambda k: k.disabled == 1)
				i = 0
				for bed in beds_to_disable:
					if i < fraction and bed.status == 'Vacant':
						i += 1
						bed.disabled = True
					elif i >= fraction:
						break

	def update_bed_status(self):
		if self.bed_space_available:
			if not self.is_new():
				self.create_beds_in_space()
			if self.beds:
				for bed in self.beds:
					if self.bed_type and not bed.bed_type:
						bed.bed_type = self.bed_type
					if self.gender and not bed.gender:
						bed.gender = self.gender
					query = """
						update
							tabBed
						set
							disabled=%(disabled)s, bed_type=%(bed_type)s, gender=%(gender)s
						where
							name=%(bed)s
					"""
					filters = {'disabled': bed.disabled, 'gender': bed.gender, 'bed_type': bed.bed_type, 'bed': bed.bed}
					frappe.db.sql(query, filters)

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
					bed.bed_type = self.bed_type
					bed.gender = self.gender
					bed.save(ignore_permissions=True)
					bed_in_space = self.append('beds')
					bed_in_space.bed = bed.name
					bed_in_space.disabled = bed.disabled
					bed_in_space.bed_type = bed.bed_type
					bed_in_space.gender = bed.gender

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

def change_room_type():
	space_details = [
		{"D":"1010110111"},
		{"D":"1010110112"},
		{"D":"1010110113"},
		{"D":"1010120121"},
		{"D":"1010120122"},
		{"D":"1010120123"},
		{"D":"1020210211"},
		{"D":"1020210212"},
		{"D":"1020210213"},
		{"D":"1020230231"},
		{"B":"1030310311"},
		{"D":"1030310313"},
		{"D":"1030320321"},
		{"D":"1030320322"},
		{"D":"1030320323"},
		{"D":"1030330331"},
		{"D":"1030330332"},
		{"D":"1030330333"},
		{"D":"1040410411"},
		{"D":"1040410412"},
		{"C":"1040410413"},
		{"D":"1040420421"},
		{"D":"1040420422"},
		{"D":"1040420423"},
		{"D":"1040430431"},
		{"D":"1040430432"},
		{"D":"1040430433"},
		{"D":"1050510511"},
		{"D":"1050510512"},
		{"D":"1050510513"},
		{"D":"1050520521"},
		{"D":"1050520522"},
		{"D":"1050520523"},
		{"D":"1050530531"},
		{"D":"1050530532"},
		{"D":"1050530533"},
		{"C":"1060610611"},
		{"C":"1060610612"},
		{"C":"1060610613"},
		{"D":"1060620621"},
		{"D":"1060620622"},
		{"D":"1060620623"},
		{"D":"1060630631"},
		{"D":"1060630632"},
		{"D":"1060630633"},
		{"D":"1070710711"},
		{"D":"1070710712"},
		{"D":"1070710716"},
		{"D":"1070720721"},
		{"D":"1101021021"},
		{"D":"1070730731"},
		{"D":"1070730732"},
		{"D":"1070730733"},
		{"D":"1080820821"},
		{"D":"1080830831"},
		{"D":"1090930931"},
		{"D":"1101031031"}
	]
	for space in space_details:
		for key in space:
			accommodation_space = frappe.get_doc('Accommodation Space', space[key])
			accommodation_space.bed_space_type = key
			accommodation_space.save(ignore_permissions=True)
