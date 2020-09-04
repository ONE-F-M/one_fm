# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Bed(Document):
	def validate(self):
		self.set_title()

	def set_title(self):
		self.title = '-'.join([self.accommodation_name, self.type,
			'Floor'+self.floor, self.accommodation_space_type, self.bed_code])

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
