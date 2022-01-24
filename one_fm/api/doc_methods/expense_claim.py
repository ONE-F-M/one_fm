import frappe
from frappe import _



def on_submit(doc, event):
    """
        Expense Cliam submit events
    """
    # create Payment Request
    if(doc.approval_status=='Approved' and not doc.is_paid):
        pr = frappe.get_doc(dict(
            doctype='Payment Request',
            payment_request_type='Outward',
            party_type='Employee',
            party=doc.employee,
            reference_doctype='Expense Claim',
            reference_name=doc.name,
            mode_of_payment=doc.mode_of_payment,
            grand_total=doc.grand_total,
            message=doc.remark
        )).insert()
