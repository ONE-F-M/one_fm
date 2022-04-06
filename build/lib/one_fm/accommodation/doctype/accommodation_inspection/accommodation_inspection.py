# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AccommodationInspection(Document):
	def get_template_details(self):
		if not self.accommodation_inspection_template: return

		self.set('readings', [])
		parameters = frappe.get_all('Accommodation Inspection Parameter', fields=["parameter"],
			filters={'parenttype': 'Accommodation Inspection Template', 'parent': self.accommodation_inspection_template},
			order_by="idx")
		for d in parameters:
			child = self.append('readings', {})
			child.parameter = d.parameter
