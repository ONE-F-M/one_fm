import frappe

def execute():
    groups = [
        {"doctype": "App Service Group", "name": "HR", "group_name": "HR", "icon": "account-tie-outline", "status": "Active"}
    ]
    
    services = [
        {"doctype": "App Service", "name": "Employee Resignation", "service": "Employee Resignation", "icon": "file-document-edit-outline", "status": "Active", "service_group": "HR", "assign_to_timesheet_employees": 1, "assign_to_non_timesheet_employees": 1},
        {"doctype": "App Service", "name": "Resignation Withdrawal", "service": "Resignation Withdrawal", "icon": "file-undo-outline", "status": "Active", "service_group": "HR", "assign_to_timesheet_employees": 1, "assign_to_non_timesheet_employees": 1},
    ]
    
    for g in groups:
        if not frappe.db.exists("App Service Group", g["name"]):
            d = frappe.get_doc(g)
            d.flags.ignore_mandatory = True
            d.insert(ignore_permissions=True)
            print(f"Created App Service Group: {g['name']}")

    for s in services:
        if not frappe.db.exists("App Service", s["name"]):
            d = frappe.get_doc(s)
            d.flags.ignore_mandatory = True
            d.insert(ignore_permissions=True)
            print(f"Created App Service: {s['name']}")
            
    # Removed demo assignment loop per PR review
    
    frappe.db.commit()
