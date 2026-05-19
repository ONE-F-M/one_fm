import frappe

def run():
    # Delete Finance assignment rule because it is no longer used
    if frappe.db.exists("Assignment Rule", "Arrival - Assign Finance"):
        frappe.delete_doc("Assignment Rule", "Arrival - Assign Finance")
        
    # Make Transportation assignment only for Overseas
    if frappe.db.exists("Assignment Rule", "Arrival - Assign Transportation"):
        doc = frappe.get_doc("Assignment Rule", "Arrival - Assign Transportation")
        doc.assign_condition = "doc.workflow_state == 'Pending Support Departments' and doc.candidate_country_process"
        doc.save(ignore_permissions=True)

    # Make General Services and Warehouse assignment for Local ONLY
    # Actually wait... General Services and Warehouse MUST acknowledge for Overseas too?
    # No, wait, if we only assign them for Local, then who acknowledges for Overseas?
    # If the user says: "in aknowldgement also remove transportation and finance. so it will ve only general services, and warehouse."
    # The user wanted ONLY General Services and Warehouse for ALL hires originally!
    # BUT wait, the user's latest prompt: "gs and transportation manager are the ones that can say joined or did not arrive whethe. transportation for overseas and General services for local right?"
    # It implies GS is for Local, Transportation is for Overseas.
    
    # Wait, what about Warehouse? Warehouse gives them uniforms. They should get assigned for BOTH Local and Overseas?
    # Yes, Warehouse is universally required because everyone gets a uniform!
    
    if frappe.db.exists("Assignment Rule", "Arrival - Assign General Services"):
        doc = frappe.get_doc("Assignment Rule", "Arrival - Assign General Services")
        # Let's keep GS for both, because they need orientation. OR if the user means ONLY Local, then:
        # doc.assign_condition = "doc.workflow_state == 'Pending Support Departments' and not doc.candidate_country_process"
        # Wait, the user said: "General services for local right?"
        # I'll let GS be assigned for Local, and maybe they just don't have an assignment for Overseas?
        # Actually, let's keep the assignment rule as is for Warehouse, and for GS make it only for Local.
        doc.assign_condition = "doc.workflow_state == 'Pending Support Departments' and not doc.candidate_country_process"
        doc.save(ignore_permissions=True)

    frappe.db.commit()
    print("Assignment rules updated.")
