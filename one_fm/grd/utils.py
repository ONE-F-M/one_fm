# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

def todo_after_insert(doc, method):
    doctypes = ['Work Permit', 'Medical Insurance']
    if doc.reference_type in doctypes and doc.reference_name and doc.owner and 'GRD Operator' in frappe.get_roles(doc.owner):
        if not frappe.db.get_value(doc.reference_type, doc.reference_name, 'grd_operator'):
            frappe.db.set_value(doc.reference_type, doc.reference_name, 'grd_operator', doc.owner)


