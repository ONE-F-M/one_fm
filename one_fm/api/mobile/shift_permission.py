import frappe
from frappe import _
from one_fm.api.notification import create_notification_log

# This method is creating shift permission record and setting the the shift details
@frappe.whitelist()
def create_shift_permission(employee, permission_type, date, reason, leaving_time=None, arrival_time=None):
    """
	Params:
	employee: HO employee ERP id
    permission_type, date, reason, leaving_time, arrival_time
    Return: shift permission record
	"""
    try:
        shift, type, assigned_shift, shift_supervisor = get_shift_details(employee,date)
        if shift and type and assigned_shift and shift_supervisor:
            has_duplicate= validate_record(employee, date, assigned_shift, permission_type)
            if not has_duplicate:
                doc = frappe.new_doc('Shift Permission')
                doc.employee = employee
                doc.date = date
                doc.permission_type = permission_type
                doc.reason = reason
                if permission_type == "Arrive Late" and arrival_time:
                    doc.arrival_time = arrival_time
                if permission_type == "Leave Early" and leaving_time:
                    doc.leaving_time = leaving_time
                doc.assigned_shift = assigned_shift
                doc.shift_supervisor = shift_supervisor
                doc.shift = shift
                doc.shift_type = type
                doc.save()
                frappe.db.commit()
                return response({'message':"Shift Permission Successfully Created",'data':doc},201)
            elif has_duplicate:
                doc = frappe.get_doc('Shift Permission',{"employee": employee, "date":date, "assigned_shift": assigned_shift, "permission_type": permission_type})
                return response({'message':"{0} has already applied for permission to {1} on {2}.".format(doc.emp_name, permission_type.lower(), date),'data':{}},409)

        elif not shift or not type or not assigned_shift or not shift_supervisor:
            return response({'message':"Shift Details are missing, Please Make sure You are have a Scheduled record on {0}".format(date),'data':{}},400)
           
    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        return response({'message':"Shift Permission Not Created Successfully",'data':{}},500)

# This method validates any duplicate permission for the employee on same day
def validate_record(employee, date, assigned_shift, permission_type):
    if frappe.db.exists("Shift Permission", {"employee": employee, "date":date, "assigned_shift": assigned_shift, "permission_type": permission_type}):
        return True
    else:
        return False 

# Fetching shift details of the employee and adding them in shift permission record
def get_shift_details(employee, date):
    shift, type = frappe.db.get_value('Employee Schedule',{'employee':employee,'employee_availability':'Working','date':date,'roster_type':'Basic'},['shift','shift_type']) 
    if shift and type:
        shift_supervisor = frappe.db.get_value('Operations Shift',{'name':shift},['supervisor'])
        assigned_shift = frappe.db.get_value('Shift Assignment',{'employee':employee,'start_date':date},['name']) # start date and end date of HO employee are the same in the shift assignment
        if not assigned_shift:
            return response({'message':"You Don't Have Shift Assignment on {date}".format(date=date),'data':{}},400)
        elif assigned_shift:
            return shift, type, assigned_shift, shift_supervisor
    elif not shift and not type:
        return response({'message':"You Don't Have Shift on {date}".format(date=date),'data':{}},400)
        
# This method is returning employee roles upon employee_id
@frappe.whitelist()
def get_employee_roles(employee_id):
    """
	Params:
	employee: employee ERP id
    Returns: roles of employee
	"""
    user_id = frappe.db.get_value('Employee',{'name':employee_id},['user_id'])
    user_roles = frappe.get_roles(user_id)
    return response({'messages':"Roles Are Successfully Listed ",'data':user_roles},200)

# This function allows you to fetch the list of Shift Permission of a given employee.
# params: employee_ID (eg: HR-EMP-00001)
# returns: List of shift Permission with name, date and workflow_state of the doc.
@frappe.whitelist()
def list_shift_permission(employee_id):
    try:
        shift_permission = frappe.get_list("Shift Permission", filters={'employee':employee_id}, fields=["name","date","workflow_state"])
        return shift_permission
    except Exception as e:
        print(frappe.get_traceback())
        return frappe.utils.response.report_error(e.http_status_code)

# This function allows you to fetch the details of a given Shift Permission.
# params: Sift Permission name (eg: SP-000001)
# returns: Details of shift Permission as a doc.
@frappe.whitelist()
def shift_permission_details(shift_permission_id):
    try:
        shift_permission = frappe.get_doc("Shift Permission", {'name':shift_permission_id},["*"])
        return shift_permission
    except Exception as e:
        print(frappe.get_traceback())
        return frappe.utils.response.report_error(e.http_status_code)

# This function allows Shift Permission supervisor to approve the permission and notify the employee.
# params: supervisor_id (eg: HR-EMP-00001) & Sift Permission id (eg: SP-000001)
# returns: Message & workflow of the document (eg: Approved)
@frappe.whitelist()
def shift_permission_approved(supervisor_id, shift_permission_id):
    try:
        shift_supervisor = frappe.db.get_value('Shift Permission',{'name':shift_permission_id},['shift_supervisor'])
        if shift_supervisor == supervisor_id:
            shift_permission_record = frappe.get_doc('Shift Permission',shift_permission_id)
            if shift_permission_record.workflow_state == "Pending":
                shift_permission_record.workflow_state="Approved"
                shift_permission_record.save()
                frappe.db.commit()
                user_id, supervisor_name= frappe.db.get_value('Employee',{'name':shift_supervisor},['user_id','employee_name'])
                subject = _("{name} has approved the permission to {type} on {date}.".format(name=supervisor_name, type=shift_permission_record.permission_type.lower(), date=shift_permission_record.date))
                message = _("{name} has approved the permission to {type} on {date}.".format(name=supervisor_name, type=shift_permission_record.permission_type.lower(), date=shift_permission_record.date))
                notify_for_shift_permission_status(subject,message,user_id,shift_permission_record,1)
                return response({'message':"Shift Permission Approved Successfully",'data':{shift_permission_record.workflow_state}},200)
            elif shift_permission_record.workflow_state == "Approved":
                return response({'message':"Shift Permission is Already Approved",'data':{}},500)
        elif shift_supervisor != supervisor_id:
            return response({'message':"Only Supervisor Has The Right to Approve",'data':{}},400)
    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        return response({'message':"Shift Permission Not Approved Successfully",'data':{}},500)

# This function allows Shift Permission supervisor to reject the permission and notify the employee.
# params: supervisor_id (eg: HR-EMP-00001) & Sift Permission id (eg: SP-000001)
# returns: Message & workflow of the document (eg: Rejected).
@frappe.whitelist()
def shift_permission_rejected(supervisor_id, shift_permission_id):
    try:
        shift_supervisor = frappe.db.get_value('Shift Permission',{'name':shift_permission_id},['shift_supervisor'])
        if shift_supervisor == supervisor_id:
            shift_permission_record = frappe.get_doc('Shift Permission',shift_permission_id)
            if shift_permission_record.workflow_state == "Pending":
                shift_permission_record.workflow_state="Rejected"
                shift_permission_record.save()
                frappe.db.commit()
                user_id, supervisor_name= frappe.db.get_value('Employee',{'name':shift_supervisor},['user_id','employee_name'])
                subject = _("{name} has rejected the permission to {type} on {date}.".format(name=supervisor_name, type=shift_permission_record.permission_type.lower(), date=shift_permission_record.date))
                message = _("{name} has rejected the permission to {type} on {date}.".format(name=supervisor_name, type=shift_permission_record.permission_type.lower(), date=shift_permission_record.date))
                notify_for_shift_permission_status(subject,message,user_id,shift_permission_record,1)
                return response({'message':"Shift Permission Rejected Successfully",'data':{shift_permission_record.workflow_state}},200)
            elif shift_permission_record.workflow_state == "Rejected":
                return response({'message':"Shift Permission is Already Rejected",'data':{}},500)
        elif shift_supervisor != supervisor_id:
            return response({'message':"Only Supervisor Has The Right to Reject",'data':{}},400)
    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        return response({'message':"Shift Permission Not Rejected Successfully",'data':{}},500)

# This function allows Shift Permission supervisor to cancel the permission and notify the employee.
# params: supervisor_id (eg: HR-EMP-00001) & Sift Permission id (eg: SP-000001)
# returns: Message & workflow of the document (eg: Cancelled).
@frappe.whitelist()
def shift_permission_cancelled(supervisor_id, shift_permission_id):
    try:
        shift_supervisor = frappe.db.get_value('Shift Permission',{'name':shift_permission_id},['shift_supervisor'])
        if shift_supervisor == supervisor_id:
            shift_permission_record = frappe.get_doc('Shift Permission',shift_permission_id)
            print("shift_permission_record=>",shift_permission_record.workflow_state)
            if shift_permission_record.workflow_state == "Approved":
                shift_permission_record.workflow_state="Cancelled"
                shift_permission_record.save()
                frappe.db.commit()
                user_id, supervisor_name= frappe.db.get_value('Employee',{'name':shift_supervisor},['user_id','employee_name'])
                subject = _("{name} has cancelled the permission to {type} on {date}.".format(name=supervisor_name, type=shift_permission_record.permission_type.lower(), date=shift_permission_record.date))
                message = _("{name} has cancelled the permission to {type} on {date}.".format(name=supervisor_name, type=shift_permission_record.permission_type.lower(), date=shift_permission_record.date))
                notify_for_shift_permission_status(subject,message,user_id,shift_permission_record,1)
                return response({'message':"Shift Permission Cancelled Successfully",'data':{shift_permission_record.workflow_state}},200)
            elif shift_permission_record.workflow_state == "Cancelled":
                return response({'message':"Shift Permission is Already Cancelled",'data':{}},500)
        elif shift_supervisor != supervisor_id:
            return response({'message':"Only Supervisor Has The Right to Cancel",'data':{}},400)
    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        return response({'message':"Shift Permission Not Cancelled Successfully",'data':{}},500)

# This method sends notification
# params: subject, message, user, shift_permission_record, and mobile_notification
# mobile_notification parameter (eg: 1) for mobile notification list filter
def notify_for_shift_permission_status(subject, message, user, shift_permission_record, mobile_notification):
    create_notification_log(subject, message, [user], shift_permission_record, mobile_notification)

# This method returing the message and status code of the API
def response(message, status_code):
    """
    Params: message, status code
    """
    frappe.local.response["message"] = message
    frappe.local.response["http_status_code"] = status_code
    return