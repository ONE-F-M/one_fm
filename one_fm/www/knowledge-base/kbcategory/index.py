import frappe
from ..api import get_categories, remove_html_tags
def get_context(context):
    context.title = frappe.form_dict.category.replace('-', ' ')
    context.categories = get_categories()
    context.subcategory = frappe.db.sql(f"""
        SELECT name, category_name, route, category_description FROM `tabHelp Category`
        WHERE published=1 AND category="{frappe.form_dict.category.replace('-', ' ')}"
    """, as_dict=1)
    for i in context.subcategory:
        if i.category_description:
            i.category_description = remove_html_tags(i.category_description)[:50]
        else:
            i.category_description = ''
    return context
