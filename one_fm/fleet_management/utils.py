# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
from frappe import _
import frappe

@frappe.whitelist(allow_guest=True)
def vehicle_naming_series(doc, method):
    name = 'VHL-'
    count = frappe.db.count('Vehicle')
    if not count or count <= 0:
        count = 1
    else:
        count += 1
    doc.name = name+str(int(count)).zfill(4)
