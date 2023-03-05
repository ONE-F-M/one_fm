import frappe
from frappe import _
from one_fm.api.notification import create_notification_log
from one_fm.api.v1.utils import response, validate_date, validate_time
from one_fm.operations.doctype.shift_permission.shift_permission import fetch_approver

@frappe.whitelist()
def create_shift_permission(employee_id: str = None, log_type: str = None, permission_type: str = None, date: str = None,
    reason: str = None, leaving_time: str = None, arrival_time: str = None, latitude: str = None,
    longitude: str = None) -> dict:
    """This method creates a shift permission for a given employee.

    Args:
        employee (str): employee id
        log_type (str): type of log(IN/OUT).
        permission_type (str): type of permission requested.
        date (str): yyyy-mm-dd
        reason (str): reason to create a shift permission
        leaving_time (str): time for leave in hh:mm:ss
        arrival_time (str): time for arriving in hh:mm:ss
        latitude (float, optional): Latitude od user.
        longitude (float, optional): Longitude od user.

    Returns:
        dict: {
            message (str): Brief message indicating the response,
			status_code (int): Status code of response.
            data (dict): shift permission created.
            error (str): Any error handled.
        }
    """

    if not employee_id:
        return response("Bad Request", 400, None, "employee_id required.")

    if not permission_type:
        return response("Bad Request", 400, None, "permission_type required.")

    if not date:
        return response("Bad Request", 400, None, "date required.")

    if not reason:
        return response("Bad Request", 400, None, "reason required.")

    if not log_type:
        if permission_type in ['Arrive Late', 'Forget to Checkin', 'Checkin Issue']:
            log_type='IN'
        elif permission_type in ['Leave Early', 'Forget to Checkout', 'Checkout Issue']:
            log_type='OUT'
        else:
            return response("Bad Request", 400, None, "log_type required.")

    if log_type == "IN" and permission_type not in ['Arrive Late', 'Forget to Checkin', 'Checkin Issue']:
        return response("Bad Request", 400, None, _('Permission Type cannot be {0}. It should be one of \
            "Arrive Late", "Forget to Checkin", "Checkin Issue" for Log Type "IN"'.format(permission_type)))

    if log_type == "OUT" and permission_type not in ['Leave Early', 'Forget to Checkout', 'Checkout Issue']:
        return response("Bad Request", 400, None, _('Permission Type cannot be {0}. It should be one of \
            "Leave Early", "Forget to Checkout", "Checkout Issue" for Log Type "OUT"'.format(permission_type)))

    if permission_type == "Arrive Late" and not arrival_time:
        return response("Bad Request", 400, None, "Arrival time required for late arrival shift permission.")

    if permission_type == "Leave Early" and not leaving_time:
        return response("Bad Request", 400, None, "Leaving time required for early exit shift permission")

    if not isinstance(employee_id, str):
        return response("Bad Request", 400, None, "employee must be of type str.")

    if not isinstance(permission_type, str):
        return response("Bad Request", 400, None, "permission_type must be of type str.")

    if permission_type not in ["Arrive Late", "Leave Early", "Checkin Issue", "Checkout Issue"]:
        return response("Bad Request", 400, None, "permission type must be either 'Arrive Late' or 'Leave Early' or 'Checkin Issue' or 'Checkout Issue'.")

    if permission_type in ["Checkin Issue", "Checkout Issue"] and latitude and longitude:
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except:
            return response("Bad Request", 400, None, "Latitude and longitude must be float.")

    if not isinstance(date, str):
        return response("Bad Request", 400, None, "date must be of type str.")

    if not validate_date(date):
        return response("Bad Request", 400, None, "date must be of type yyyy-mm-dd.")

    if not isinstance(reason, str):
        return response("Bad Request", 400, None, "reason must be of type str.")

    if arrival_time:
        if not isinstance(arrival_time, str):
            return response("Bad Request", 400, None, "arival_time must be of type str.")

        if not validate_time(arrival_time):
            return response("Bad Request", 400, None, "arrival_time must be of type hh:mm:ss.")

    if leaving_time:
        if not isinstance(leaving_time, str):
            return response("Bad Request", 400, None, "leaving_time must be of type str.")

        if not validate_time(leaving_time):
            return response("Bad Request", 400, None, "leaving_time must be of type hh:mm:ss.")

    try:
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))

        shift_details = get_shift_details(employee)

        if shift_details.found:
            shift, shift_type, shift_assignment, shift_supervisor = shift_details.data
        else:
            return response("Resource Not Found", 404, None, "shift not found in employee schedule for {employee}".format(employee=employee))

        if not shift_type:
            return response("Resource Not Found", 404, None, "shift type not found in employee schedule for {employee}".format(employee=employee))

        if not shift_assignment:
            return response("Resource Not Found", 404, None, "shift assingment not found for {employee}".format(employee=employee))

        if not shift_supervisor:
            return response("Resource Not Found", 404, None, "shift supervisor not found for {employee}".format(employee=employee_id))

        if not frappe.db.exists("Shift Permission", {"employee": employee, "date": date, "assigned_shift": shift_assignment, "permission_type": permission_type}):
            shift_permission_doc = frappe.new_doc('Shift Permission')
            shift_permission_doc.employee = employee
            shift_permission_doc.date = date
            shift_permission_doc.log_type = log_type
            shift_permission_doc.permission_type = permission_type
            shift_permission_doc.reason = reason
            if permission_type == "Arrive Late" and arrival_time:
                shift_permission_doc.arrival_time = arrival_time
            if permission_type == "Leave Early" and leaving_time:
                shift_permission_doc.leaving_time = leaving_time
            if permission_type in ["Checkin Issue", "Checkout Issue"]:
                shift_permission_doc.latitude = latitude if latitude else 0.0
                shift_permission_doc.longitude = longitude if longitude else 0.0
            shift_permission_doc.assigned_shift = shift_assignment
            shift_permission_doc.shift_supervisor = shift_supervisor
            shift_permission_doc.shift = shift
            shift_permission_doc.shift_type = shift_type
            shift_permission_doc.save()
            frappe.db.commit()
            return response("Success", 201, shift_permission_doc.as_dict())

        else:
            return response("Duplicate", 422, None, "Shift permission already created for {employee}".format(employee=employee_id))

    except Exception as error:
        return response("Internal Server Error", 500, None, error)


def get_shift_details(employee):
    shift = None
    shift_type = None
    shift_assignment = None
    shift_supervisor = None

    shift_assignment, shift_supervisor, shift, shift_type = fetch_approver(employee)

    if not shift_assignment:
        return frappe._dict({'found':False})

    return frappe._dict({'found':True, 'data':[shift, shift_type, shift_assignment, shift_supervisor]})

@frappe.whitelist()
def list_shift_permission(employee_id: str = None):
    if not employee_id:
        return response("Bad Request", 400, None, "employee_id required.")

    if not isinstance(employee_id, str):
        return response("Bad Request", 400, None, "employee_id must be of type str.")

    try:
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))

        shift_permission_list = frappe.get_list("Shift Permission", filters={'employee': employee}, fields=["name", "date", "workflow_state"])
        return response("Success", 200, shift_permission_list)

    except Exception as error:
        return response("Internal Server Error", 500, None, error)

@frappe.whitelist()
def shift_permission_details(shift_permission_id: str = None):
    if not shift_permission_id:
        return response("Bad Request", 400, None, "shift_permission_id required.")

    if not isinstance(shift_permission_id, str):
        return response("Bad Request", 400, None, "shift_permission_id must be of type str.")

    try:
        shift_permission_doc = frappe.get_doc("Shift Permission", {'name': shift_permission_id})

        if not shift_permission_doc:
            return response("Resource Not Found", 404, None, "Shift permission with {shift_permission_id} not found".format(shift_permission_id=shift_permission_id))

        return response("Success", 200, shift_permission_doc.as_dict())

    except Exception as error:
        return response("Internal Server Error", 500, None, error)

@frappe.whitelist()
def approve_shift_permission(employee_id: str = None, shift_permission_id: str = None):
    if not employee_id:
        return response("Bad Request", 400, None, "employee_id required.")

    if not isinstance(employee_id, str):
        return response("Bad Request", 400, None, "employee_id must be of type str.")

    if not shift_permission_id:
        return response("Bad Request", 400, None, "shift_permission_id required.")

    if not isinstance(shift_permission_id, str):
        return response("Bad Request", 400, None, "shift_permission_id must be of type str.")

    try:
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))

        shift_permission_doc = frappe.get_doc('Shift Permission', shift_permission_id)
        if not shift_permission_doc:
            return response("Resource Not Found", 404, None, "shift permission with {shift_permission_id} not found".format(shift_permission_id=shift_permission_id))

        shift_supervisor = frappe.db.get_value('Shift Permission', {'name': shift_permission_id},['shift_supervisor'])
        if not shift_supervisor:
            return response("Resource Not Found", 404, None, "No shift supervisor found for {shift_permission_id}".format(shift_permission_id=shift_permission_id))

        if shift_supervisor != employee:
            return response("Forbidden", 403, None, "{employee_id} cannot approve this shift permission.".format(employee_id=employee_id))

        if shift_permission_doc.workflow_state == "Pending":
            shift_permission_doc.workflow_state="Approved"
            shift_permission_doc.save()
            frappe.db.commit()

            user_id, supervisor_name = frappe.db.get_value('Employee', {'name': shift_supervisor}, ['user_id', 'employee_name'])
            subject = _("{name} has approved the permission to {type} on {date}.".format(name=supervisor_name, type=shift_permission_doc.permission_type.lower(), date=shift_permission_doc.date))
            message = _("{name} has approved the permission to {type} on {date}.".format(name=supervisor_name, type=shift_permission_doc.permission_type.lower(), date=shift_permission_doc.date))
            notify_for_shift_permission_status(subject, message, user_id, shift_permission_doc, 1)

            return response("Success", 201, shift_permission_doc.as_dict())

        else:
            return response("Bad Request", 400, None, "Shift permission not in 'Pending' state.")

    except Exception as error:
        return response("Internal Server Error", 500, None, error)

@frappe.whitelist()
def reject_shift_permission(employee_id: str = None, shift_permission_id: str = None):
    if not employee_id:
        return response("Bad Request", 400, None, "employee_id required.")

    if not isinstance(employee_id, str):
        return response("Bad Request", 400, None, "employee_id must be of type str.")

    if not shift_permission_id:
        return response("Bad Request", 400, None, "shift_permission_id required.")

    if not isinstance(shift_permission_id, str):
        return response("Bad Request", 400, None, "shift_permission_id must be of type str.")

    try:
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))

        shift_permission_doc = frappe.get_doc('Shift Permission', shift_permission_id)
        if not shift_permission_doc:
            return response("Resource Not Found", 404, None, "shift permission with {shift_permission_id} not found".format(shift_permission_id=shift_permission_id))

        shift_supervisor = frappe.db.get_value('Shift Permission', {'name': shift_permission_id},['shift_supervisor'])
        if not shift_supervisor:
            return response("Resource Not Found", 404, None, "No shift supervisor found for {shift_permission_id}".format(shift_permission_id=shift_permission_id))

        if shift_supervisor != employee:
            return response("Forbidden", 403, None, "{employee_id} cannot approve this shift permission.".format(employee_id=employee_id))

        if shift_permission_doc.workflow_state == "Pending":
            shift_permission_doc.workflow_state="Rejected"
            shift_permission_doc.save()
            frappe.db.commit()

            user_id, supervisor_name= frappe.db.get_value('Employee',{'name':shift_supervisor},['user_id','employee_name'])
            subject = _("{name} has rejected the permission to {type} on {date}.".format(name=supervisor_name, type=shift_permission_doc.permission_type.lower(), date=shift_permission_doc.date))
            message = _("{name} has rejected the permission to {type} on {date}.".format(name=supervisor_name, type=shift_permission_doc.permission_type.lower(), date=shift_permission_doc.date))
            notify_for_shift_permission_status(subject, message,user_id, shift_permission_doc, 1)

            return response("Success", 201, shift_permission_doc.as_dict())

        else:
            return response("Bad Request", 400, None, "Shift permission not in 'Pending' state.")

    except Exception as error:
        return response("Internal Server Error", 500, None, error)


def notify_for_shift_permission_status(subject, message, user, shift_permission_doc, mobile_notification):
    create_notification_log(subject, message, [user], shift_permission_doc, mobile_notification)
