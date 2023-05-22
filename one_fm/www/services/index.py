import frappe

def get_context(context):
    
    services = {}
    category = frappe.get_value("HD Article Category", {'category_name':'Company Service'},["name"])
    services = frappe.get_list("HD Article", {'category': category},['name','title', 'content'])
    
    context.services = services
