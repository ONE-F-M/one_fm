import frappe

def copy_details():
    acp1 = frappe.get_doc("Agency Country Process", "ACP001")
    acp2 = frappe.get_doc("Agency Country Process", "ACP002")
    
    # Clear existing details
    acp2.set("agency_process_details", [])
    
    # Copy details
    for row in acp1.get("agency_process_details"):
        new_row = frappe.copy_doc(row)
        new_row.name = None # Clear name to create new
        new_row.parent = acp2.name
        acp2.append("agency_process_details", new_row)
        
    acp2.save(ignore_permissions=True)
    frappe.db.commit()
    print(f"Successfully copied {len(acp1.get('agency_process_details'))} rows from ACP001 to ACP002")
