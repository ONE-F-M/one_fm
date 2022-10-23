import frappe
from frappe.utils import getdate


def before_save(doc, event):
    current_doc = frappe.get_doc("Employee", doc.name)
    if (doc.shift != current_doc.shift) and (doc.shift_working != current_doc.shift_working):
        schedules = frappe.get_list("Employee Schedule", filters={'employee':doc.name, 'date': ['>', getdate()]})
        for name in schedules:
            frappe.get_doc("Employee Schedule", name).delete()

