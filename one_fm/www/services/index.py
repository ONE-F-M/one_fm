import frappe
import re

def get_context(context):
    services = []
    category = frappe.get_value("HD Article Category", {'category_name':'Company Service'},["name"])
    service = frappe.get_list("HD Article", {'category': category},['name','title', 'content'])
    for s in service:
        services.append({
            'title':s.title,
            'content': ((remove_html_tags(s.content)[0:250] + "...") if s.content else ""),
        })

    context.services = services

def remove_html_tags(text):
    """Remove html tags from a string"""
    clean = re.compile('<.*?>')
    filtered = re.sub(clean, ' ', text)
    return re.sub(' +', ' ', filtered)