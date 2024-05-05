import frappe

def execute():
    #Create Onboard Subcontract Employee if none exists for this Subcontract Staff Shortlist
    existing_onboard_subcontract_employee = frappe.get_all("Onboard Subcontract Employee",{'subcontract_staff_shortlist':'OPR-SSS-2023-00029'})
    if not existing_onboard_subcontract_employee:
        shortlist_doc = frappe.get_doc("Subcontract Staff Shortlist","OPR-SSS-2023-00029")
        shortlist_doc.create_subcontract_onboard_employee()
        frappe.db.commit()