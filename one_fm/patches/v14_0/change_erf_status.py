import frappe
def execute():
    try:
        query = """
            update
                `tabERF` as erf,
                
            set
                erf.status = 'Open'
            where
                erf.status = 'Draft'
                
        """
        frappe.db.sql(query)
    except:
        frappe.log_error(title="Error Updating ERF",message=frappe.get_traceback())