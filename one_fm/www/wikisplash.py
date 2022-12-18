import frappe
from frappe import _

def get_context(context):
    context.wikis = frappe.db.sql(f"""
        SELECT * FROM `tabWiki Page`;
        """, as_dict=1)
    context.cur_user = frappe.get_value("User",frappe.session.user,'first_name') or "Guest"
    context.title = "Wikisplash"
    context.opening_quote = _('Would you like to view the wiki page in English?')

    return context
    
