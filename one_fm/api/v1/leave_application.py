import frappe
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on, get_leave_allocation_records, get_leave_details
from datetime import date
import datetime
import collections
from one_fm.api.tasks import get_action_user,get_notification_user
from one_fm.api.v1.utils import response, validate_date

@frappe.whitelist()
def get_leave_detail(employee_id: str = None, leave_id: str = None) -> dict:
    """This method gets the leave data for a specific employee.

    Args:
        employee_id (str, optional): The employee ID of user.
        leave_id (str, optional): Leave ID of a specific leave application. Defaults to None.

    Returns:
        dict: {
            message (str): Brief message indicating the response,
			status_code (int): Status code of response.
            data (dict): Leave data,
            error (str): Any error handled.
        }
    """
    if not employee_id:
        return response("Bad Request", 400, None, "employee_id required.")

    if not isinstance(employee_id, str):
        return response("Bad Request", 400, None, "employee_id must be of type str.")

    if leave_id and not isinstance(leave_id, str):
            return response("Bad Request", 400, None, "leave_id must be of type str.")
    
    try:
        employee = frappe.db.get_value("Employee", {'employee_id':employee_id})
        
        if not employee:
            return response("Resource Not Found", 404, None, "No employee record found for {employee_id}".format(employee_id=employee_id))
        
        if not leave_id:
            leave_list = frappe.get_all("Leave Application", {'employee':employee}, ["name","leave_type", "status","from_date", "total_leave_days"])
            if leave_list and len(leave_list) > 0:
                return response("Success", 200, leave_list)
            else:
                return response("Resource Not Found", 404, None, "No leaves found for {employee_id}".format(employee_id=employee_id))
        
        elif leave_id:
            leave_data = frappe.get_doc("Leave Application", leave_id)
            if leave_data:
                return response("Success", 200, leave_data.as_dict())
            else:
                return response("Resource Not Found", 404, None, "No leave data found for {leave_id}".format(leave_id=leave_id))
    
    except Exception as error:
       return response("Internal Server Error", 500, None, error)

@frappe.whitelist()
def get_leave_balance(employee_id: str = None, leave_type: str = None) -> dict:
    """This method gets the leave balance data for a specific employee.

    Args:
        employee_id (str, optional): employee_id of user.
        leave_type (str, optional): Type of leave to fetch leave balance for.

    Returns:
        dict: {
            message (str): Brief message indicating the response,
			status_code (int): Status code of response.
            data (dict): Leave balance.
            error (str): Any error handled.
        }
    """
    if not employee_id:
        return response("Bad Request", 400, None, "employee_id required.")

    if not leave_type:
        return response("Bad Request", 400, None, "leave_type required.")
    
    if not isinstance(employee_id, str):
        return response("Bad Request", 400, None, "employee_id must be of type str.")

    if not isinstance(leave_type, str):
        return response("Bad Request", 400, None, "leave_type must be of type str.")

    today=date.today()
    
    try:
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))
        
        allocation_records = get_leave_details(employee, today)
        leave_balance = allocation_records['leave_allocation'][leave_type]
        
        if leave_balance:
            return response("Success", 200, int(leave_balance))
        else:
            return response("Resource Not Found", 404, None, "No leave allocated to {employee}".format(employee=employee_id))
            
    except Exception as error:
        return response("Internal Server Error", 500, None, error)

@frappe.whitelist()
def get_leave_types(employee_id: str = None) -> dict:
    """This method gets the leave types from the leave allocated to a specific employee.

    Args:
        employee_id (str): employee id of user.

    Returns:
        dict: {
            message (str): Brief message indicating the response,
			status_code (int): Status code of response.
            data (List): List of leave types,
            error (str): Any error handled.
        }
    """

    if not employee_id:
        return response("Bad Request", 400, None, "employee_id required.")

    if not isinstance(employee_id, str):
        return response("Bad Request", 400, None, "employee_id must be of type str")
    
    try:
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))
        
        leave_types_set = set()
        leave_type_list = frappe.get_list("Leave Allocation", {"employee": employee}, 'leave_type')
        
        if not leave_type_list or len(leave_type_list) == 0:
            return response("Resource Not Found", 404, None, "No leave allocated to {employee}".format(employee=employee_id))
        
        for leave_type in leave_type_list:
            leave_types_set.add(leave_type.leave_type)
        
        return response("Success", 200, list(leave_types_set))
        
    except Exception as error:
        return response("Internal Server Error", 500, None, error)

@frappe.whitelist()
def create_new_leave_application(employee_id: str = None, from_date: str = None, to_date: str = None, leave_type: str = None, reason: str = None) -> dict:
    """[summary]

    Args:
        employee (str): Employee record name.
        from_date (str): Start date => yyyy-mm-dd
        to_date (str): End date => yyyy-mm-dd
        leave_type (str): Type of leave
        reason (str): Reason for leave

    Returns:
        dict: {
            message (str): Brief message indicating the response,
			status_code (int): Status code of response.
            data (dict): Leave application that was created,
            error (str): Any error handled.
        }
    """
    if not employee_id:
        return response("Bad Request", 400, None, "employee_id required.")

    if not from_date:
        return response("Bad Request", 400, None, "from_date required.")

    if not to_date:
        return response("Bad Request", 400, None, "to_date required.")

    if not leave_type:
        return response("Bad Request", 400, None, "leave_type required.")

    if not reason:
        return response("Bad Request", 400, None, "reason required.")

    if not isinstance(employee_id, str):
        return response("Bad Request", 400, None, "employee_id must be of type str")

    if not isinstance(from_date, str):
        return response("Bad Request", 400, None, "from_date must be of type str.")

    if not validate_date(from_date):
        return response("Bad Request", 400, None, "from_date must be of format yyyy-mm-dd.")

    if not validate_date(to_date):
        return response("Bad Request", 400, None, "to_date must be of format yyyy-mm-dd.")

    if not isinstance(to_date, str):
        return response("Bad Request", 400, None, "to_date must be of type str.")

    if not isinstance(leave_type, str):
        return response("Bad Request", 400, None, "leave_type must be of type str.")

    if not isinstance(reason, str):
        return response("Bad Request", 400, None, "reason must be of type str.")

    
    try:
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))
        
        leave_approver = get_leave_approver(employee)
        
        if not leave_approver:
            return response("Resource Not Found", 404, None, "No leave approver found for {employee}.".format(employee=employee_id))
        
        if frappe.db.exists("Leave Application", {'employee': employee,'from_date': ['>=', to_date],'to_date' : ['>=', from_date]}):
            return response("Duplicate", 422, None, "Leave application already created for {employee}".format(employee=employee_id))
        
        
        # Approve leave application for "Sick Leave"
        if str(leave_type).lower() == "sick leave":
            doc = new_leave_application(employee, from_date, to_date, leave_type, "Approved", reason, leave_approver)
            doc.submit()
            frappe.db.commit()
            return response("Success", 201, doc)

        else:
            doc = new_leave_application(employee, from_date, to_date, leave_type, "Open", reason, leave_approver)
            return response("Success", 201, doc)
    
    except Exception as error:
        return response("Internal Server Error", 500, None, error)

def new_leave_application(employee: str, from_date: str,to_date: str,leave_type: str,status:str, reason: str,leave_approver: str) -> dict:
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
    return leave.as_dict()


def get_leave_approver(employee: str) -> str:
    """This function fetches the leave approver for a given employee.
    The leave approver is fetched  either Report_to or Leave Approver. 
    But, if both don't exist, Operation manager is the Leave Approver.

    Args:
        employee (str): The employee record name

    Returns:
        str: user id of leave approver
    """

    leave_approver, reports_to = frappe.db.get_value("Employee", employee, ["leave_approver", "reports_to"])
    if not leave_approver:
        if reports_to:
            return frappe.db.get_value('Employee', {'name': reports_to}, ['user_id'])
        else:
            #if not, return the 'Operational Manager' as the leave approver. But, check if employee himself is not a leave manager.
            operation_manager_name, operation_manager_user_id = frappe.db.get_value('Employee', {'Designation': "Operation Manager"}, ['name','user_id'])
            if operation_manager_name != employee:
                return operation_manager_user_id
    
    return leave_approver