import frappe
from one_fm.custom.assignment_rule.assignment_rule import get_assignment_rule_json_file, create_assignment_rule

def execute():
    create_assignment_rule(get_assignment_rule_json_file("leave_application_pending_approver.json"))
    if frappe.db.exists("Assignment Rule", "Leave Approver Assignment"):
        frappe.delete_doc("Assignment Rule", "Leave Approver Assignment", ignore_permissions=True)
