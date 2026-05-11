import frappe

def execute():
    notifications = [
        {
            "name": "Arrival - Transportation Reminder",
            "subject": "Reminder: Acknowledge Arrival for {{ doc.candidate_name }}",
            "condition": "doc.workflow_state == 'Pending Support Departments' and doc.transport_acknowledged == 0",
            "field": "transportation_manager",
            "message": "<p>Dear {{ doc.transportation_manager }},</p><p>This is a reminder to acknowledge the Arrival and Deployment for <b>{{ doc.candidate_name }}</b>.</p><p><a href='/app/arrival-and-deployment/{{ doc.name }}'>Click here to view</a></p>"
        },
        {
            "name": "Arrival - Finance Reminder",
            "subject": "Reminder: Acknowledge Arrival for {{ doc.candidate_name }}",
            "condition": "doc.workflow_state == 'Pending Support Departments' and doc.finance_acknowledged == 0",
            "field": "finance",
            "message": "<p>Dear {{ doc.finance }},</p><p>This is a reminder to acknowledge the Arrival and Deployment for <b>{{ doc.candidate_name }}</b>.</p><p><a href='/app/arrival-and-deployment/{{ doc.name }}'>Click here to view</a></p>"
        },
        {
            "name": "Arrival - General Services Reminder",
            "subject": "Reminder: Acknowledge Arrival for {{ doc.candidate_name }}",
            "condition": "doc.workflow_state == 'Pending Support Departments' and doc.general_services_acknowledged == 0",
            "field": "general_services",
            "message": "<p>Dear {{ doc.general_services }},</p><p>This is a reminder to acknowledge the Arrival and Deployment for <b>{{ doc.candidate_name }}</b>.</p><p><a href='/app/arrival-and-deployment/{{ doc.name }}'>Click here to view</a></p>"
        },
        {
            "name": "Arrival - Warehouse Reminder",
            "subject": "Reminder: Acknowledge Arrival for {{ doc.candidate_name }}",
            "condition": "doc.workflow_state == 'Pending Support Departments' and doc.warehouse_acknowledged == 0",
            "field": "warehouse",
            "message": "<p>Dear {{ doc.warehouse }},</p><p>This is a reminder to acknowledge the Arrival and Deployment for <b>{{ doc.candidate_name }}</b>.</p><p><a href='/app/arrival-and-deployment/{{ doc.name }}'>Click here to view</a></p>"
        }
    ]

    for n in notifications:
        if frappe.db.exists("Notification", n["name"]):
            frappe.delete_doc("Notification", n["name"], ignore_permissions=True)
            
        doc = frappe.new_doc("Notification")
        doc.name = n["name"]
        doc.subject = n["subject"]
        doc.document_type = "Arrival and Deployment"
        doc.event = "Days After"
        doc.date_changed = "support_assigned_on"
        doc.days_in_advance = -1
        doc.channel = "Email"
        doc.condition = n["condition"]
        doc.message = n["message"]
        doc.append("recipients", {
            "receiver_by_document_field": n["field"]
        })
        doc.insert(ignore_permissions=True)
