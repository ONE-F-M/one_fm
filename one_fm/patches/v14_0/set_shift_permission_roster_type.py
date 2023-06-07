import frappe


def execute():
    print("Setting roster_type in Shift Permission")
    shift_permissions = frappe.get_all("Shift Permission", filters={'date':[">=", "2023-06-01"]}, fields="*")
    for i in shift_permissions:
        frappe.db.set_value("Shift Permission", i.name, 'roster_type', frappe.db.get_value("Shift Assignment", i.shift_assignment, 'roster_type'))
