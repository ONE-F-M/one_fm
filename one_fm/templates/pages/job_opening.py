from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document


def get_context(context):
    context.show_search = True


@frappe.whitelist(allow_guest=True)
def get_gender():
    doc = frappe.get_doc('Gender')
    doc.title = 'Gender'
    doc.save()
    return doc
