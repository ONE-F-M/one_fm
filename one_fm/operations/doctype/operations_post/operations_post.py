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
		start_date = None
		end_date = None
		project = frappe.get_doc("Project", self.project)
		contract = frappe.get_doc("Contracts", project.contract)
		if contract and contract.start_date and contract.end_date:
			start_date = contract.start_date
			end_date = contract.end_date
		else:
			start_date = project.expected_start_date
			end_date = project.expected_end_date
		frappe.enqueue(set_post_active, post=self, start_date=start_date, end_date=end_date, is_async=True, queue="long")

	def on_update(self):
		self.validate_name()

	def validate_name(self):
		condition = self.post_name+"-"+self.gender+"|"+self.site_shift
		if condition != self.name:
			rename_doc(self.doctype, self.name, condition, force=True)
		

@frappe.whitelist()
def set_post_active(post, start_date, end_date):
	for date in	pd.date_range(start=start_date, end=end_date):
		sch = frappe.new_doc("Post Schedule")
		sch.post = post.name
		sch.date = cstr(date.date())
		sch.post_status = "Planned"
		sch.save()