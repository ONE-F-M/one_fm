# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class HeadHunt(Document):
	def on_submit(self):
		self.make_applicant_lead()

	def make_applicant_lead(self):
		for item in self.items:
			_make_applicant_lead(self, item)

def _make_applicant_lead(doc, item):
	lead = frappe.new_doc('Applicant Lead')
	lead.applicant_name = item.applicant_name
	lead.email_id = item.email_id
	lead.gender = item.gender
	lead.nationality = item.nationality
	lead.mobile_no = item.mobile_no
	lead.sugested_position = item.sugested_position
	lead.lead_owner_type = doc.lead_owner_type
	lead.lead_owner_dt = doc.lead_owner_dt
	lead.lead_owner = doc.lead_owner
	lead.save(ignore_permissions=True)
