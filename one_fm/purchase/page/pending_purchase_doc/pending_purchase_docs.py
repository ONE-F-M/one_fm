import frappe
def get_data():
    """
        Fetch the pending workflow actions/Todos for the RFM,RFP and PO for that user
    """
    current_user = frappe.session.user
    user_roles = frappe.get_roles(current_user)
    rfm_docs = frappe.get_all("Request for Material",{'status':['IN',['Accepted',"Draft"]],'docstatus':1,'request_for_material_approver':current_user},['name','status'])
    rfp1 = frappe.get_all('Request for Purchase',{'docstatus':1,'status':['IN',['Draft','Accepted']],'accepter':current_user},['status','name'])
    rfp2 = frappe.get_all('Request for Purchase',{'docstatus':1,'status':['IN',['Draft','Accepted']],'approver':current_user},['status','name'])
    rfp_docs = frappe.get_all('ToDo',{'status':'Open','allocated_to':current_user,'reference_type':'Request for Purchase'},['reference_name'])
    po_docs = frappe.get_all("Workflow Action",{'reference_doctype':"Purchase Order",'role':['IN',[user_roles]]})