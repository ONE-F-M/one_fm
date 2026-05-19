import frappe

def check_acp001_fields():
    rows = frappe.get_all("Agency Process Details", 
        filters={"parent": "ACP001"}, 
        fields=["idx", "process_name", "reference_type", "reference_complete_status_field", "reference_complete_status_value"],
        order_by="idx asc"
    )
    for r in rows:
        print(f"Row {r.idx}: {r.process_name} | Type: {r.reference_type} | Field: {r.reference_complete_status_field} | Value: {r.reference_complete_status_value}")

def run():
    check_acp001_fields()
