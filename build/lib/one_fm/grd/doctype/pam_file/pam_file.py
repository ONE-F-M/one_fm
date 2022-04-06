# -*- coding: utf-8 -*-
# Copyright (c) 2019, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document

class PAMFile(Document):
	def on_update(self):
		if self.government_project == 1:
			self.db_set('pam_file_number',self.contract_pam_file_number)
		

