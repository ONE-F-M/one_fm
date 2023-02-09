from datetime import datetime
import frappe, json
from frappe.utils import getdate, nowdate, get_last_day
from frappe.desk.query_report import *


def generate_contracts_invoice():
    """
        Generate Sales Invoice for Contracts
    """
    try:
        contracts = frappe.get_list('Contracts', filters={
            'workflow_state':'Active',
            # 'due_date':str(datetime.today().date().day)
        })
        # generate
        for contract in contracts:
            contract_doc = frappe.get_doc("Contracts", contract.name)
            contract_due_date = contract_doc.due_date

            if str(contract_due_date).lower() == "end of month" and getdate() == get_last_day(getdate()):
                contract_doc.generate_sales_invoice()

            elif contract_due_date == str(datetime.today().date().day):
                contract_doc.generate_sales_invoice()

    except Exception as e:
        frappe.log(str(e), "Contracts Invoice")

def roster_projection_view_task():
    """
        Generate ROSTER projection
    """
    report = frappe.get_doc("Report", 'Roster Projection View')
    background_enqueue_run(report.name,
        filters=json.dumps(
            {'month':datetime.today().month, 'year':datetime.today().year}), user='Administrator'
    )
