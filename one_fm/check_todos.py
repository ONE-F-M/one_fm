import frappe

def run():
    todos = frappe.db.sql("""
        SELECT name, owner, allocated_to, description
        FROM `tabToDo`
        WHERE reference_type = 'Arrival and Deployment'
        AND reference_name = 'ARD-2026-00005'
    """, as_dict=True)
    for t in todos:
        print(t)
