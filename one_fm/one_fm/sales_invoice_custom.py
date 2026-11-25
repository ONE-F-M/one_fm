from frappe import _
import frappe
from datetime import date, datetime
from erpnext.accounts.utils import get_balance_on


@frappe.whitelist()
def allocate_advances(frm_id: str, amount: float, doc=None):
    if not doc:
        doc = frappe.get_doc("Sales Invoice",frm_id)
    if not (
        frappe.has_permission("Sales Invoice", "submit", doc=doc)
        and frappe.has_permission("Journal Entry", "create")
        and frappe.has_permission("Journal Entry", "submit")
    ):
        frappe.throw(_("You are not permitted to settle this Sales Invoice from advances."), frappe.PermissionError)
    advance_account = frappe.get_value('Accounts Additional Settings',None,'customer_advance_account')
    if advance_account:
        naming_controller = frappe.get_doc("Document Naming Settings")
        journal_series = naming_controller.get_options("Journal Entry").strip("\n")
        
        if journal_series:
            args = {
                'doctype':"Journal Entry",
                'naming_series':journal_series,
                'company':doc.company,
                'voucher_type':"Journal Entry",
                'posting_date':doc.posting_date,
                'user_remark':"Invoice settlement for Sales Invoice {}".format(doc.name)
            }
            journal_dict = frappe._dict(args)
            je_doc  = frappe.get_doc(journal_dict)
            je_doc.append("accounts",{
                'account':advance_account,
                'debit_in_account_currency':amount,
                'party_type':'Customer',
                'party':doc.customer,
            })
            je_doc.append("accounts",{
                'account':doc.debit_to,
                'credit_in_account_currency':amount,
                'party_type':'Customer',
                'party':doc.customer,
                'reference_type':'Sales Invoice',
                'reference_name':doc.name
                
            })
            je_doc.save()
            je_doc.submit()
    return


@frappe.whitelist()
def get_customer_advance_balance(customer):
    """
        Fetch the customer balance on the advance account if exists, If not account is set then return 0
    Args:
        customer (Valid Customer): A valid customer
    """
    customer_advance = frappe.get_value('Accounts Additional Settings',None,'customer_advance_account')
    if not customer_advance:
        return 0
    customer_balance = get_balance_on(customer_advance,party_type = "Customer",party = customer)
    if customer_balance > 0:
        #Debit Balance, Customer is owing
        return (0-customer_balance)
    elif customer_balance < 0:
        # Credit balance, customer is being owed
        return (abs(customer_balance))
    else:
        # Balance is zero
        return customer_balance
    return customer_balance



@frappe.whitelist()
def get_projectwise_timesheet_data(project, item_code, start_date = None, end_date = None, shift_hours = None, gender = None,  posting_date = None):
    filters = {
        'project': project, 'start_date': start_date,
        'end_date': end_date, 'item_code': item_code,
        'shift_hours': shift_hours, 'gender': gender
    }
    if posting_date != None:
        posting_date = datetime.strptime(posting_date, '%Y-%m-%d')
        filters['start_date'] = date(posting_date.year, posting_date.month, 1)
        filters['end_date'] = posting_date
    return frappe.db.sql("""
            SELECT
                t.name, t.parent, t.from_time,
                t.billing_hours, t.billing_amount as billing_amt
	 		FROM `tabTimesheet Detail` t, `tabOperations Shift` s
            WHERE t.parenttype = 'Timesheet'
                and s.name = t.shift and s.duration = %(shift_hours)s
                and t.docstatus=1 and t.project = %(project)s
                and t.is_billable = 1 and t.sales_invoice is null and t.from_time >= %(start_date)s
                and t.to_time < %(end_date)s
                and t.Activity_type in (select post_name from `tabOperations Role` where sale_item
                = %(item_code)s )
                and (select gender from `tabOperations Post` where name = t.operations_role) = %(gender)s
                order by t.from_time asc
            """, values = filters, as_dict=1)

def set_advance_payment_details(doc,event):
    """
    Set the advance  details of the advance payment doctype (Payment Entry/Journal Entry)

    Args:
        doc (object): doctype doc
        event (str): event
    """
    if doc.advances:
        for each in doc.advances:
            if each.reference_type == "Payment Entry":
                each.custom_received_amount = frappe.get_value("Payment Entry",each.reference_name,'paid_amount')
            elif each.reference_type == "Journal Entry":
                each.custom_received_amount = frappe.get_value('Journal Entry Account',{'parent':each.reference_name,'account':doc.debit_to},'credit_in_account_currency')

def set_print_settings_from_contracts(doc, method):
    set_advance_payment_details(doc,method)
    if doc.get('automatic_settlement') == "Yes" and doc.get('balance_in_advance_account'):
        if not doc.get('settlement_amount'):
            frappe.throw("Please set an amount to be settled from advances for this invoice.")
        if doc.get('settlement_amount') > doc.get('balance_in_advance_account') and doc.get('automatic_settlement') == "Yes":
            frappe.throw("Settlement amount cannot be more than balance in advance account")
        if doc.get('settlement_amount') > doc.get('outstanding_amount') and  doc.get('automatic_settlement') == "Yes":
            frappe.throw("Settlement amount cannot be more than invoice balance")
            
    if doc.contracts:
        contracts_print_settings = frappe.db.get_values('Contracts', doc.contracts, ['sales_invoice_print_format', 'sales_invoice_letter_head'], as_dict=True)
        if contracts_print_settings and len(contracts_print_settings) > 0:
            if contracts_print_settings[0].sales_invoice_print_format:
                doc.format = contracts_print_settings[0].sales_invoice_print_format
            if contracts_print_settings[0].sales_invoice_letter_head:
                doc.letter_head = contracts_print_settings[0].sales_invoice_letter_head
