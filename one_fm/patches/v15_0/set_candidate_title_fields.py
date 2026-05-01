import frappe

def execute():
    doctypes = [
        "Candidate Country Process", 
        "Overseas Medical Appointment WAFID", 
        "Overseas Remedical", 
        "PCC Clearance", 
        "Visa Stamping", 
        "Arrival and Deployment"
    ]
    
    for dt in doctypes:
        if frappe.db.exists("DocType", dt):
            doc = frappe.get_doc("DocType", dt)
            # Use db.set_value to avoid writing JSON files to disk during production migrations
            frappe.db.set_value("DocType", dt, {
            "title_field": "candidate_name" if not doc.title_field else doc.title_field,
            "search_fields": "candidate_name,passport_number",
            "show_title_field_in_link": 1
        })
            frappe.clear_cache(doctype=dt)
            print(f"Updated DB schema for {dt}: title_field=candidate_name, search_fields=candidate_name,passport_number")
    
    frappe.db.commit()
