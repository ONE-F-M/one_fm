import frappe

def list_acp():
    acps = frappe.get_all("Agency Country Process", pluck="name")
    for name in acps:
        doc = frappe.get_doc("Agency Country Process", name)
        rows = len(doc.get("agency_process_details") or [])
        print(f"{name}: {rows} rows")
