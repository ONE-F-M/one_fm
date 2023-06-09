import frappe

def execute():
    print("Patching Employee Checkin")
    ecs = frappe.get_all("Employee Checkin", filters={
        'date': ['BETWEEN', ['2023-06-08', '2023-06-09']]
    }, fields="*")
    for i in ecs:
        frappe.db.set_value("Employee Checkin", i.name, 'post_abbrv', frappe.db.get_value("Shift Assignment", i.shift_assignment, 'post_abbrv'))
        frappe.db.set_value("Employee Checkin", i.name, 'operations_role', frappe.db.get_value("Shift Assignment", i.shift_assignment, 'operations_role'))
        frappe.db.set_value("Employee Checkin", i.name, 'operations_site', frappe.db.get_value("Shift Assignment", i.shift_assignment, 'site'))
        frappe.db.set_value("Employee Checkin", i.name, 'project', frappe.db.get_value("Shift Assignment", i.shift_assignment, 'project'))
        frappe.db.set_value("Employee Checkin", i.name, 'company', frappe.db.get_value("Shift Assignment", i.shift_assignment, 'company'))
        frappe.db.set_value("Employee Checkin", i.name, 'operations_role', frappe.db.get_value("Shift Assignment", i.shift_assignment, 'operations_role'))