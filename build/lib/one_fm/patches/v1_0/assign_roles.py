from __future__ import unicode_literals
import frappe

def execute():
    frappe.enqueue(assign, queue='long')
        
def assign():
    users = frappe.get_all("User", {"user_type":"System User"})
    for user in users:
        user_roles = frappe.get_roles(user.name)
        User = frappe.get_doc("User", {"name":user.name})
        User.add_roles("Penalty Recipient")
        if "Site Supervisor" in user_roles or "Shift Supervisor" in user_roles or "Project Manager" in user_roles:
            User.add_roles("Penalty Issuer")
        User.save(ignore_permissions=True)
        frappe.db.commit()