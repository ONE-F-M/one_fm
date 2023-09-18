import frappe

def execute():
    user_list = frappe.db.sql("""SELECT u.name as user_id, e.name as employee_id from `tabUser` u 
                left JOIN `tabEmployee` e on u.name=e.user_id
                WHERE e.status in ('Active','Vacation')
                AND e.user_id LIKE '%armor-services.com%'""", as_dict=1)
    
    rename_user(user_list)
    frappe.db.commit()

def rename_user(user_list):
    for user in user_list:
        old_user_id = str(user.user_id)
        new_user_id = old_user_id.split('@')[0] + "@one-fm.com"
        print(old_user_id, new_user_id)
        if not frappe.db.exists("User", {'name':new_user_id}):
            frappe.rename_doc("User", old_user_id, new_user_id, merge=False, force=1)
        else:
            frappe.db.set_value("Employee", user.employee_id, 'user_id', new_user_id)

