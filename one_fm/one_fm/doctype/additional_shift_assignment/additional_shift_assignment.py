# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document

class AdditionalShiftAssignment(Document):
	def autoname(self):
		self.name = self.employee+"|"+self.shift
