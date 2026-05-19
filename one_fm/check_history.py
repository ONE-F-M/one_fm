import frappe
import json

def check_history(docname):
    print(f"--- History for {docname} ---")
    doc = frappe.get_doc("Agency Country Process", docname)
    print(f"Current rows: {len(doc.get('agency_process_details'))}")
    
    versions = frappe.get_all("Version", filters={"docname": docname}, order_by="creation desc")
    for v in versions:
        vdoc = frappe.get_doc("Version", v.name)
        data = json.loads(vdoc.data)
        
        added = len(data.get("added", []))
        removed = len(data.get("removed", []))
        
        if added > 0 or removed > 0:
            print(f"Version {v.name} ({vdoc.creation}): Added {added}, Removed {removed}")

def run():
    check_history("ACP001")
    check_history("ACP002")
