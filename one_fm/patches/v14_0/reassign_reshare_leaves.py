import frappe
from hrms.hr.utils import share_doc_with_approver
def execute():
    #Reshare and Reassign all draft leave applications
    all_leaves = frappe.get_all("Leave Application",{"docstatus":0})
    for each in all_leaves:
        try:
            leave_doc = frappe.get_doc("Leave Application",each.name)
            leave_doc.assign_to_leave_approver()
            share_doc_with_approver(leave_doc, leave_doc.leave_approver)
        except:
            frappe.log_error("An Error Occured while closing {}".format(each.name))
            continue