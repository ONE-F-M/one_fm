import frappe

@frappe.whitelist()
def get_profile():
    return frappe.get_doc("User", frappe.session.user)

@frappe.whitelist()
def get_defaults():
        data = frappe._dict({})
        data.my_todos = frappe.db.get_list("ToDo", filters={
            'allocated_to':frappe.session.user,
            'status':'Open'
        }, fields="*", ignore_permissions=True)
        data.assigned_todos = frappe.db.get_list("ToDo", filters={
            'assigned_by':frappe.session.user,
            'status':'Open'
        }, fields="*", ignore_permissions=True)

        return data