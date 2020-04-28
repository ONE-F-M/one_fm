# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class OperationsProject(Document):
	pass


def get_timeline_data(doctype, name):
	'''Return timeline for attendance'''
	return dict(frappe.db.sql('''select unix_timestamp(from_time), count(*)
		from `tabTimesheet Detail` where project=%s
			and from_time > date_sub(curdate(), interval 1 year)
			and docstatus < 2
			group by date(from_time)''', name))
