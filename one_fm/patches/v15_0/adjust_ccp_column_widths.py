import frappe

def execute():
    # Update grid column allocations precisely to 10 total
    # Process Name: 2
    # Planned Date: 1
    # Live Plan Date: 1
    # Actual Date: 2
    # Status: 2
    # ETA Status: 2
    updates = {
        'process_name': 2,
        'planned_date': 1,
        'live_plan_date': 1,
        'actual_date': 2,
        'status': 2,
        'eta_status': 2
    }
    
    for fieldname, cols in updates.items():
        frappe.db.sql("""
            UPDATE `tabDocField` 
            SET columns=%s 
            WHERE parent='Candidate Country Process Details' 
            AND fieldname=%s
        """, (cols, fieldname))
    
    frappe.db.commit()
