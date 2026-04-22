import frappe
import json


def execute():
    if not frappe.db.exists("Web Form", "subcontract-staff-attendance"):
        return

    json_path = frappe.get_app_path(
        "one_fm",
        "one_fm",
        "web_form",
        "subcontract_staff_attendance",
        "subcontract_staff_attendance.json"
    )

    with open(json_path) as f:
        doc_dict = json.load(f)


    frappe.db.set_value(
        "Web Form",
        "subcontract-staff-attendance",
        "client_script",
        doc_dict.get("client_script", ""),
        update_modified=False
    )
    frappe.db.commit()