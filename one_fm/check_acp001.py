import frappe

def check_acp():
    doc = frappe.get_doc("Agency Country Process", "ACP001")
    for row in doc.agency_process_details:
        if row.process_name == "Arrival & Deployment" or row.reference_type == "Arrival and Deployment":
            print(f"Row {row.idx}: {row.process_name}")
            print(f"  reference_type: '{row.reference_type}'")
            print(f"  reference_name: '{row.reference_name}'")

def run():
    check_acp()
