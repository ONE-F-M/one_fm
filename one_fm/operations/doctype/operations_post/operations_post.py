# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import datetime
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc
from frappe.utils import cstr, getdate, add_to_date, date_diff
import pandas as pd

class OperationsPost(Document):
	def after_insert(self):
		post_abbrv = frappe.db.get_value("Operations Role", self.post_template, ["post_abbrv"])
		if frappe.db.exists("Contracts", {'project': self.project}):
			start_date, end_date = frappe.db.get_value("Contracts", {'project': self.project}, ["start_date", "end_date"])
			if start_date and end_date:
				frappe.enqueue(set_post_active, post=self, operations_role=self.post_template, post_abbrv=post_abbrv, shift=self.site_shift, site=self.site, project=self.project, start_date=start_date, end_date=end_date, is_async=True, queue="long")

	def validate(self):
		if not self.post_name:
			frappe.throw("Post Name cannot be empty.")

		if not self.gender:
			frappe.throw("Gender cannot be empty.")

		if not self.site_shift:
			frappe.throw("Shift cannot be empty.")

		if(frappe.db.get_value('Operations Role', self.post_template, 'shift') != self.site_shift):
			frappe.throw(f"Operations Role ({self.post_template}) does not belong to selected shift ({self.site_shift})")

	def on_update(self):
		self.validate_name()

	def validate_name(self):
		condition = self.post_name+"-"+self.gender+"|"+self.site_shift
		if condition != self.name:
			rename_doc(self.doctype, self.name, condition, force=True)

	def on_update(self):
		if self.status == "Active":
			check_list = frappe.db.get_list("Post Schedule", filters={"post":self.name, "date": [">", getdate()]})
			if len(check_list) < 1 :
				frappe.enqueue(set_post_schedule, doc=self, is_async=True, queue="long")

		elif self.status == "Inactive":
			frappe.enqueue(delete_schedule, doc=self, is_async=True, queue="long")

def set_post_schedule(doc):
	project = frappe.get_doc("Project", doc.project)
	today = getdate()
	if not project.expected_end_date:
		end_date = add_to_date(today, days=365)
	else:
		end_date = project.expected_end_date

	if end_date > today:
		duration = date_diff(getdate(end_date), getdate())
		if duration > 10:
			frappe.enqueue(set_post_schedule_by_date(end_date=end_date, post_name=doc.name), is_async=True, queue="long")
		else:
			set_post_schedule_by_date(end_date=end_date, post_name=doc.name)

def set_post_schedule_by_date(end_date, post_name):
	for date in pd.date_range(start=getdate(), end=end_date):
				check_doc = frappe.get_doc({
				"doctype": "Post Schedule",
				"date": cstr(date.date()),
				"post": post_name,
				"post_status": "Planned"
					})
				check_doc.save()
	frappe.db.commit()

def delete_schedule(doc):
    check_list = frappe.db.get_list("Post Schedule", filters={"post": doc.name, "date": [">", getdate()]})
    for schedule in check_list:
        frappe.get_doc("Post Schedule", schedule.name).delete()
    frappe.db.commit()



@frappe.whitelist()
def set_post_active(post, operations_role, post_abbrv, shift, site, project, start_date, end_date):
	for date in	pd.date_range(start=start_date, end=end_date):
		sch = frappe.new_doc("Post Schedule")
		sch.post = post.name
		sch.operations_role = operations_role
		sch.post_abbrv = post_abbrv
		sch.shift = shift
		sch.site = site
		sch.project = project
		sch.date = cstr(date.date())
		sch.post_status = "Planned"
		sch.save()
