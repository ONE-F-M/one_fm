import frappe

def get_context(context):
    context.wikis = frappe.db.sql(f"""
        SELECT * FROM `tabWiki Page`;
        """, as_dict=1)
    context.cur_user = frappe.get_value("User",frappe.session.user,'first_name')

    return context
    
