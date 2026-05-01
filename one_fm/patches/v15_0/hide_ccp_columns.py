import frappe

def execute():
    # Force update Candidate Country Process Details to hide these columns from list view
    frappe.db.sql("""
        UPDATE `tabDocField` 
        SET in_list_view=0 
        WHERE parent='Candidate Country Process Details' 
        AND fieldname IN ('sequence_type', 'before_task', 'after_task')
    """)
    frappe.db.commit()
