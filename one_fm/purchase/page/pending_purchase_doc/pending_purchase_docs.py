import frappe
@frappe.whitelist()
def get_data():
    """
        Fetch the pending workflow actions/Todos for the RFM,RFP and PO for that user
    """
    current_user = frappe.session.user
    user_roles = frappe.get_roles(current_user)
    rfm_docs = frappe.get_all("Request for Material",{'status':['IN',['Accepted',"Draft"]],'docstatus':1,'request_for_material_approver':current_user},['name','status'])
    rfp1 = frappe.get_all('Request for Purchase',{'docstatus':1,'status':'Draft','accepter':current_user},['status','name'])
    rfp2 = frappe.get_all('Request for Purchase',{'docstatus':1,'status':'Accepted','approver':current_user},['status','name'])
    rfp_docs = frappe.get_all('ToDo',{'status':'Open','allocated_to':current_user,'reference_type':'Request for Purchase'},['reference_name']) 
    # For the query above, we have to ensure that only approved RFP are added to the page
    po_docs = frappe.get_all("Workflow Action",{'reference_doctype':"Purchase Order",'role':['IN',[user_roles]]},['reference_name','workflow_state']) 
    results = PendingPurchases(rfm_data=rfm_docs,rfp_data1=rfp1,rfp_data2=rfp2,rfp_data3=rfp_docs,po_data=po_docs)
    return results.items
    
class PendingPurchases:
    def __init__(self,rfm_data,rfp_data1,rfp_data2,rfp_data3,po_data):
        self.items = []
        self.rfm_data = rfm_data
        self.rfp_data_pending_acceptance = rfp_data1
        self.rfp_data_pending_approval = rfp_data2
        self.rfp_data_pending_conversion = rfp_data3
        self.po_data = po_data
        self.added_rfm_docs = []
        self.added_rfp_docs = []
        self.added_po_docs = []
        self.sort_rfm()
        self.sort_rfp()
        self.sort_po()
    
    
    def sort_rfm(self):
        for each in self.rfm_data:
            if each.name not in self.added_rfm_docs:
                self.items.append({'rfm':each.name,'rfm_status':each.status})
                self.added_rfm_docs.append(each.name)

    def update_items(self,document,row,is_rfm = False,is_rfp = False):
        #Loop through the items table and update the row where the document is referenced
        if is_rfm:
            for each in self.items:
                if each['rfm'] == document:
                    each['rfp'] = row['name']
                    each['status'] = row['status']
                    self.added_rfp_docs.append(row['name'])
        if is_rfp:
            for each in self.items:
                if each['rfp'] == document:
                    each['po'] = row['name']
                    each['status'] = row['status']
                    self.added_po_docs.append(row['name'])
            
            
    def sort_rfp(self):
        for each in self.rfp_data_pending_acceptance:
            if each.name not in self.added_rfp_docs:
                rfm = frappe.db.get_value("Request for Purchase",each.name,'request_for_material')
                if rfm in self.added_rfm_docs:
                    self.update_items(rfm,{'name':each.name,'status':'Pending Acceptance'},is_rfm=True)
                else:
                    self.items.append({'rfm':rfm,'rfm_status':"Submitted",'rfp':each.name,'rfp_status':'Pending Acceptance'})
                    self.added_rfm_docs.append(rfm)
                    self.added_rfp_docs.append(each.name)
        for one in self.rfp_data_pending_approval:
            if one.name not in self.added_rfp_docs:
                rfm = frappe.db.get_value("Request for Purchase",one.name,'request_for_material')
                if rfm in self.added_rfm_docs:
                    self.update_items(rfm,{'name':one.name,'status':'Pending Approval'},is_rfm=True)
                else:
                    self.items.append({'rfm':rfm,'rfm_status':"Submitted",'rfp':one.name,'rfp_status':"Pending Approval"})
                    self.added_rfm_docs.append(rfm)
                    self.added_rfp_docs.append(one.name)
        for ind in self.rfp_data_pending_conversion:
            if ind.reference_name not in self.added_rfp_docs and frappe.get_value("Request for Purchase",ind.reference_name,'docstatus') == 1:
                rfm = frappe.db.get_value("Request for Purchase",ind.reference_name,'request_for_material')
                # only add rows that have been accepted and approved, if the RFP has not been approved or accepted then leave it.
                if frappe.get_value("Request for Purchase",ind.reference_name,'status') == ['Approved']:
                    if rfm in self.added_rfm_docs:
                        self.update_items(rfm,{'name':ind.reference_name,'status':'Pending Conversion to PO'},is_rfm=True)
                    else:
                        self.items.append({'rfm':rfm,'rfm_status':"Submitted",'rfp':ind.reference_name,'rfp_status':"Pending Conversion to PO"})
                        self.added_rfm_docs.append(rfm)
                        self.added_rfp_docs.append(ind.reference_name)
    
    
    def sort_po(self):
        for each in self.po_data:
            if int(frappe.get_value("Purchase Order",each.reference_name,'docstatus')) < 1:
                rfp = frappe.get_value("Purchase Order",each.reference_name,'one_fm_request_for_purchase')
                rfm = frappe.get_value("Purchase Order",each.reference_name,'request_for_material')
                if not rfm:
                     rfm = frappe.get_value("Request for Purchase",rfp,'request_for_material')
                if rfp in self.added_rfp_docs:
                    self.update_items(rfp,{'name':each.reference_name,'status':each.workflow_state},is_rfp=True)
                if rfm not in self.added_rfm_docs and rfp not in self.added_rfp_docs:
                    self.items.append({'rfm':rfm,'rfm_status':"Submitted",'rfp':rfp,'rfp_status':"Submitted",'po':each.reference_name,'po_status':each.workflow_state})
                    self.added_rfm_docs.append(rfm)
                    self.added_rfp_docs.append(rfp)
                    
                    
                    
                
                
            
    
    
    