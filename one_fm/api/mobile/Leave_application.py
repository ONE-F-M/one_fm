import frappe
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on, get_leave_allocation_records, get_leave_details
from datetime import date
import datetime
from one_fm.one_fm.doctype.leave_application.leave_application import get_leave_approver,get_employee_schedule, notifier_leave
import collections
from one_fm.api.tasks import get_action_user,get_notification_user
from one_fm.operations.page.checkpoint_scan.checkpoint_scan import response

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
            frappe.throw(_('You Are Not currently Allocated with a leave policy'))
            return ('No Leave Allocated.')
            
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(frappe.get_traceback())
        return frappe.utils.response.report_error(e)

@frappe.whitelist()
def leave_type_list(employee):
    try:
        leave_policy_list = frappe.get_list("Leave Allocation", {"employee":employee}, 'leave_type')
        #return leave_policy_list
        leave_policy=[]
        if leave_policy_list:
            for types in leave_policy_list:
                leave_policy.append(types.leave_type)
            return leave_policy
        else:
            frappe.throw(_('You Are Not currently Allocated with a leave policy'))
            return {'message': _('You Are Not currently Allocated with a leave policy.')}
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(frappe.get_traceback())
        return frappe.utils.response.report_error(e)

@frappe.whitelist()
def leave_notify(docname,status):
    doc = frappe.get_doc("Leave Application",{"name":docname})
    doc.status=status
    doc.save()
    doc.submit()
    frappe.db.commit()

#This function is the api to create a new leave notification.
#bench execute --kwargs "{'employee':'HR-EMP-00002','from_date':'2021-11-02','to_date':'2021-11-02','leave_type':'Annual Leave','reason':'fever'}"  one_fm.api.mobile.Leave_application.create_new_leave_application
@frappe.whitelist()
def create_new_leave_application(employee,from_date,to_date,leave_type,reason):
    """
    Params:
    employee: erp id
    from_date,to_date,half_day_date= date in YYYY-MM-DD format
    leave_type=from leave policy
    half_day=1 or 0
    """
    #get Leave Approver of the employee.
    leave_approver = get_leave_approver(employee)
    #check if leave exist and overlaps with the given date (StartDate1 <= EndDate2) and (StartDate2 <= EndDate1)
    leave_exist = frappe.get_list("Leave Application", filters={"employee": employee,'from_date': ['>=', to_date],'to_date' : ['>=', from_date]})
    print(leave_exist)
    if leave_exist:
        return response('You have already applied leave for this date.', 400)
    else:
        if leave_approver:
            #if sick leave, automatically accept the leave application
            if leave_type == "Sick Leave":
                doc = new_leave_application(employee,from_date,to_date,leave_type,"Approved",reason,leave_approver)
                doc.submit()
                frappe.db.commit()
            #else keep it open and that sends the approval notification to the 'leave approver'.
            else:
                doc = new_leave_application(employee,from_date,to_date,leave_type,"Open",reason,leave_approver)
        return doc

#create new leave application doctype
frappe.whitelist()
def new_leave_application(employee,from_date,to_date,leave_type,status,reason,leave_approver):
     try:
        leave = frappe.new_doc("Leave Application")
        leave.employee=employee
        leave.leave_type=leave_type
        leave.from_date=from_date
        leave.to_date=to_date
        leave.description=reason or "None"
        leave.follow_via_email=1
        leave.status=status
        leave.leave_approver = leave_approver
        leave.save()
        frappe.db.commit()
        return leave
     except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(frappe.get_traceback())
        return frappe.utils.response.report_error(e)