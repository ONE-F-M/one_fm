import frappe

@frappe.whitelist()
def get_call(allow_guest=True):
    return "Hello"
# def get_call(status,priority,description,allocate_to):
#     todo = frappe.new_doc("ToDo")
#     todo.description = description
#     todo.status = status
#     todo.priority = priority
#     todo.save()

#     return todo