import frappe

def after_migrate():
    frappe.get_attr("one_fm.setup.workflow.leave_acknowledgement_form.execute")()