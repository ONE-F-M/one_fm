import frappe
from frappe.utils import getdate
from frappe.desk.form.assign_to import add as add_assignment


def validate_hd_ticket(doc, event):
    bug_buster = frappe.get_all("Bug Buster",{'docstatus':1,'from_date':['<=',getdate()],'to_date':['>=',getdate()]},['employee'])
    if bug_buster:
        emp_user = frappe.get_value("Employee",bug_buster[0].employee,'user_id')
        if emp_user:
            doc.custom_bug_buster = emp_user
