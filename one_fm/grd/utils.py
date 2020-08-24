# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe

def todo_after_insert(doc, method):
    if doc.reference_type == 'Work Permit' and doc.reference_name and doc.owner and 'GRD Operator' in frappe.get_roles(doc.owner):
        if not frappe.db.get_value(doc.reference_type, doc.reference_name, 'grd_operator'):
            frappe.db.set_value(doc.reference_type, doc.reference_name, 'grd_operator', doc.owner)
