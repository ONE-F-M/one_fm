import frappe

def run():
    doc = frappe.new_doc("Candidate Country Process")
    doc.job_applicant = "HR-APP-2026-00585"
    doc.job_offer = "HR-OFF-2026-00070"
    doc.start_date = "2026-05-15"
    doc.agency_country_process = "ACP001"
    doc.insert(ignore_permissions=True)
    print("Created:", doc.name)
