import frappe
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on, get_leave_allocation_records, get_leave_details
from datetime import date
import datetime
import collections
from one_fm.api.tasks import get_action_user,get_notification_user
from one_fm.api.v1.utils import response

@frappe.whitelist()
def get_leave_detail(employee_id: str = None, leave_id: str = None) -> dict:
    """This method gets the leave data for a specific employee.

    Args:
        employee_id (str, optional): The employee ID of user.
        leave_id (str, optional): Leave ID of a specific leave application. Defaults to None.

    Returns:
        dict: {
            message (str): Brief message indicating the response,
            data (List[dict]/dict): Leave details,
            error (str): Any error handled.
        }
    """
    if not employee_id:
        return response("Bad request", 400, None, "employee_id required.")

    if not isinstance(employee_id, str):
        return response("Bad request", 400, None, "employee_id must be of type str.")

    if leave_id and not isinstance(leave_id, str):
            return response("Bad request", 400, None, "leave_id must be of type str.")
    
    try:
        employee = frappe.db.get_value("Employee", {'employee_id':employee_id})
        
        if not employee:
            return response("Resource not found", 404, None, "No employee record found for {employee_id}".format(employee_id=employee_id))
        
        if not leave_id:
            leave_list = frappe.get_all("Leave Application", {'employee':employee}, ["name","leave_type", "status","from_date", "total_leave_days"])
            if leave_list and len(leave_list) > 0:
                return response("Success", 200, leave_list)
            else:
                return response("Resource not found", 404, None, "No leaves found for {employee_id}".format(employee_id=employee_id))
        
        elif leave_id:
            leave_data = frappe.db.get_value("Leave Application",{'name': leave_id}, ["*"] )
            if leave_data:
                return response("Success", 200, leave_data)
            else:
                return response("Resource not found", 404, None, "No leave data found for {leave_id}".format(leave_id=leave_id))
    
    except Exception as error:
       return response("Internal server error", 500, None, error)

@frappe.whitelist()
def get_leave_balance(employee: str = None, leave_type: str = None) -> dict:
    """This method gets the leave balance data for a specific employee.

    Args:
        employee (str, optional): Employee record name.
        leave_type (str, optional): Type of leave to fetch leave balance for.

    Returns:
        dict: {
            message (str): Brief message indicating the response,
            data : Leave details,
            error (str): Any error handled.
        }
    """
    if not employee:
        return response("Bad request", 400, None, "employee required.")

    if not leave_type:
        return response("Bad request", 400, None, "leave_type required.")
    
    if not isinstance(employee, str):
        return response("Bad request", 400, None, "employee must be of type str.")

    if not isinstance(leave_type, str):
        return response("Bad request", 400, None, "leave_type must be of type str.")

    today=date.today()
    
    try:
        allocation_records = get_leave_details(employee, today)
        leave_balance = allocation_records['leave_allocation'][leave_type]
        
        if leave_balance:
            return response("Success", 200, leave_balance)
        else:
            return response("Resource not found", 404, None, "No leave allocated to {employee}".format(employee=employee))
            
    except Exception as error:
        return response("Internal server error", 500, None, error)

@frappe.whitelist()
def get_leave_types(employee: str = None) -> dict:
    """This method gets the leave types from the leave allocated to a spcific employee.

    Args:
        employee (str): employee record name.

    Returns:
        dict: {
            message (str): Brief message indicating the response,
            data (List): list of leave types,
            error (str): Any error handled.
        }
    """

    if not employee:
        return response("Bad request", 400, None, "employee required.")

    if not isinstance(employee, str):
        return response("Bad request", 400, None, "employee must be of type str")
    
    try:
        leave_types_set = {}
        leave_type_list = frappe.get_list("Leave Allocation", {"employee": employee}, 'leave_type')
        
        if not leave_type_list or len(leave_type_list) == 0:
            return response("Resource not found", 404, None, "No leave allocated to {employee}".format(employee=employee))
        
        for leave_type in leave_type_list:
            leave_types_set.add(leave_type.leave_type)
        
        return response("Success", 200, list(leave_types_set))
        
    except Exception as error:
        return response("Internal server error", 500, None, error)

@frappe.whitelist()
def create_new_leave_application(employee: str = None, from_date: str = None, to_date: str = None, leave_type: str = None, reason: str = None) -> dict:
    """[summary]

    Args:
        employee (str): Employee record name.
        from_date (str): Start date => yyyy-mm-dd
        to_date (str): End date => yyyy-mm-dd
        leave_type (str): Type of leave
        reason (str): Reason for leave

    Returns:
        dict: {
            
        }
    """
    if not employee:
        return response("Bad request", 400, None, "employee required.")

    if not from_date:
        return response("Bad request", 400, None, "from_date required.")

    if not to_date:
        return response("Bad request", 400, None, "to_date required.")

    if not leave_type:
        return response("Bad request", 400, None, "leave_type required.")

    if not reason:
        return response("Bad request", 400, None, "reason required.")

    if not isinstance(employee, str):
        return response("Bad request", 400, None, "employee must be of type str")

    if not isinstance(from_date, str):
        return response("Bad request", 400, None, "from_date must be of type str.")

    if not isinstance(to_date, str):
        return response("Bad request", 400, None, "to_date must be of type str.")

    if not isinstance(leave_type, str):
        return response("Bad request", 400, None, "leave_type must be of type str.")

    if not isinstance(reason, str):
        return response("Bad request", 400, None, "reason must be of type str.")

    
    try:
        leave_approver = get_leave_approver(employee)
        
        if not leave_approver:
            return response("Resource not found", 404, None, "No leave approver found for {employee}.".format(employee=employee))
        
        leave_list = frappe.get_list("Leave Application", filters={'employee': employee,'from_date': ['>=', to_date],'to_date' : ['>=', from_date]})

        if leave_list and len(leave_list) > 0:
            return response()
        
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
    
    except Exception as error:
        return response("Internal server error", 500, None, error)

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

    Param: doc -> Leave Application Doc (which needs approval)

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