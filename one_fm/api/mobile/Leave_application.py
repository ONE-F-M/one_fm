import frappe
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on, get_leave_allocation_records, get_leave_details
from datetime import date
import datetime
from one_fm.one_fm.doctype.leave_application.leave_application import get_leave_approver,get_employee_schedule, notifier_leave
import collections
from one_fm.api.tasks import get_action_user,get_notification_user

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

@frappe.whitelist()
def create_new_leave_application(employee,from_date,to_date,leave_type,reason,half_day,half_day_date=None):
    """
	Params:
	employee: erp id
    from_date,to_date,half_day_date= date in YYYY-MM-DD format
    leave_type=from leave policy
    half_day=1 or 0
	"""
    List_Shifts = get_employee_schedule(employee, from_date,to_date)
    Shifts = []
    #Shift_dict = {}
    
    for i in range(len(List_Shifts)):
        if List_Shifts[i].shift not in Shifts:
            Shifts.append(List_Shifts[i].shift)
        #Shift_dict.setdefault(List_Shifts[i].shift, []).append(List_Shifts[i].date)
    
    #if there are multiple shift, create seperate leave application
    if len(Shifts)>1:
        doc = None
        for i in range(len(List_Shifts)):
            leave_approver, Role = get_action_user(employee,List_Shifts[i].shift)
            if leave_approver is not None:
                if str(List_Shifts[i].date)==half_day_date:
                    doc = new_leave_application(employee,List_Shifts[i].date,List_Shifts[i].date,leave_type,reason,'1',half_day_date,leave_approver)
                else:
                    
                    doc= new_leave_application(employee,List_Shifts[i].date,List_Shifts[i].date,leave_type,reason,'0',None,leave_approver)

            if Role:
                notify_user = get_notification_user(employee,List_Shifts[i].shift, Role)
                if notify_user is not None:
                    for user in notify_user:
                        notifier_leave(doc, user)
    else:
        leave_approver, Role = get_action_user(employee,List_Shifts[i].shift)
        if leave_approver is not None:
            doc = new_leave_application(employee,from_date,to_date,leave_type,reason,half_day,half_day_date,leave_approver)
        if Role:
            notify_user = get_notification_user(employee,List_Shifts[i].shift, Role)
            if notify_user is not None:
                for user in notify_user:
                    notifier_leave(doc, user)

frappe.whitelist()
def new_leave_application(employee,from_date,to_date,leave_type,reason,half_day,half_day_date,leave_approver):
     try:
        leave = frappe.new_doc("Leave Application")
        leave.employee=employee
        leave.leave_type=leave_type
        leave.from_date=from_date
        leave.to_date=to_date
        leave.description=reason or "None"
        leave.half_day=half_day
        leave.half_day_date=half_day_date
        leave.follow_via_email=1
        leave.status="Open"
        leave.leave_approver = leave_approver
        leave.save()
        frappe.db.commit()
        print(leave)
        return leave
     except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(frappe.get_traceback())
        return frappe.utils.response.report_error(e)