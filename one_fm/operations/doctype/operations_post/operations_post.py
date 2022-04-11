# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc
from frappe.utils import cstr, getdate, add_to_date
import pandas as pd

class OperationsPost(Document):
	def after_insert(self):
		post_abbrv = frappe.db.get_value("Post Type", self.post_template, ["post_abbrv"])
		if frappe.db.exists("Contracts", {'project': self.project}):
			start_date, end_date = frappe.db.get_value("Contracts", {'project': self.project}, ["start_date", "end_date"])
			if start_date and end_date:
				frappe.enqueue(set_post_active, post=self, post_type=self.post_template, post_abbrv=post_abbrv, shift=self.site_shift, site=self.site, project=self.project, start_date=start_date, end_date=end_date, is_async=True, queue="long")
	
	def validate(self):
		if not self.post_name:
			frappe.throw("Post Name cannot be empty.")

		if not self.gender:
			frappe.throw("Gender cannot be empty.")

		if not self.site_shift:
			frappe.throw("Shift cannot be empty.")

	def on_update(self):
		self.validate_name()

	def validate_name(self):
		condition = self.post_name+"-"+self.gender+"|"+self.site_shift
		if condition != self.name:
			rename_doc(self.doctype, self.name, condition, force=True)
		

@frappe.whitelist()
def set_post_active(post, post_type, post_abbrv, shift, site, project, start_date, end_date):
	for date in	pd.date_range(start=start_date, end=end_date):
		sch = frappe.new_doc("Post Schedule")
		sch.post = post.name
		sch.post_type = post_type
		sch.post_abbrv = post_abbrv
		sch.shift = shift
		sch.site = site
		sch.project = project
		sch.date = cstr(date.date())
		sch.post_status = "Planned"
		sch.save()