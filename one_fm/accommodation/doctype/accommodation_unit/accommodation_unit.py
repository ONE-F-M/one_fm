# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AccommodationUnit(Document):
	def validate(self):
		self.set_title()

	def set_title(self):
		self.title = '-'.join([self.accommodation_name, self.type, 'Floor'+self.floor])

	def autoname(self):
		self.set_accommodation_unit_code()
		self.name = self.accommodation+str(int(self.floor)).zfill(2)+self.accommodation_unit_code

	def set_accommodation_unit_code(self):
		if not self.accommodation_unit_code:
			self.accommodation_unit_code = str(int(self.floor)).zfill(2)+get_latest_accommodation_unit_code(self)

def get_latest_accommodation_unit_code(doc):
	query = """
		select
			accommodation_unit_code+1
		from
			`tabAccommodation Unit`
		where
			accommodation='{0}' and floor='{1}'
		order by
			accommodation_unit_code desc limit 1
	"""
	accommodation_unit_code = frappe.db.sql(query.format(doc.accommodation, doc.floor))
	new_accommodation_unit_code = accommodation_unit_code[0][0] if accommodation_unit_code else 1
	return str(int(new_accommodation_unit_code)).zfill(1)
