import frappe

def after_insert(doc, event):
    """
        Bank Account document event that update Employee document if
        Salary Mode='Bank'
    """
    if(doc.party_type=='Employee' and doc.party):
        employee = frappe.get_doc(doc.party_type, doc.party)
        if employee.salary_mode=='Bank' and not employee.bank_account:
            employee.db_set('bank_account', doc.name)
            employee.reload()
