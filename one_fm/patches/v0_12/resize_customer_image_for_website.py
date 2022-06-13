from __future__ import unicode_literals
import frappe
from one_fm.tasks.erpnext.customer import on_update

def execute():
    print('Preparing Customer List')
    frappe.reload_doctype('Customer')
    print('Resizing images for website')
    try:
        customers = frappe.db.sql("SELECT name FROM `tabCustomer` WHERE image IS NOT NULL", as_dict=1)
        for row in customers:
            on_update(doc=frappe.get_doc("Customer", row.name))
    except Exception as e:
        print(e)
    print('Done')
