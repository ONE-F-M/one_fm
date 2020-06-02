# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class GPLetter(Document):
	pass


# @frappe.whitelist()
# def get_suppliers(doctype, txt, searchfield, start, page_len, filters):
#     return frappe.db.sql("""select parent from `tabSupplier Group Table`
#         where parenttype='Supplier' and parentfield='supplier_group_table' and group=%(supplier_group)s and subgroup=%(supplier_subgroup)s
#             and ({key} like %(txt)s
#                 or parent like %(txt)s)
#         order by
#             if(locate(%(_txt)s, parent), locate(%(_txt)s, parent), 99999),
#             idx desc,
#             parent
#         limit %(start)s, %(page_len)s""".format(**{
#             'key': searchfield
#         }), {
#             'txt': "%s%%" % txt,
#             '_txt': txt.replace("%", ""),
#             'start': start,
#             'page_len': page_len,
#             'supplier_group': filters.get('supplier_group'),
#             'supplier_subgroup': filters.get('supplier_subgroup')
#         })

