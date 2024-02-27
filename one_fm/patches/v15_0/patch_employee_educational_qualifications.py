import frappe

def execute():
    frappe.db.sql("""
        UPDATE `tabEmployee`
        SET 
            one_fm__highest_educational_qualification="Bachelor"
        WHERE 
            one_fm__highest_educational_qualification="Graduate"
    """)

    frappe.db.sql("""
        UPDATE `tabEmployee`
        SET 
            one_fm__highest_educational_qualification="Others"
        WHERE 
            one_fm__highest_educational_qualification="Post Graduate"
    """)