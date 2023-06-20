import frappe
from ...api import get_categories, remove_html_tags
def get_context(context):
    context.title = frappe.form_dict.subcategory.replace('-', ' ')
    context.categories = get_categories()
    context.articles = frappe.db.sql(f"""
        SELECT name, title, route, content FROM `tabHelp Article`
        WHERE published=1 AND subcategory="{frappe.form_dict.subcategory.replace('-', ' ')}"
    """, as_dict=1)
    for i in context.articles:
        if i.content:
            i.content = remove_html_tags(i.content)[:50]
        else:
            i.content = ''
    return context
