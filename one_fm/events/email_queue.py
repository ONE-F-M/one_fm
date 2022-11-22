import frappe
from frappe.email.doctype.email_queue.email_queue import send_now
def after_insert(doc, event):
    found = False
    for row in doc.recipients:
        if row.recipient.startswith('2'):
            frappe.db.sql("""
                DELETE FROM `tabEmail Queue` 
                WHERE name IN (SELECT e.name FROM `tabEmail Queue` e JOIN `tabEmail Queue Recipient` r 
                ON r.parent=e.name WHERE r.recipient LIKE '2%');
            """)
            found = True
            break
    if found:
        send_now(name=doc.name)
