from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.wiki_page import get_wiki_page_custom_fields

def execute():
    create_custom_fields(get_wiki_page_custom_fields())