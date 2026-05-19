import frappe

def execute():
    # Get all resignations where employee is missing
    docs = frappe.get_all("Employee Resignation", filters={"employee": ["is", "not set"]})
    print(f"Found {len(docs)} resignations with missing employee field.")
    for d in docs:
        doc = frappe.get_doc("Employee Resignation", d.name)
        if doc.employees and len(doc.employees) > 0:
            emp = doc.employees[0].employee
            if emp:
                frappe.db.set_value("Employee Resignation", doc.name, "employee", emp)
                print(f"Updated {doc.name} with employee {emp}")
    frappe.db.commit()

