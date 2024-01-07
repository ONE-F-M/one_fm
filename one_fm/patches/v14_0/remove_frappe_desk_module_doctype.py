from __future__ import unicode_literals

import frappe

def execute():
    module = frappe.db.exists("Module Def", {"module_name": "FrappeDesk"})
    if module:
        print("Deleting the doctypes from module {0} \n DocTypes:".format(module))
        doctypes = frappe.db.get_all("DocType", {"module": module})
        for doc in doctypes:
            print(doc.name)
            frappe.delete_doc("DocType", doc.name)
            frappe.db.commit()
        frappe.delete_doc("Module Def", module)
        frappe.db.commit()
