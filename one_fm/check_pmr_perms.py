import frappe

def check_perms():
    meta = frappe.get_meta("Project Manpower Request")
    field = meta.get_field("fulfillment_actions")
    if not field:
        print("Field 'fulfillment_actions' not found in PMR.")
        return
        
    print(f"Field permlevel: {field.permlevel}")
    
    # Check Property Setters for any dynamic permission changes
    props = frappe.get_all("Property Setter", 
        filters={'doc_type': 'Project Manpower Request', 'field_name': 'fulfillment_actions'}, 
        fields=['property', 'value']
    )
    print("Property Setters:")
    for p in props:
        print(f"  {p.property} = {p.value}")

def run():
    check_perms()
