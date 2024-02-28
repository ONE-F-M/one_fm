import frappe

def execute ():
    goals = frappe.db.sql(""" 
                            SELECT `name`, `employee`
                            FROM `tabGoal`
                            WHERE `department` IS NULL
                        """, as_dict=1)
    if goals:
        for obj in goals:
            employee_department = frappe.db.get_value("Employee", obj.employee, "department")
            frappe.db.set_value("Goal", obj.name, {"department": employee_department}) if employee_department else None