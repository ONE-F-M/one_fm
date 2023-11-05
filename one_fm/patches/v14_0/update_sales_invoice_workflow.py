import frappe

def execute():
    """
        Update all cancelled sales invoice documents to cancelled workflow state
    """
    all_sales_invoices = frappe.get_all("Sales Invoice",{'docstatus':2})
    if all_sales_invoices:
        for each in all_sales_invoices:
            frappe.db.set_value("Sales Invoice",each.name,'workflow_state','Cancelled')
        frappe.db.commit()