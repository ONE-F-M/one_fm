import os
import re

utils_file = "one_fm/utils.py"
with open(utils_file, "r") as f:
    content = f.read()

method_code = """
@frappe.whitelist()
@frappe.read_only()
def get_sibling_counts(doctype, name, items=None):
    from frappe.desk.notifications import _get_linked_document_counts, get_external_links
    
    doc = frappe.get_doc(doctype, name)
    doc.check_permission()
    
    # We are getting siblings linked by candidate_country_process
    # So we want to count where the sibling's candidate_country_process == doc.candidate_country_process
    
    links = doc.meta.get_dashboard_data()
    import json
    if items is None:
        items = []
        for group in links.transactions:
            items.extend(group.get("items"))
    if not isinstance(items, list):
        items = json.loads(items)
        
    out = {
        "external_links_found": [],
        "internal_links_found": [],
    }
    
    ccp_name = getattr(doc, "candidate_country_process", None)
    
    for d in items:
        # custom count logic for siblings
        try:
            filters = {"candidate_country_process": ccp_name} if ccp_name else {"name": "invalid"}
            docs = frappe.get_all(d, filters=filters, limit=100, distinct=True, ignore_ifnull=True)
            total_count = len(docs)
            out["external_links_found"].append({"doctype": d, "count": total_count, "open_count": 0})
        except Exception as e:
            out["external_links_found"].append({"doctype": d, "open_count": 0, "count": 0})
            
    return {"count": out}
"""

if "get_sibling_counts" not in content:
    with open(utils_file, "a") as f:
        f.write("\n" + method_code)
        print("Added get_sibling_counts to utils.py")
else:
    print("Method already exists")
