import frappe

def run():
    # Restore Finance Assignment Rule
    if not frappe.db.exists("Assignment Rule", "Arrival - Assign Finance"):
        doc = frappe.new_doc("Assignment Rule")
        doc.update({
            "name": "Arrival - Assign Finance",
            "document_type": "Arrival and Deployment",
            "assign_condition": "doc.workflow_state == 'Pending Support Departments'",
            "unassign_condition": "doc.workflow_state == 'Completed'",
            "due_date_based_on": "arrival_date",
            "assignment_days": [{"day": d} for d in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]],
            "field": "finance",
            "description": "Dear {{ finance }},\n\nKindly arrange 30 KD as Loan Amount for the arriving employees\n\nPFA: Loan Application form for Arriving employees",
            "rule": "Based on Field",
            "disabled": 0
        })
        doc.insert(ignore_permissions=True)

    # Ensure Transportation is active and correctly configured
    if frappe.db.exists("Assignment Rule", "Arrival - Assign Transportation"):
        doc = frappe.get_doc("Assignment Rule", "Arrival - Assign Transportation")
        # Keep it for Overseas only, as per previous discussion, but ensure description is correct
        doc.description = "Dear {{ transportation_manager }},\n\nKindly arrange Airport Pick Up & Accommodation Accordingly based on the flight schedules."
        doc.save(ignore_permissions=True)

    frappe.db.commit()
    print("Finance restored and descriptions updated.")
