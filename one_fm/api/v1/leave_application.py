from pathlib import Path
import hashlib, base64, json
import frappe
from frappe import _
from datetime import date
import datetime
import collections

from frappe.utils import cint, cstr, getdate, add_months
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on, get_leave_allocation_records, get_leave_details

from one_fm.api.api import upload_file
from one_fm.api.tasks import get_action_user,get_notification_user
from one_fm.api.v1.utils import response, validate_date
from one_fm.utils import (
    get_current_shift, check_if_backdate_allowed,
    get_approver, get_approver_user,
)
from one_fm.api.utils import validate_sick_leave_attachment

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
    try:
        if not employee_id:
            return response("Bad Request", 400, None, "employee_id required.")

        if not isinstance(employee_id, str):
            return response("Bad Request", 400, None, "employee_id must be of type str.")

        if leave_id and not isinstance(leave_id, str):
            return response("Bad Request", 400, None, "leave_id must be of type str.")

        employee = frappe.db.get_value("Employee", {'employee_id':employee_id})

        if not employee:
            return response("Resource Not Found", 404, None, "No employee record found for {employee_id}".format(employee_id=employee_id))

        if not leave_id:
            leave_list = frappe.get_all("Leave Application", {'employee':employee},
                ["name", "leave_type", "status", "from_date", "total_leave_days", "leave_approver", "posting_date"])
            if leave_list and len(leave_list) > 0:
                return response("Success", 200, leave_list)
            else:
                return response("Resource Not Found", 404, None, "No leaves found for {employee_id}".format(employee_id=employee_id))

        elif leave_id:
            leave_details = frappe.get_doc("Leave Application", leave_id)
            if leave_details.leave_approver == frappe.session.user:
                is_leave_approver = 1
            else:
                is_leave_approver = 0
            data = leave_details.as_dict()
            data.update({"is_leave_approver":is_leave_approver})

            if leave_details:
                return response("Success", 200, data)
            else:
                return response("Resource Not Found", 404, None, "No leave data found for {leave_id}".format(leave_id=leave_id))

    except Exception as error:
        frappe.log_error(title="API Leave Detail", message=frappe.get_traceback())
        return response("Internal Server Error", 500, None, error)

@frappe.whitelist()
def approver_leave() -> dict:
    """This method gets the list of leave application, where the current user is the leave approver.

    Returns:
        dict: {
            message (str): Brief message indicating the response,
			status_code (int): Status code of response.
            data (dict): list of leave application,
            error (str): Any error handled.
        }
    """

    try:
        leave_data = frappe.get_all("Leave Application", filters={'leave_approver':frappe.session.user}, fields=["name","leave_type", "status","from_date", "total_leave_days"] )

        if leave_data:
            return response("Success", 200, leave_data)
        else:
            return response("Resource Not Found", 404, None, "No leave data found")

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

    # if not leave_type:
    #     return response("Bad Request", 400, None, "leave_type required.")

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
        leave_type = leave_type.title()
        if allocation_records["leave_allocation"]:
            if leave_type:
                if allocation_records["leave_allocation"].get(leave_type):
                    leave_balance = allocation_records['leave_allocation'][leave_type]
                    leave_balance['leave_type'] = leave_type
                    return response("Success", 200, leave_balance)
                else:
                    response("Resource Not Found", 404, None, "No {leave_type} allocated to {employee}".format(
                        employee=employee_id, leave_type=leave_type))
            else:
                leave_balance = allocation_records['leave_allocation']
                return response("Success", 200, leave_balance)
        else:
            return response("Resource Not Found", 404, None, "No allocated to {employee}".format(
                employee=employee_id))

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
def create_new_leave_application(employee_id: str = None, from_date: str = None, 
    to_date: str = None, leave_type: str = None, reason: str = None, proof_document = {}) -> dict:
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
    try:
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

        if proof_document_required_for_leave_type(leave_type) and not proof_document:
            return response("Bad Request", 400, None, "Leave type requires a proof_document.")

        if not check_if_backdate_allowed(leave_type, from_date):
            return response("Bad Request", 400, None, "You are not allowed to apply for later or previous date.")
        

        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})
        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))

        leave_approver = frappe.db.get_value("Employee", get_approver(employee), "user_id")
        if not leave_approver:
            return response("Resource Not Found", 404, None, "No leave approver found for {employee}.".format(employee=employee_id))

        if frappe.db.exists("Leave Application", {'employee': employee,'from_date': ['BETWEEN', [from_date, to_date]],'to_date' : ['BETWEEN', [from_date, to_date]]}):
            return response("Duplicate", 422, None, "Leave application already created for {employee}".format(employee=employee_id))

        if proof_document_required_for_leave_type(leave_type):
            if not proof_document:
                return response("Missing", 400, None, "Proof document is required for {leave_type}".format(leave_type=leave_type))
            proof_doc_json = json.loads(proof_document)[0]
            attachment = proof_doc_json.get('attachment')
            attachment_name = proof_doc_json.get('attachment_name')
            if not attachment or not attachment_name:
                return response('proof_document key requires attachment and attachment_name', {}, 400)

            file_ext = "." + attachment_name.split(".")[-1]
            content = base64.b64decode(attachment)
            filename = hashlib.md5((attachment_name + str(datetime.datetime.now())).encode('utf-8')).hexdigest() + file_ext
            doc = new_leave_application(employee, from_date, to_date, leave_type, "Open", reason, leave_approver, {
                'description':filename,
                'attachments':content
            })
        else:
            doc = new_leave_application(employee, from_date, to_date, leave_type, "Open", reason, leave_approver)
        return response("Success", 201, doc)
    except Exception as error:
        frappe.log_error(message=frappe.get_traceback(), title='Leave API')
        return response("Internal Server Error", 500, None, error)
    
def new_leave_application(employee: str, from_date: str,to_date: str,leave_type: str,status:str, reason: str,leave_approver: str, attachments = {}) -> dict:
    leave = frappe.new_doc("Leave Application")
    leave.employee=employee
    leave.leave_type=leave_type
    leave.from_date=from_date
    leave.to_date=to_date
    leave.source = 'V1'
    leave.description=reason or "None"
    leave.follow_via_email=1
    leave.status=status
    leave.leave_approver = leave_approver
    leave.leave_approver_name = frappe.db.get_value("User", leave_approver, 'full_name')
    leave.save(ignore_permissions=True)
    if attachments:
        _file = upload_file(leave, "", attachments['description'], "", attachments['attachments'], is_private=True)
        leave.append('proof_documents', {'description':attachments['description'], 
            "attachments":_file.file_url})
        leave.save()
    # add the files to File doctype
    return leave.as_dict()

@frappe.whitelist()
def fetch_leave_approver(employee: str) -> str:
    """This function fetches the leave approver for a given employee.
    The leave approver is fetched  either Report_to or Leave Approver.
    But, if both don't exist, Operation manager is the Leave Approver.

    Args:
        employee (str): The employee record name

    Returns:
        str: user id of leave approver
    """
    employee_details = frappe.db.get_list("Employee", {"name":employee}, ["reports_to", "department"])
    reports_to = employee_details[0].reports_to
    department = employee_details[0].department
    employee_shift = frappe.get_list("Shift Assignment",fields=["*"],filters={"employee":employee}, order_by='creation desc',limit_page_length=1)
    if reports_to:
        approver = frappe.get_value("Employee", reports_to, ["user_id"])
    elif len(employee_shift) > 0 and employee_shift[0].shift:
        approver, Role = get_action_user(employee,employee_shift[0].shift)
    else:
        approvers = frappe.db.sql(
				"""select approver from `tabDepartment Approver` where parent= %s and parentfield = 'leave_approvers'""",
				(department),
			)
        approvers = [approver[0] for approver in approvers]
        approver = approvers[0]
    return approver


def proof_document_required_for_leave_type(leave_type):
    if int(frappe.db.get_value("Leave Type", {'name': leave_type}, "is_proof_document_required")):
        return True

    return False

@frappe.whitelist()
def leave_approver_action(leave_id: str,status: str) -> dict:
    try:
        doc = frappe.get_doc("Leave Application",{"name":leave_id})
        doc.status = status
        doc.submit()
        frappe.db.commit()
        return response("Success", 201, doc)
        #return response('Leave Application was'+status,doc, 201)
    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        frappe.respond_as_web_page(_("Error"), e , http_status_code=417)

@frappe.whitelist()
def leave_application_list(
        employee_id: str, from_date: str = None, to_date: str = None,
        leave_type: str = None,
        status: str = None) -> dict:
    """
    this method retrived list of leave application for both employee and reports to
    """
    try:
        if not employee_id:
            return response("error", 400, {}, "Employee ID is required.")
        employee = frappe.get_value("Employee", {"employee_id": employee_id}, ["name", "user_id"], as_dict=1)
        if not employee:
            return response("error", 404, {}, "Employee not found.")
        
        if not(from_date and to_date):
            posting_date = ["BETWEEN", [add_months(getdate(), -2), getdate()]]
        else:
            posting_date = ["BETWEEN", [from_date, to_date]]

        extra_filters = {}
        if leave_type:
            extra_filters["leave_type"] = leave_type
        if status:
            extra_filters["status"] = status


        my_leaves_query = frappe.get_all("Leave Application", 
            filters = {**{
                "employee": employee.name,
                "posting_date": posting_date
            }, **extra_filters},
            fields=["*"]
        )
        my_leaves = [{
            "name":i.name,"employee_name":i.employee_name, "workflow_state":i.workflow_state,
            "leave_type":i.leave_type, "total_leave_days":i.total_leave_days,
            "posting_date":i.posting_date, "from_date":i.from_date, "to_date":i.to_date, 
            "leave_approver_name":i.leave_approver_name, "description":i.description, 
            "proof_documents":i.proof_documents or []
            } for i in my_leaves_query
        ]
        reports_to_query = frappe.get_all("Leave Application", 
            filters = {**{
                "leave_approver": employee.user_id,
                "posting_date": posting_date,
            }, **extra_filters},
            fields=["*"]
        )
        reports_to = [{
            "name":i.name,"employee_name":i.employee_name, "workflow_state":i.workflow_state,
            "leave_type":i.leave_type, "total_leave_days":i.total_leave_days,
            "posting_date":i.posting_date, "from_date":i.from_date, "to_date":i.to_date, 
            "leave_approver_name":i.leave_approver_name, "description":i.description, 
            "proof_documents":clean_proof_documents(i.proof_documents)
            } for i in reports_to_query
        ]
        return response("success", 200, {"my_leaves":my_leaves, "reports_to": reports_to})
    except Exception as e:
        return response("error", 500, {}, str(frappe.get_traceback()))

def clean_proof_documents(proof_documents):
    """
    This filters out attachments
    """
    if proof_documents:
        attachments = [i.attachments for i in proof_documents]
    else:
        attachments = []
    return attachments

