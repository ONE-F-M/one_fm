import frappe
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on, get_leave_allocation_records, get_leave_details
from datetime import date
import datetime
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

#This function is the api to create a new leave notification.
#bench execute --kwargs "{'employee':'HR-EMP-00002','from_date':'2021-11-17','to_date':'2021-11-17','leave_type':'Annual Leave','reason':'fever'}"  one_fm.api.mobile.Leave_application.create_new_leave_application
@frappe.whitelist()
def create_new_leave_application(employee,from_date,to_date,leave_type,reason):
    """
    Params:
        employee: erp id
        from_date,to_date,half_day_date= date in YYYY-MM-DD format
        leave_type=from leave policy
        reason
    Return:
        Success, 201 : Success on Creation of Leave Application
		Bad request, 400: When Leave already Exists or when employee doesn't have a leave approver.
		server error, 500: Failed to create new leave application
    """
    #get Leave Approver of the employee.
    leave_approver = get_leave_approver(employee)
    #check if leave exist and overlaps with the given date (StartDate1 <= EndDate2) and (StartDate2 <= EndDate1)
    leave_exist = frappe.get_list("Leave Application", filters={"employee": employee,'from_date': ['>=', to_date],'to_date' : ['>=', from_date]})
    # Return response status 400, if the leave exists.
    if leave_exist:
        return response('You have already applied leave for this date.',[], 400)
    else:
        if leave_approver:
            try:
                #if sick leave, automatically accept the leave application
                if leave_type == "Sick Leave":
                    doc = new_leave_application(employee,from_date,to_date,leave_type,"Approved",reason,leave_approver)
                    doc.submit()
                    frappe.db.commit()
                #else keep it open and that sends the approval notification to the 'leave approver'.
                else:
                    doc = new_leave_application(employee,from_date,to_date,leave_type,"Open",reason,leave_approver)
                return response('Success',doc, 201)
            except Exception as e:
                frappe.log_error(frappe.get_traceback())
                return response(e,[], 500)
        else:
            return response("You don't have a leave approver.",[], 400)

#create new leave application doctype
frappe.whitelist()
def new_leave_application(employee,from_date,to_date,leave_type,status,reason,leave_approver):
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

# Function to create response to the API. It generates json with message, data object and the status code.
def response(message, data, status_code):
     frappe.local.response["message"] = message
     frappe.local.response["data_obj"] = data
     frappe.local.response["http_status_code"] = status_code
     return

@frappe.whitelist()
def get_leave_approver(employee):
    """
    This function fetches the leave approver for a given employee.
    The leave approver is fetched  either Report_to or Leave Approver. 
    But, if both don't exist, Operation manager is the Leave Approver.

    Params: ERP Employee ID

    Return: User ID of Leave Approver

    """
    approver = None
    #check if employee has leave approver or report to assigned in the employee doctype
    leave_approver, report_to = frappe.db.get_value("Employee", employee, ["leave_approver", "reports_to"])
    if not leave_approver:
        if report_to:
            approver = frappe.db.get_value('Employee', {'name': report_to}, ['user_id'])
        else:
            #if not, return the 'Operational Manager' as the leave approver. But, check if employee himself is not a leave manager.
            operation_manager = frappe.db.get_value('Employee', {'Designation': "Operation Manager"}, ['name','user_id'])
            if operation_manager[0]!= employee:
                approver = operation_manager[1]
    else:
        approver = leave_approver
    return approver

def notify_leave_approver(doc):
    """
    This function is to notify the leave approver and request his action. 
    The Message sent through mail consist of 2 action: Approve and Reject.(It is sent only when the not sick leave.)

    Param: doc -> Leave Application DocName (which needs approval)

    It's a action that takes place on update of Leave Application.
    """
    #If Leave Approver Exist
    if doc.leave_approver:
        parent_doc = frappe.get_doc('Leave Application', doc.name)
        args = parent_doc.as_dict() #fetch fields from the doc.

        #Fetch Email Template for Leave Approval. The email template is in HTML format.
        template = frappe.db.get_single_value('HR Settings', 'leave_approval_notification_template')
        if not template:
            frappe.msgprint(_("Please set default template for Leave Approval Notification in HR Settings."))
            return
        email_template = frappe.get_doc("Email Template", template)
        message = frappe.render_template(email_template.response_html, args)

        #send notification
        doc.notify({
            # for post in messages
            "message": message,
            "message_to": doc.leave_approver,
            # for email
            "subject": email_template.subject
        })