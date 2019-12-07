# -*- coding: utf-8 -*-
# Copyright (c) 2019, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PurchaseRequest(Document):
	pass


@frappe.whitelist()
def get_data(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select site from `tabProject Sites`
		where parent = %(project_parent)s
			and docstatus < 2
			and {key} like %(txt)s
		order by
			if(locate(%(_txt)s, site), locate(%(_txt)s, site), 99999),
			idx desc,
			site
		limit %(start)s, %(page_len)s""".format(**{
			'key': searchfield
		}), {
			'txt': "%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'project_parent': filters.get("project_parent")
		})
	