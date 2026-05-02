import frappe

def execute():
    groups = [
        {"doctype": "App Service Group", "name": "Attendance", "group_name": "Attendance", "icon": "clock-outline", "status": "Active"},
        {"doctype": "App Service Group", "name": "Leave", "group_name": "Leave", "icon": "calendar-outline", "status": "Active"}
    ]
    
    services = [
        {"doctype": "App Service", "name": "Checkin Checkout", "service": "Checkin Checkout", "icon": "map-marker-outline", "status": "Active", "service_group": "Attendance", "assign_to_timesheet_employees": 1, "assign_to_non_timesheet_employees": 1},
        {"doctype": "App Service", "name": "Leaves", "service": "Leaves", "icon": "format-list-bulleted", "status": "Active", "service_group": "Leave", "assign_to_timesheet_employees": 1, "assign_to_non_timesheet_employees": 1},
        {"doctype": "App Service", "name": "New Leave Application", "service": "New Leave Application", "icon": "plus-circle-outline", "status": "Active", "service_group": "Leave", "assign_to_timesheet_employees": 1, "assign_to_non_timesheet_employees": 1},
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
    
    frappe.db.commit()
