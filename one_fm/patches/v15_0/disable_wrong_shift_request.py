import frappe

def execute():
    """Disable shift request HR-SHR-24-06-00227"""
    doc_ = frappe.db.exists("Shift Request",'HR-SHR-24-06-00227')
    if doc_:
        frappe.db.set_value("Shift Request",'HR-SHR-24-06-00227','to_date','2024-09-16')
        frappe.db.commit()