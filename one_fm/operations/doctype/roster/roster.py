# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr
class Roster(Document):
	def before_insert(self):
		if frappe.db.exists("Roster", {"employee": self.employee, "date": self.date}):
			frappe.throw(_("Roster already scheduled for {employee} on {date}.".format(employee=self.employee_name, date=cstr(self.date))))


@frappe.whitelist()
def get_post_types(doctype, txt, searchfield, start, page_len, filters):
	shift = filters.get('shift')
	post_types = frappe.db.sql("""
		SELECT DISTINCT post_template
		FROM `tabOperations Post`
		WHERE site_shift="{shift}"
	""".format(shift=shift))
	print(post_types)
	return post_types