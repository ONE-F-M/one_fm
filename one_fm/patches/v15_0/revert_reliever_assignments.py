import frappe
from frappe.utils import today
from one_fm.one_fm.doctype.reliever_assignment.reliever_assignment import reassign_responsibilities

def execute():
    reliever_assignments = frappe.get_all("Reliever Assignment", filters={"status":"Transferred","assignment_period_end":["<=", today()]})

    for assignment in reliever_assignments:
        frappe.enqueue(reassign_responsibilities, leave_application=assignment["name"])