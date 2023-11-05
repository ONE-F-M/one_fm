# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class PenaltyList(Document):
	def validate(self):
		if not self.docstatus == 0:
			self.validate_active()
			self.validate_overlap()

	def validate_active(self):		
		if self.active and frappe.db.exists("Penalty List", {"active": 1}):
			frappe.throw(_("There can only be 1 active Penalty List."))

	def validate_overlap(self):
		filters = {
			'start_date': ('between', [self.start_date, self.end_date]),
			'end_date': ('between', [self.start_date, self.end_date]),
		}
		overlap = frappe.db.get_list('Penalty List', filters=filters)
		if len(overlap) > 0:
			frappe.throw(_("Dates overlap with an existing Penalty List."))
		