import frappe

def run():
    doc = frappe.get_doc("DocType", "Arrival and Deployment")
    
    fields_to_remove = [
        "arrival_time", 
        "transportation_manager", 
        "finance", 
        "section_break_flight", 
        "flight_number", 
        "airline", 
        "ticket_attachment", 
        "arrival_airport", 
        "transport_acknowledged", 
        "finance_acknowledged"
    ]
    
    # Remove fields
    doc.fields = [df for df in doc.fields if df.fieldname not in fields_to_remove]
    
    # Update pickup_contact
    for df in doc.fields:
        if df.fieldname == "pickup_contact":
            df.fieldtype = "Link"
            df.options = "Employee"
            df.label = "Pickup Person"
    
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    print("Arrival and Deployment schema updated.")
