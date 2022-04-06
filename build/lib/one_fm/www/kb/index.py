import frappe

def get_context(context):
    if frappe.session.user=='Guest':
        raise  frappe.exceptions.PermissionError('Please login to continue')

    context.help_article = frappe.db.sql("""
        SELECT name, title, category, route
        FROM `tabHelp Article`
        WHERE published=1
    """, as_dict=1)
    return context
