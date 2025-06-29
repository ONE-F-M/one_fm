import frappe

def create_assignment_rule(assignment_rule_data):
    existing = frappe.db.exists("Assignment Rule", {"name": assignment_rule_data["name"]})
    if not existing:
        frappe.get_doc(assignment_rule_data).insert()
    else:
        doc = frappe.get_doc("Assignment Rule", {"name": assignment_rule_data["name"]})
        doc.update(assignment_rule_data)
        doc.save()
