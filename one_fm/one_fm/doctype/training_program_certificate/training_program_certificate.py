# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe import _
import frappe
from frappe.model.document import Document
from frappe.utils import getdate

class TrainingProgramCertificate(Document):
	def autoname(self):
		self.name = self.training_program_name+"/"+self.employee

	def validate(self):
		if self.issue_date and self.expiry_date:
			if getdate(self.issue_date) >= getdate(self.expiry_date):
				frappe.throw(_("Expiry date cannot be on or before Issue date"))

		elif not self.issue_date and self.expiry_date and getdate(self.expiry_date) <= getdate():
			frappe.throw(_("Expiry date cannot be on or before today"))