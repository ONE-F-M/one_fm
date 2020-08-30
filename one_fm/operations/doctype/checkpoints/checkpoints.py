# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Checkpoints(Document):
	def validate(self):
		self.generate_code()

	def generate_code(self):
		if not self.checkpoint_code:
			self.checkpoint_code = frappe.generate_hash(length=30)

