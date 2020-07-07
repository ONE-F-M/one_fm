# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PAMVisa(Document):
	def validate(self):
		if self.status == 'Rejected' and self.visa_application_rejected==0:
			self.visa_application_rejected = 1

			frappe.get_doc({
				"doctype":"PAM Visa"
			}).insert(ignore_permissions=True)

