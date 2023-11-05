import frappe

def execute():
    post_abbr = frappe.db.sql("""UPDATE `tabEmployee Schedule` es, `tabOperations Role` o
                            SET es.post_abbrv = o.post_abbrv 
                            WHERE es.reference_doctype='Shift Request'
                            AND o.name = es.operations_role""")
    frappe.db.commit()