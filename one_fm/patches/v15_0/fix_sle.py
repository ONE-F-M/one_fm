import frappe
from erpnext.stock.utils import get_combine_datetime

def execute():
    all_sle = frappe.get_all("Stock Ledger Entry",{"posting_datetime":['is','not set']},['name','posting_date','posting_time'])
    if all_sle:
        for each in all_sle:
            try:
                combined_datetime = get_combine_datetime(each.posting_date,each.posting_time)
                frappe.db.set_value("Stock Ledger Entry",each.name,'posting_datetime',combined_datetime)
            except:
                frappe.log_error(title = "Error Update SLE",message = frappe.get_traceback())
            