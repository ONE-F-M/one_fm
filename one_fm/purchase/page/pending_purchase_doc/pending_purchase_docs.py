import frappe
def get_data():
    """
        Fetch the pending workflow actions for the RFM,RFP and PO for that user
    """
    current_user = frappe.session.user
    rfm_docs = frappe.get_all("Request for Material",{'docstatus':1,'request_for_material_approver':current_user,'status':'Draft'},['name','status'])
    rfq_docs = frappe.get_all('ToDo',{'status':'Open','allocated_to':current_user,'reference_type':'Request for Purchase'},['reference_name'])
    po_docs = frappe.get_all("Workflow Action")