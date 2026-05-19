import frappe

def run():
    doc = frappe.get_doc("Assignment Rule", "Arrival - Assign General Services")
    print("GS Condition:", doc.assign_condition)

    todos = frappe.get_all("ToDo", filters={'reference_type': 'Arrival and Deployment', 'reference_name': 'ARD-2026-00005'}, fields=['owner', 'allocated_to'])
    print("ToDos for ARD-2026-00005:", todos)
