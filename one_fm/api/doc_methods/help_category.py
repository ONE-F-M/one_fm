import frappe
from frappe import _
from slugify import slugify


def validate(doc, method):
    """
        Validate data
    """
    if doc.category_name == doc.category:
        frappe.throw(_("Category name should not be same as sub-category."))
    # check for sub category
    if (doc.category and frappe.get_doc("Help Category", doc.category).is_subcategory):
        frappe.throw(_("Subcategory cannot be selected as category."))

def before_insert(doc, method):
    """
        Rename route before saving in help category
    """
    # set route
    if (doc.is_subcategory and doc.category):
        doc.route = f"/knowledge-base/{slugify(doc.category, allow_unicode=True)}/{slugify(doc.category_name, allow_unicode=True)}"
    else:
        doc.route = f"/knowledge-base/{slugify(doc.category_name, allow_unicode=True)}"
