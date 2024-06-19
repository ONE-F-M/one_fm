import frappe
from frappe import _

def get_context(context):
    print(frappe.form_dict.id)
    customer = frappe.get_doc("Client", {"route_hash": frappe.form_dict.id})
    context.doc = customer
    context.parents = [{'route': customer.route , 'title': _(customer.customer_name) }]
