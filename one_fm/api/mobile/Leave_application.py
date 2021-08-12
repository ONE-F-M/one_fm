import frappe
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on, get_leave_allocation_records, get_leave_details
from datetime import date
import datetime

@frappe.whitelist()
def get_leave_detail(employee_id):
    try:
        employee=frappe.get_value("Employee", {'employee_id':employee_id})
        leaves = frappe.get_all("Leave Application", filters={'employee':employee}, fields=["name","leave_type", "status","from_date", "total_leave_days"] )
        return leaves 
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(frappe.get_traceback())
        return frappe.utils.response.report_error(e)
    
@frappe.whitelist()
def leave_detail(leave_id):
    try:
        Leave_details = frappe.get_value("Leave Application", leave_id, '*' ) 
        return Leave_details
        print(Leave_details)
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(frappe.get_traceback())
        return frappe.utils.response.report_error(e)

@frappe.whitelist()
def get_leave_balance(employee, leave_type):
    today=date.today()
    try:
        allocation_records = get_leave_details(employee, today)
        Leave_balance = allocation_records['leave_allocation'][leave_type]
        
        if Leave_balance:
            return Leave_balance
        else:
            return ('No Leave Allocated.')
            
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(frappe.get_traceback())
        return frappe.utils.response.report_error(e)

@frappe.whitelist()
def create_new_leave_application(employee,from_date,to_date,leave_type,reason,half_day,half_day_date=None):
    try:
        leave = frappe.new_doc("Leave Application")
        leave.employee=employee
        leave.leave_type=leave_type
        leave.from_date=from_date
        leave.to_date=to_date
        leave.description=reason or "None"
        leave.half_day=half_day
        if half_day==1 and from_date!=to_date:
            if from_date<=half_day_date and to_date>=half_day_date:
                leave.half_day_date=half_day_date
            else:
                return ('Half Day Date should be between From Date and To Date.')
        leave.submit()
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(frappe.get_traceback())
        return frappe.utils.response.report_error(e)
    
