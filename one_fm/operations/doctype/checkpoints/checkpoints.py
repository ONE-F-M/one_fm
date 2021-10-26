# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
import hashlib

class Checkpoints(Document):
	def validate(self):
		self.generate_code()

	def generate_code(self):
		if not self.checkpoint_code:
			# Generate a MD5 hash of the checkpoint name, project and site to maintain uniqueness of the checkpoint code.
			checkpoint_code = hashlib.md5((self.checkpoint_name + self.project_name + self.site_name).encode('utf-8')).hexdigest()
			
			# Set checkpoint code 
			if not frappe.db.exists("Checkpoints", {'checkpoint_code': checkpoint_code}):
				self.checkpoint_code = checkpoint_code
			else:
				frappe.throw(_("Checkpoint with the same checkpoint code already exists. Suggestion to use a different checkpoint name."))

