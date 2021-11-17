import frappe
from frappe import _
from one_fm.api.notification import create_notification_log

# This method is creating overtime request record and setting the the shift details
@frappe.whitelist()
def create_overtime_request(employee, request_type, date, start_time=None, end_time=None, shift=None, post_type=None):
    """
        Params:
            employee: Employee ID in ERP
            request_type: 'Head Office' or 'Operations'
        Return: Overtime Request record
    """
    try:
        doc = frappe.new_doc('Overtime Request')
        doc.employee = employee
        doc.date = date
        doc.request_type = request_type
        doc.start_time = start_time
        doc.end_time = end_time
        doc.shift = shift
        doc.post_type = post_type
        doc.save()
        frappe.db.commit()
        return response("Overtime Request Successfully Created", doc, True, 201)

    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        return response(e, {}, False, 500)


@frappe.whitelist()
def get_overtime_request_list(employee, status=None, owner=None):
    """
        This function allows you to fetch the list of overtime request of a given employee.
        params:
            employee (eg: HR-EMP-00001)
            status: None or 'Draft' or 'Pending' or 'Accepted' or 'Rejected'
            owner: User, who created the overtime request
        returns: List of overtime request with name, date and workflow_state of the doc.
    """
    try:
        filters = {'employee':employee}
        if status:
            filters['status'] = status
        if owner:
            filters['owner'] = owner
        return frappe.get_list("Overtime Request", filters=filters, fields=["name", "date", "workflow_state"])
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_overtime_request(overtime_request):
    '''
        This function allows you to fetch the details of a given Shift Permission.
        params: overtime_request: Overtime Request (eg: OT-HO-.HR-EMP-00001.-00001)
        returns: Details of Overtime Request as a doc.
    '''
    try:
        return frappe.get_doc("Overtime Request", overtime_request)
    except Exception as e:
        return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def employee_accept_or_reject_overtime_request(employee, overtime_request_id, workflow_state):
    """
        This function allows Employee to Accept the Overtime Request and notify the owner.
        params:
            employee (eg: HR-EMP-00001)
            overtime_request_id (eg: OT-HO-.HR-EMP-00001.-00001)
            workflow_state : 'Request Accepted', 'Request Rejected'
        returns: Message & workflow of the document
    """
    try:
        overtime_request = frappe.get_doc('Overtime Request', overtime_request_id)
        if workflow_state not in ['Request Accepted', 'Request Rejected']:
            return response("{0} can not {1}".format(overtime_request.employee_name, workflow_state), {}, False, 400)

        if overtime_request.employee != employee:
            return response("Only {0} Has The Right to Accept".format(overtime_request.employee_name), {}, False, 400)

        if overtime_request.workflow_state == workflow_state:
            return response("Overtime {0} Already !".format(workflow_state), {}, False, 400)

        if overtime_request.workflow_state == "Pending":
            overtime_request.workflow_state = workflow_state
            overtime_request.save()
            frappe.db.commit()

            subject = _("{0} {1} Overtime Request {2}".format(overtime_request.employee_name, status, overtime_request.name))
            message = subject + _(" dated {0}.".format(overtime_request.date))

            create_notification_log(subject, message, [overtime_request.owner], overtime_request, True)

            return response("Overtime {0} Successfully".format(workflow_state), {overtime_request.workflow_state}, True, 200)

    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        return response(e, {}, False, 500)

# This method returing the message and status code of the API
def response(message, data, success, status_code):
    """
        Params: message, status code
    """
    frappe.local.response["message"] = message
    frappe.local.response["data"] = data
    frappe.local.response["success"] = success
    frappe.local.response["http_status_code"] = status_code
    return
