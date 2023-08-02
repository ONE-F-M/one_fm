import frappe
from frappe.utils import getdate, add_days


def on_update(doc, method=None):
    
    try:
        current_doc = frappe.get_doc("Employee", doc.name)
        if (doc.shift != current_doc.shift) and (doc.shift_working != current_doc.shift_working):
            frappe.db.sql(f"""
                DELETE FROM `tabEmployee Schedule` WHERE employee='{doc.employee}'
                AND date>'{getdate()}'
            """)
    except:
        pass

    # clear future employee schedules
    clear_schedules(doc)


def clear_schedules(doc):
    # clear future employee schedules
    todays_date = getdate()
    if doc.status == 'Left' and doc.relieving_date <= todays_date:
        frappe.db.sql(f"""
            DELETE FROM `tabEmployee Schedule` WHERE employee='{doc.name}'
            AND date>'{doc.relieving_date}'
        """)
        frappe.msgprint(f"""
            Employee Schedule cleared for {doc.employee_name} starting from {add_days(doc.relieving_date, 1)} 
        """)

def assign_role_profile_based_on_designation(doc, method=None):
    if doc.designation:
        if doc.is_new:
            if doc.user_id:
                designation = doc.designation
            else:
                return
        else:
            if doc.designation != doc.get_doc_before_save().designation:
                designation = doc.designation
            else:
                return
        r_prof = frappe.db.get_value("Designation", designation, "role_profile")
        if r_prof:
            user = frappe.get_doc("User", doc.user_id)
            user.role_profile_name = r_prof
            user.save()