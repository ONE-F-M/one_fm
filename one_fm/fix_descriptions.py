import frappe

def run():
    # Fix Assignment Rule Descriptions
    rules_to_fix = [
        ("Arrival - Assign General Services", "Dear {{ general_services }},\n\nKindly confirm the date and time for GS Orientation."),
        ("Arrival - Assign Warehouse", "Dear {{ warehouse }},\n\nKindly arrange their Uniforms and welcome kit accordingly."),
        ("Arrival - Recruiter Not Arrived", "Dear {{ recruiter }},\n\nThe candidate {{ candidate_name }} did not arrive as scheduled. Please investigate and take appropriate action.")
    ]

    for rule_name, description in rules_to_fix:
        if frappe.db.exists("Assignment Rule", rule_name):
            doc = frappe.get_doc("Assignment Rule", rule_name)
            doc.description = description
            doc.save(ignore_permissions=True)

    frappe.db.commit()
    print("Assignment Rule Descriptions fixed.")
