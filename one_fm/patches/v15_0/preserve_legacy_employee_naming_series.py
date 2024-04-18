import frappe

def execute():
    data = frappe.get_all("Employee", fields=["name", "employee_name"])
    for employee in data:
            frappe.db.set_value("Employee", employee.name, "custom_legacy_name", employee.name)