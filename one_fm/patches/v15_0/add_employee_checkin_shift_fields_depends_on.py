import frappe


def execute():
    fieldnames = [
        "operations_site",
        "project",
        "company",
        "operations_role",
        "post_abbrv",
        "roster_type",
    ]
    for fieldname in fieldnames:
        name = f"Employee Checkin-{fieldname}"
        if frappe.db.exists("Custom Field", name):
            custom_field = frappe.get_doc("Custom Field", name)
            custom_field.depends_on = "eval:doc.shift_assignment"
            custom_field.save()
