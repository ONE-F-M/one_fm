# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class DesignationUniformProfile(Document):
	def autoname(self):
		name = ""
		if self.project:
			name = self.project+"-"
		self.name = name+self.designation
