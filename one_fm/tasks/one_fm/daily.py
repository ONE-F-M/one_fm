from datetime import datetime
import frappe
from frappe.utils import getdate, nowdate


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

def mark_future_attendance_request():
    """
        GET attendance request for the future where date is today
    """
    attendance_requests = frappe.db.sql(f"""
        SELECT name FROM `tabAttendance Request`
        WHERE '{nowdate()}' BETWEEN from_date AND to_date AND future_request=1 
        AND docstatus=1
    """, as_dict=1)
    for row in attendance_requests:
        try:
            frappe.get_doc("Attendance Request", row.name).create_future_attendance()
        except Exception as e:
            frappe.log_error(str(e), 'Attendance Request')
