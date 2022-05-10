import frappe
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on, get_leave_allocation_records, get_leave_details
from datetime import date
import datetime
import collections
from one_fm.api.tasks import get_action_user,get_notification_user
import base64, json
from frappe.utils import getdate

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
    try:
        doc = frappe.get_doc("Leave Application",{"name":docname})
        doc.status=status
        doc.save()
        doc.submit()
        frappe.db.commit()
        frappe.respond_as_web_page(_("Success"), _("Leave Application "+docname+" was "+status), http_status_code=201)
        #return response('Leave Application was'+status,doc, 201)
    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        frappe.respond_as_web_page(_("Error"), e , http_status_code=417)

#This function is the api to create a new leave notification.
#bench execute --kwargs "{'employee':'HR-EMP-00002','from_date':'2021-11-17','to_date':'2021-11-17','leave_type':'Annual Leave','reason':'fever'}"  one_fm.api.mobile.Leave_application.create_new_leave_application
@frappe.whitelist()
def create_new_leave_application(employee,from_date,to_date,leave_type,reason, proof_document = {}):
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
    from pathlib import Path
    import hashlib
    #get Leave Approver of the employee.
    leave_approver = get_leave_approver(employee)
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    #check if leave exist and overlaps with the given date (StartDate1 <= EndDate2) and (StartDate2 <= EndDate1)
    leave_exist = frappe.get_list("Leave Application", filters={"employee": employee,'from_date': ['>=', to_date],'to_date' : ['>=', from_date]}, ignore_permissions=True)
    # Return response status 400, if the leave exists.
    if leave_exist:
        return response('You have already applied leave for this date.',[], 400)

    if proof_document_required_for_leave_type(leave_type) and not proof_document:
        return response('Leave type requires a proof_document.', {}, 400)

    if leave_approver:
        try:
            attachment_path = None
            if proof_document_required_for_leave_type(leave_type):
                proof_doc_json = json.loads(proof_document)
                attachment = proof_doc_json['attachment']
                attachment_name = proof_doc_json['attachment_name']

                if not attachment or not attachment_name:
                    return response('proof_document key requires attachment and attachment_name', {}, 400)

                file_ext = "." + attachment_name.split(".")[-1]
                content = base64.b64decode(attachment)
                filename = hashlib.md5((attachment_name + str(datetime.datetime.now())).encode('utf-8')).hexdigest() + file_ext

                Path(frappe.utils.cstr(frappe.local.site)+f"/public/files/leave-application/{frappe.session.user}").mkdir(parents=True, exist_ok=True)
                OUTPUT_FILE_PATH = frappe.utils.cstr(frappe.local.site)+f"/public/files/leave-application/{frappe.session.user}/{filename}"
                with open(OUTPUT_FILE_PATH, "wb") as fh:
                    fh.write(content)

                attachment_path = f"/files/leave-application/{frappe.session.user}/{filename}"

            #if sick leave, automatically accept the leave application
            if leave_type == "Sick Leave":
                doc = new_leave_application(employee,from_date,to_date,leave_type,"Approved",reason,leave_approver, attachment_path)
                doc.submit()
                frappe.db.commit()
            #else keep it open and that sends the approval notification to the 'leave approver'.
            else:
                doc = new_leave_application(employee,from_date,to_date,leave_type,"Open",reason,leave_approver, attachment_path)
            return response('Success',doc, 201)
        except Exception as e:
            frappe.log_error(frappe.get_traceback())
            return response(e,[], 500)
    else:
        return response("You don't have a leave approver.",[], 400)

#create new leave application doctype
def new_leave_application(employee,from_date,to_date,leave_type,status,reason,leave_approver, attachment_path = None):
    leave = frappe.new_doc("Leave Application")
    leave.employee=employee
    leave.leave_type=leave_type
    leave.from_date=from_date
    leave.to_date=to_date
    leave.description=reason or "None"
    leave.follow_via_email=1
    leave.status=status
    leave.leave_approver = leave_approver
    if attachment_path:
        leave.proof_document = attachment_path
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

def proof_document_required_for_leave_type(leave_type):
    if int(frappe.db.get_value("Leave Type", {'name': leave_type}, "is_proof_document_required")):
        return True

    return False
