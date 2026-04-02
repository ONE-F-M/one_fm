import frappe

def execute():
    """Update attendance for Leave Extension Requests created after 2026-01-20"""
    
    # 1. Get all approved Leave Extension Requests
    leave_extension_requests = frappe.get_all(
        "Leave Extension Request",
        filters={
            "creation": [">=", "2026-01-20"],
            "docstatus": 1
        },
        fields=["name"]
    )
    print(f"Found {len(leave_extension_requests)} Leave Extension Requests.")
    
    for ler in leave_extension_requests:
        try:
            # 2. Fetch the leave application with the leave extension name in the custom_leave_extension_request field
            linked_applications = frappe.get_all(
                "Leave Application",
                filters={
                    "custom_leave_extension_request": ler.name,
                    "docstatus": ["<", 2]
                },
                fields=["name"]
            )
            
            for la in linked_applications:
                # 3. Update attendance
                leave_app = frappe.get_doc("Leave Application", la.name)
                leave_app.update_attendance()
                frappe.db.commit()
                print(f"Updated attendance for {la.name}")
                
        except Exception as e:
            frappe.log_error(f"Error updating attendance for extension {ler.name}: {str(e)}", "Leave Extension Attendance Update")
            frappe.db.rollback()