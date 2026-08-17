from pathlib import Path
import hashlib, base64, json
import frappe
from frappe import _
from datetime import date
import datetime
import collections

from frappe.utils import cint, cstr, getdate, add_months, add_days, strip_html
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on, get_leave_allocation_records, get_leave_details

from one_fm.api.api import upload_file
from one_fm.api.tasks import get_action_user,get_notification_user
from one_fm.api.v1.utils import response, validate_date
from one_fm.utils import check_if_backdate_allowed, get_approver, get_approver_user
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
            return response(_("Missing Employee ID"), 400, None,
                            _("Please enter your Employee ID."))

        if not isinstance(employee_id, str):
            return response(_("Invalid Employee ID"), 400, None,
                            _("Please enter a valid Employee ID."))

        if leave_id and not isinstance(leave_id, str):
            return response(_("Invalid Leave ID"), 400, None,
                            _("Please select a valid leave application."))

        employee = frappe.db.get_value("Employee", {'employee_id':employee_id})

        if not employee:
            return response(_("Employee Not Found"), 404, None,
                            _("No employee record found for Employee ID {0}. "
                              "Please contact the IT Helpdesk.").format(employee_id))

        if not leave_id:
            leave_list = frappe.get_all("Leave Application", {'employee':employee},
                ["name", "leave_type", "status", "from_date", "total_leave_days", "leave_approver", "posting_date"])
            if leave_list and len(leave_list) > 0:
                return response("Success", 200, leave_list)
            else:
                return response(_("No Leave Applications"), 404, None,
                                _("You have not applied for any leave yet."))

        elif leave_id:
            if not frappe.db.exists("Leave Application", leave_id):
                return response(_("Leave Not Found"), 404, None,
                                _("This leave application no longer exists. "
                                  "Please refresh and try again."))

            leave_details = frappe.get_doc("Leave Application", leave_id)
            if leave_details.leave_approver == frappe.session.user:
                is_leave_approver = 1
            else:
                is_leave_approver = 0
            data = leave_details.as_dict()

            for d in data.proof_documents:
                filename = frappe.get_value("File",{'file_url':d.attachments},['file_name'])
                d.update({"file_name":filename})
            data.update({"is_leave_approver":is_leave_approver})

            return response("Success", 200, data)

    except Exception as error:
        frappe.log_error(
            title=f"Mobile API: leave_application.get_leave_detail | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(error)) or type(error).__name__)

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
        return response(_("Missing Employee ID"), 400, None,
                        _("Please enter your Employee ID."))

    if not isinstance(employee_id, str):
        return response(_("Invalid Employee ID"), 400, None,
                        _("Please enter a valid Employee ID."))

    if leave_type is not None and not isinstance(leave_type, str):
        return response(_("Invalid Leave Type"), 400, None,
                        _("Please select a valid leave type."))

    today=date.today()

    try:
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response(_("Employee Not Found"), 404, None,
                            _("No employee record found for Employee ID {0}. "
                              "Please contact the IT Helpdesk.").format(employee_id))

        allocation_records = get_leave_details(employee, today)

        if leave_type:
            leave_type = leave_type.title()

        if allocation_records["leave_allocation"]:
            if leave_type:
                if allocation_records["leave_allocation"].get(leave_type):
                    leave_balance = allocation_records['leave_allocation'][leave_type]
                    leave_balance['leave_type'] = leave_type
                    return response("Success", 200, leave_balance)
                else:
                    return response(_("No Leave Balance"), 404, None,
                                    _("You have no {0} allocated. Please contact HR.").format(leave_type))
            else:
                leave_balance = allocation_records['leave_allocation']
                return response("Success", 200, leave_balance)
        else:
            return response(_("No Leave Allocation"), 404, None,
                            _("You have no leave allocated for this period. Please contact HR."))

    except Exception as error:
        frappe.log_error(
            title=f"Mobile API: leave_application.get_leave_balance | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(error)) or type(error).__name__)

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
        return response(_("Missing Employee ID"), 400, None,
                        _("Please enter your Employee ID."))

    if not isinstance(employee_id, str):
        return response(_("Invalid Employee ID"), 400, None,
                        _("Please enter a valid Employee ID."))

    try:
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response(_("Employee Not Found"), 404, None,
                            _("No employee record found for Employee ID {0}. "
                              "Please contact the IT Helpdesk.").format(employee_id))

        leave_types_set = set()
        leave_type_list = frappe.get_list("Leave Allocation", {"employee": employee}, 'leave_type')

        if not leave_type_list or len(leave_type_list) == 0:
            return response(_("No Leave Allocation"), 404, None,
                            _("You have no leave allocated for this period. Please contact HR."))

        leave_types = frappe.get_all("Leave Type", fields=["name", "is_proof_document_required"])
        leave_types_dict = {}
        for i in leave_types:
            leave_types_dict[i.name] = i.is_proof_document_required
        leave_type_documents = {}
        for leave_type in leave_type_list:
            if leave_type.leave_type in leave_types_dict:
                leave_type_documents[leave_type.leave_type] = leave_types_dict[leave_type.leave_type]
        return response("Success", 200, leave_type_documents)

    except Exception as error:
        frappe.log_error(
            title=f"Mobile API: leave_application.get_leave_types | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(error)) or type(error).__name__)


@frappe.whitelist()
def get_employees_role_to_display_reliever_field(employee_id: str = None)-> dict:
    try:
        employee = frappe.get_value("Employee", {"employee_id": employee_id}, ["name", "user_id", "reports_to"], as_dict=1)
        if not employee:
            return response(_("Employee Not Found"), 404, None,
                            _("No employee record found for Employee ID {0}. "
                              "Please contact the IT Helpdesk.").format(employee_id))

        super_user_role = frappe.db.get_single_value("ONEFM General Setting", "super_user_role")
        user_roles = frappe.get_roles(employee.user_id)
        if (employee.reports_to or (super_user_role in user_roles)):
            return response("Success", 200, True)
        return response("Success", 200, False)
    except Exception as error:
        frappe.log_error(
            title=f"Mobile API: leave_application.get_employees_role_to_display_reliever_field | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(error)) or type(error).__name__)



@frappe.whitelist()
def get_employees_list():
    try:
        super_user_role = frappe.db.get_single_value("ONEFM General Setting", "super_user_role")
        users_with_role = frappe.get_all("Has Role",filters={"role": super_user_role, "parenttype": "User"},fields=["parent as user_name"])
        user_names = [user["user_name"] for user in users_with_role]
        employees_with_role = frappe.get_all("Employee",filters={"status": "Active", "user_id": ["in", user_names]},fields=["employee_id", "employee_name", "designation","employee"])
        employees = frappe.get_all("Employee",filters={"status": "Active","reports_to": ["is", "set"]},fields=["employee_id", "employee_name", "designation","employee"])
        for employee in employees_with_role:
            if employee not in employees:
                employees.append(employee)
        return response("Success", 200, employees)
    except Exception as error:
        frappe.log_error(
            title=f"Mobile API: leave_application.get_employees_list | {frappe.session.user}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(error)) or type(error).__name__)

@frappe.whitelist()
def create_new_leave_application(employee_id: str = None, from_date: str = None, 
    to_date: str = None, leave_type: str = None, reason: str = None, proof_document = {},reliever:str=None, resumption_date: str = None) -> dict:
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
            return response(_("Missing Employee ID"), 400, None,
                            _("Please enter your Employee ID."))

        if not from_date:
            return response(_("Missing Start Date"), 400, None,
                            _("Please select the first day of your leave."))

        if not to_date:
            return response(_("Missing End Date"), 400, None,
                            _("Please select the last day of your leave."))

        if not leave_type:
            return response(_("Missing Leave Type"), 400, None,
                            _("Please select a leave type."))

        if not reason:
            return response(_("Missing Reason"), 400, None,
                            _("Please enter a reason for your leave."))

        if not isinstance(employee_id, str):
            return response(_("Invalid Employee ID"), 400, None,
                            _("Please enter a valid Employee ID."))

        if not isinstance(from_date, str) or not validate_date(from_date):
            return response(_("Invalid Start Date"), 400, None,
                            _("Please select a valid start date."))

        if not isinstance(to_date, str) or not validate_date(to_date):
            return response(_("Invalid End Date"), 400, None,
                            _("Please select a valid end date."))

        if getdate(from_date) > getdate(to_date):
            return response(_("Invalid Date Range"), 400, None,
                            _("The start date cannot be after the end date."))

        if not resumption_date:
            resumption_date = cstr(add_days(getdate(to_date), 1))
        elif not isinstance(resumption_date, str):
            return response(_("Invalid Resumption Date"), 400, None,
                            _("Please select a valid resumption date."))
        if not validate_date(resumption_date):
            return response(_("Invalid Resumption Date"), 400, None,
                            _("Please select a valid resumption date."))

        if not isinstance(leave_type, str):
            return response(_("Invalid Leave Type"), 400, None,
                            _("Please select a valid leave type."))

        if not isinstance(reason, str):
            return response(_("Invalid Reason"), 400, None,
                            _("Please enter a valid reason for your leave."))

        if not frappe.db.exists("Leave Type", leave_type):
            return response(_("Invalid Leave Type"), 400, None,
                            _("The leave type you selected is no longer available. "
                              "Please choose another."))

        if proof_document_required_for_leave_type(leave_type) and not proof_document:
            return response(_("Proof Document Required"), 400, None,
                            _("{0} requires a supporting document. "
                              "Please attach one and try again.").format(leave_type))

        if not check_if_backdate_allowed(leave_type, from_date):
            return response(_("Backdated Leave Not Allowed"), 400, None,
                            _("{0} cannot be applied for a past date. "
                              "Please contact HR if you need to record it.").format(leave_type))
        

        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})
        if not employee:
            return response(_("Employee Not Found"), 404, None,
                            _("No employee record found for Employee ID {0}. "
                              "Please contact the IT Helpdesk.").format(employee_id))

        leave_approver = frappe.db.get_value("Employee", get_approver(employee), "user_id")
        if not leave_approver:
            return response(_("No Leave Approver"), 404, None,
                            _("No leave approver is set up for your record. Please contact HR."))

        if frappe.db.exists("Leave Application", {'employee': employee,'from_date': ['BETWEEN', [from_date, to_date]],'to_date' : ['BETWEEN', [from_date, to_date]]}):
            return response(_("Leave Already Applied"), 422, None,
                            _("You have already applied for leave covering these dates."))

        if proof_document_required_for_leave_type(leave_type):
            if not proof_document:
                return response(_("Proof Document Required"), 400, None,
                                _("{0} requires a supporting document. "
                                  "Please attach one and try again.").format(leave_type))

            if isinstance(proof_document, dict) :
                attachment = proof_document.get('attachment')
                attachment_name = proof_document.get('attachment_name')
            else:
                try:
                    proof_doc_json = json.loads(proof_document)
                    if isinstance(proof_doc_json, list):
                        proof_doc_json = proof_doc_json[0]
                except:
                    proof_doc_json = {}
                attachment = proof_doc_json.get('attachment')
                attachment_name = proof_doc_json.get('attachment_name')
            if not attachment or not attachment_name:
                return response(_("Invalid Attachment"), 400, None,
                                _("Your document could not be read. Please attach it again."))

            file_ext = "." + attachment_name.split(".")[-1]
            content = base64.b64decode(attachment)
            filename = hashlib.md5((attachment_name + str(datetime.datetime.now())).encode('utf-8')).hexdigest() + file_ext
            doc = new_leave_application(employee, from_date, to_date, leave_type, "Open", reason, leave_approver,reliever, {
                'attachment_name':attachment_name,
                'attachment_hashed_name':filename,
                'attachment_file':content
            }, resumption_date=resumption_date)
        else:
            doc = new_leave_application(employee, from_date, to_date, leave_type, "Open", reason, leave_approver,reliever, resumption_date=resumption_date)
        return response("Success", 201, doc)
    except Exception as error:
        frappe.log_error(
            title=f"Mobile API: leave_application.create_new_leave_application | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(error)) or type(error).__name__)
    
def new_leave_application(employee: str, from_date: str,to_date: str,leave_type: str,status:str, reason: str,leave_approver: str,reliever:str, attachments = {}, resumption_date: str = None) -> dict:
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
    leave.custom_reliever_ = reliever
    leave.resumption_date = resumption_date
    leave.leave_approver_name = frappe.db.get_value("User", leave_approver, 'full_name')
    leave.save(ignore_permissions=True)
    if reliever:
        leave.workflow_state = "Pending Reliever"
    else:
        leave.workflow_state = "Pending Approver"
    frappe.db.commit()
    if attachments:
        _file = upload_file(leave, "", attachments['attachment_hashed_name'], "", attachments['attachment_file'], is_private=True)
        leave.append('proof_documents', {'description':attachments['attachment_name'], 
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
    approver = get_approver_user(employee)
    return approver


def proof_document_required_for_leave_type(leave_type):
    if int(frappe.db.get_value("Leave Type", {'name': leave_type}, "is_proof_document_required")):
        return True

    return False

@frappe.whitelist()
def leave_approver_action(leave_id: str,status: str) -> dict:
    try:
        if not frappe.db.exists("Leave Application", leave_id):
            return response(_("Leave Not Found"), 404, None,
                            _("This leave application no longer exists. "
                              "Please refresh and try again."))

        doc = frappe.get_doc("Leave Application",{"name":leave_id})
        has_leave_approver_role = "Leave Approver" in frappe.get_roles(frappe.session.user)

        if not has_leave_approver_role:
            return response(_("Not Allowed"), 403, None,
                            _("You do not have permission to approve or reject leave applications."))
        
        if doc:
            if not doc.leave_approver in [frappe.session.user, 'administrator']:
                return response(_("Not Allowed"), 401, None,
                                _("You are not the assigned approver for this leave application."))
            if status == "Approved":
                doc.status = status
                doc.save()
            elif status == "Rejected":
                doc.db_set('status', 'Rejected')
                doc.db_set('workflow_state', 'Rejected')
                doc.reload()
            else:
                return response(_("Invalid Action"), 400, None,
                                _("Please choose either Approve or Reject."))
        else:
            return response(_("Leave Not Found"), 404, None,
                            _("This leave application no longer exists. "
                              "Please refresh and try again."))
        doc.submit()
        frappe.db.commit()
        return response("Success", 201, doc)
    except Exception as e:
        frappe.log_error(
            title=f"Mobile API: leave_application.leave_approver_action | {leave_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(e)) or type(e).__name__)

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
            return response(_("Missing Employee ID"), 400, None,
                            _("Please enter your Employee ID."))
        employee = frappe.get_value("Employee", {"employee_id": employee_id}, ["name", "user_id"], as_dict=1)
        if not employee:
            return response(_("Employee Not Found"), 404, None,
                            _("No employee record found for Employee ID {0}. "
                              "Please contact the IT Helpdesk.").format(employee_id))
        
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
        frappe.log_error(
            title=f"Mobile API: leave_application.leave_application_list | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(e)) or type(e).__name__)

def clean_proof_documents(proof_documents):
    """
    This filters out attachments
    """
    if proof_documents:
        attachments = [i.attachments for i in proof_documents]
    else:
        attachments = []
    return attachments

@frappe.whitelist()
def fetch_proof_document(file_name: str, docname: str, doctype: str) -> dict:
    try:
        if not frappe.db.exists("File", {"attached_to_name":docname, "attached_to_doctype":doctype, 'file_name':file_name}):
            return response(_("Document Not Found"), 404, None,
                            _("This document is no longer available. It may have been removed."))

        file_doc = frappe.get_doc("File",{"attached_to_name":docname, "attached_to_doctype":doctype, 'file_name':file_name})
        content = frappe.get_doc("File", file_doc.name).get_content()
        base64EncodedStr = base64.b64encode(content).decode('utf-8')
        data = {
            "file_url": file_doc.file_url,
            "file_type":  file_doc.file_type,
            "content": base64EncodedStr,
        }
        return response("Success", 200, data)
    except Exception as e:
        frappe.log_error(
            title=f"Mobile API: leave_application.fetch_proof_document | {docname}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(e)) or type(e).__name__)
