# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

class RecruitmentTripRequest(Document):
	def validate(self):
		self.validate_dates()
	def validate_dates(self):
		if self.from_date and self.to_date:
			if self.from_date > self.to_date:
				frappe.throw(_("To Date cannot be before From Date"))
