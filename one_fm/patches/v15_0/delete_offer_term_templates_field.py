import frappe

def execute():
    if frappe.db.exists('Custom Field', {'name': 'Job Offer-offer_term_templates'}):
        frappe.db.sql("""
            delete from
                `tabCustom Field`
            where
                name='Job Offer-offer_term_templates'
        """)
