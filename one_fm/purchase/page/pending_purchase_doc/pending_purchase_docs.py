import frappe
def get_data():
    """
        Fetch the pending workflow actions for the RFM,RFP and PO for that user
    """
    current_user = frappe.session.user
    actions = frappe.get_all("Workflow Action")
    