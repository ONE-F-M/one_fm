import frappe

def execute():
    # Make sure Warehouse role exists
    if not frappe.db.exists("Role", "Warehouse"):
        frappe.get_doc({"doctype": "Role", "role_name": "Warehouse"}).insert(ignore_permissions=True)

    # Update Workflow to include Warehouse
    wf = frappe.get_doc("Workflow", "Arrival and Deployment Workflow")
    # Add Warehouse to transitions
    existing_transitions = [t.allowed for t in wf.transitions if t.action == "Complete Deployment"]
    if "Warehouse" not in existing_transitions:
        wf.append("transitions", {
            "state": "Pending Support Departments",
            "action": "Complete Deployment",
            "next_state": "Completed",
            "allowed": "Warehouse"
        })
        wf.save(ignore_permissions=True)

    # Assignment Rules
    rules = [
        {
            "name": "Arrival - Assign Transportation",
            "doctype": "Assignment Rule",
            "document_type": "Arrival and Deployment",
            "assign_condition": "doc.workflow_state == 'Pending Support Departments'",
            "unassign_condition": "doc.workflow_state == 'Completed'",
            "due_date_based_on": "arrival_date",
            "assignment_days": [{"day": d} for d in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]],
            "field": "transportation_manager",
            "description": "Kindly arrange Airport Pick Up & Accommodation Accordingly based on the flight schedules."
        },
        {
            "name": "Arrival - Assign General Services",
            "doctype": "Assignment Rule",
            "document_type": "Arrival and Deployment",
            "assign_condition": "doc.workflow_state == 'Pending Support Departments'",
            "unassign_condition": "doc.workflow_state == 'Completed'",
            "due_date_based_on": "arrival_date",
            "assignment_days": [{"day": d} for d in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]],
            "field": "general_services",
            "description": "Dear {{ doc.general_services }},\n\nKindly confirm the date and time for GS Orientation."
        },
        {
            "name": "Arrival - Assign Finance",
            "doctype": "Assignment Rule",
            "document_type": "Arrival and Deployment",
            "assign_condition": "doc.workflow_state == 'Pending Support Departments'",
            "unassign_condition": "doc.workflow_state == 'Completed'",
            "due_date_based_on": "arrival_date",
            "assignment_days": [{"day": d} for d in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]],
            "field": "finance",
            "description": "Dear {{ doc.finance }},\n\nKindly arrange 30 KD as Loan Amount for the arriving employees\n\nPFA: Loan Application form for Arriving employees"
        },
        {
            "name": "Arrival - Assign Warehouse",
            "doctype": "Assignment Rule",
            "document_type": "Arrival and Deployment",
            "assign_condition": "doc.workflow_state == 'Pending Support Departments'",
            "unassign_condition": "doc.workflow_state == 'Completed'",
            "due_date_based_on": "arrival_date",
            "assignment_days": [{"day": d} for d in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]],
            "field": "warehouse",
            "description": "Dear {{ doc.warehouse }},\n\nKindly arrange their Uniforms and welcome kit accordingly."
        }
    ]

    for r in rules:
        if frappe.db.exists("Assignment Rule", r["name"]):
            frappe.delete_doc("Assignment Rule", r["name"], ignore_permissions=True)
            
        doc = frappe.new_doc("Assignment Rule")
        doc.update(r)
        doc.rule = "Based on Field"
        doc.disabled = 0
        doc.insert(ignore_permissions=True)

