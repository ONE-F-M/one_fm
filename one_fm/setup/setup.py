import frappe

def after_migrate():
    frappe.get_attr("one_fm.setup.workflow.leave_acknowledgement_form.execute")()
    frappe.get_attr("one_fm.setup.assignment_rule.subcontract_staff_shortlist.execute")()