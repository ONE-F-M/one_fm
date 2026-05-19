import frappe

def check():
    props = frappe.get_all("Property Setter", 
        filters={'doc_type': 'PMR Fulfillment Action', 'field_name': 'action_type'}, 
        fields=['property', 'value']
    )
    print("Property Setters for action_type:")
    for p in props:
        print(f"  {p.property} = {p.value}")

def run():
    check()
