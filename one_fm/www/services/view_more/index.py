import frappe

def get_context(context):
    no_cache = 1
    title = frappe.form_dict.title
    service = {}

    content = frappe.get_doc("HD Article", {'title': title})

    if content:
        service.update({'title': content.title})
        service.update({'content': content.content})
   
    context.service = service
