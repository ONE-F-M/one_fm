from datetime import datetime
import frappe


def generate_contracts_invoice():
    """
        Generate Sales Invoice for Contracts
    """
    try:
        contracts = frappe.get_list('Contracts', filters={
        'docstatus':1, 'workflow_state':'Active', 'due_date':str(datetime.today().date().day)
        })
        # generate
        for i in contracts:
            contract = frappe.get_doc("Contracts", i.name).generate_sales_invoice()
    except Exception as e:
        frappe.log(str(e), "Contracts Invoice")
