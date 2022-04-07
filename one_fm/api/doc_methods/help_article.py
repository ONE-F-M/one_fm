import frappe
from frappe import _
from slugify import slugify


def validate(doc, method):
    """
        Validate data
    """
    if doc.category == doc.subcategory:
        frappe.throw(_("Category name should not be same as sub-category."))
    # check for sub category
    category = frappe.get_doc("Help Category", doc.category)
    subcategory = frappe.get_doc("Help Category", doc.subcategory)
    if (category.is_subcategory==1):
        frappe.throw(_("Subcategory cannot be selected as category."))
    if (not subcategory.is_subcategory):
        frappe.throw(_("Category cannot be selected as subcategory."))
    if subcategory.category!=category.name:
        frappe.throw(_(f"""Subcategory {subcategory.name} is not a child of {category.name}"""))

def before_insert(doc, method):
    """
        Rename route before saving in help category
    """
    # set route
    pass
    # doc.route = f"/kb/{slugify(doc.category_name, allow_unicode=True)}"
    # if (doc.is_subcategory and doc.category):
    #     doc.route += f"/{slugify(doc.category, allow_unicode=True)}"


def on_update(doc, method):
    """
        Update route before saving in help category
    """
    # set route
    pass
    # doc.route = f"/kb/{slugify(doc.category_name, allow_unicode=True)}"
    # if (doc.is_subcategory and doc.category):
    #     doc.route += f"/{slugify(doc.category, allow_unicode=True)}"
