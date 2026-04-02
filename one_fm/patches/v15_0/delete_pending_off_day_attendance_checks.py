import frappe

def execute():
    """Delete Pending Approval Attendance Checks that fall on an Employee's Day Off"""
    
    # Get all Attendance Checks pending approval
    attendance_checks = frappe.get_all(
        "Attendance Check",
        filters={
            "workflow_state": "Pending Approval",
            "docstatus": ["<", 2]
        },
        fields=["name", "employee", "date"]
    )
    
    deleted_count = 0
    
    for ac in attendance_checks:
        try:
            # Check for Employee Schedule on that date
            availability = frappe.db.get_value(
                "Employee Schedule",
                {
                    "employee": ac.employee,
                    "date": ac.date
                },
                "employee_availability"
            )
            
            if availability in ["Client Day Off", "Day Off"]:
                # If the schedule indicates a day off, delete the attendance check
                frappe.delete_doc("Attendance Check", ac.name, force=True, ignore_permissions=True)
                deleted_count += 1
                frappe.db.commit()
                
        except Exception as e:
            frappe.log_error(f"Error deleting Attendance Check {ac.name}: {str(e)}", "Delete Off Day Attendance Checks Patch")
            frappe.db.rollback()
            
    print(f"Successfully deleted {deleted_count} Attendance Check records on Days Off.")
