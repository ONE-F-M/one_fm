# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc
from frappe.utils import cstr, getdate, add_to_date
import pandas as pd
from frappe.desk.reportview import build_match_conditions, get_filters_cond

class OperationsRole(Document):
	def after_insert(self):
		post_abbrv = self.post_abbrv
		if frappe.db.exists("Contracts", {'project': self.project}):
			start_date, end_date = frappe.db.get_value("Contracts", {'project': self.project}, ["start_date", "end_date"])
			if start_date and end_date:
				frappe.enqueue(set_post_active, post=self, operations_role=self.name, post_abbrv=post_abbrv, shift=self.shift, site=self.site, project=self.project, start_date=start_date, end_date=end_date, is_async=True, queue="long")

	def validate(self):
		if not self.post_name:
			frappe.throw("Post Name cannot be empty.")

		if not self.shift:
			frappe.throw("Shift cannot be empty.")


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

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_operations_role_list(doctype, txt, searchfield, start, page_len, filters=None):
	from erpnext.controllers.queries import get_fields

	fields = ["name"]

	fields = get_fields("Operations Role", fields)

	match_conditions = build_match_conditions("Operations Role")
	match_conditions = "and {}".format(match_conditions) if match_conditions else ""

	if filters:
		filter_exist = False
		for filter in filters:
			if filters[filter]:
				filter_exist = True
		if filter_exist:
			filter_conditions = get_filters_cond(doctype, filters, [])
			match_conditions += "{}".format(filter_conditions)

	return frappe.db.sql(
		"""
		select %s
		from `tabOperations Role`
		where docstatus < 2
			and is_active = 1
			and (%s like %s or post_name like %s)
			{match_conditions}
		order by
			case when name like %s then 0 else 1 end,
			case when post_name like %s then 0 else 1 end,
			name, post_name limit %s, %s
		""".format(
			match_conditions=match_conditions
		)
		% (", ".join(fields), searchfield, "%s", "%s", "%s", "%s", "%s", "%s"),
		("%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, start, page_len),
	)
