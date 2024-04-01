import frappe
from frappe.utils import getdate
from frappe.desk.form.assign_to import add as add_assignment


def validate_hd_ticket(doc,event):
    if not doc.is_new():
        if not doc.agent_group:
            default_support_team = frappe.get_value("Bug Buster Employee",None,'default_support_team')
            if default_support_team:
                doc.agent_group = default_support_team
        existing_todo = frappe.get_all("ToDo",{'reference_name':doc.name,'reference_type':'HD Ticket'},['name'])
        if not existing_todo:
            bug_buster = frappe.get_all("Bug Buster",{'docstatus':1,'from_date':['<=',getdate()],'to_date':['>=',getdate()]},['employee'])
            if bug_buster:
                emp_user = frappe.get_value("Employee",bug_buster[0].employee,'user_id')
                if emp_user:
                    add_assignment({
                                    'doctype': "HD Ticket",
                                    'name': str(doc.name),
                                    'assign_to': [emp_user],
                                    "description": "Please Review Issue",
                                    })

def assign_to_bug_buster(doc, event):
    """
        Assign Ticket to the bug buster if any exists
    """
    bug_buster = frappe.get_all("Bug Buster",{'docstatus':1,'from_date':['<=',getdate()],'to_date':['>=',getdate()]},['employee'])
    if bug_buster:
        emp_user = frappe.get_value("Employee",bug_buster[0].employee,'user_id')
        if emp_user:
            existing_todo = frappe.get_all("ToDo",{'reference_name':doc.name,'reference_type':'HD Ticket'},['name'])
            if not existing_todo:
                add_assignment({
                                'doctype': "HD Ticket",
                                'name': str(doc.name),
                                'assign_to': [emp_user],
                                "description": "Please Review Issue details",
                                })