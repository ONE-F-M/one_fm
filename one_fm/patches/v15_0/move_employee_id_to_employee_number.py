import frappe

def execute():
    data = frappe.get_all("Employee", fields=["name", "employee_name", "employee_id"])
    for employee in data:
        if employee.employee_id:
            new_id = employee.employee_id[0:7]
            frappe.db.set_value("Employee", employee.name, "employee_number", new_id)