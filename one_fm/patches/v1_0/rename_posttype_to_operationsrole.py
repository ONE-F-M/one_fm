import frappe

def execute():
    doctypes = frappe.db.get_list("DocType")
    for row in doctypes:
        try:
            post= frappe.db.sql(f"SHOW COLUMNS FROM `tab{row.name}` LIKE 'post_type';", as_dict=1)
            role = frappe.db.sql(f"SHOW COLUMNS FROM `tab{row.name}` LIKE 'operations_role';")
            if post and role:
                frappe.db.sql(f"UPDATE `tab{row.name}` SET operations_role = post_type;")
                print(post, row)
        except:
            pass
