import frappe

def check_custom():
    custom = frappe.get_all("Custom Field", filters={'dt': 'PMR Fulfillment Action'}, fields=['fieldname', 'options'])
    print(f"Custom Fields for PMR Fulfillment Action: {custom}")

def run():
    check_custom()
