import frappe, os, json, requests
from datetime import datetime, timedelta
from frappe.utils import now
from frappe import _

def validate_sick_leave_attachment(doc):
    """
       Ensure that all sick leaves have an attachment

    Returns:
        (Bool) : True if attachment is present, False if attachment is not present.
    """
    leave_attachments = frappe.get_all("File",{'attached_to_doctype':"Leave Application",'attached_to_name':doc.name},['name'])
    if not leave_attachments:
        return False
    return True


def response(code, title, msg, data=None):
    frappe.local.response['http_status_code'] = code
    frappe.local.response['message'] = {
        'title': title,
        'msg': msg,
        'data':data
    }


def get_reports_to_employee_name(employee):
    reports_to = frappe.db.get_value('Employee', employee, 'reports_to')
    if reports_to: return reports_to
    
    if not reports_to:
        site = frappe.db.get_value('Employee', employee, 'site')
        if site:
            return frappe.db.get_value('Operations Site', site, 'account_supervisor')

    if not reports_to:
        shift = frappe.db.get_list("Shift Assignment", filters={'employee':employee},
            fields=['shift'], order_by="start_date DESC", page_length=1)
        if len(shift):
            return frappe.db.get_value("Operations Shift", shift[0].shift, 'supervisor')

    # when no shift supervisor or reports to in employee use site and project

    # if no site supervisor, get project manager 
    if not reports_to:
        project = frappe.db.get_value('Employee', employee, 'project')
        if project:
            return frappe.db.get_value('Project', project, 'account_manager')

    if not reports_to:
        frappe.throw(f"Employee {employee} have no reports to.")

@frappe.whitelist()
def set_up_face_recognition_server_credentials():
    try:
        credpath = os.getcwd()+frappe.utils.get_site_base_path().replace('./', '/')+frappe.local.conf.google_application_credentials
        with open(credpath, 'r') as f:
            cred = json.loads(f.read())
            res=requests.post(
                frappe.local.conf.face_recognition_channel.get('url')+'/bigbang', 
                json={'cred':cred, 'bucketpath':frappe.local.conf.face_recognition_channel.get('bucket')}, 
                timeout=300)
        return {'error':False, 'message':'Face Recognition Server credentials setup successfully.'}
    except Exception as e:
        frappe.log_error("Face Recognition Setup", frappe.get_traceback())
        return {'error':True, 'message':e}
    
@frappe.whitelist()
def _get_current_shift(employee):
    """
        Get current shift employee should be logged into
    """
    sql = f"""
        SELECT * FROM `tabShift Assignment`
        WHERE employee="{employee}" AND status="Active" AND 
        ('{now()}' BETWEEN start_datetime AND end_datetime)
    """
    shift = frappe.db.sql(sql, as_dict=1)
    if shift: # shift was checked in between start and end time
        return shift[0]
    else: # we look right and left (right for next shift)
        dt = datetime.strptime(now(), '%Y-%m-%d %H:%M:%S.%f')
        curtime_plus_1 = dt + timedelta(hours=1)
        sql = f"""
            SELECT * FROM `tabShift Assignment`
            WHERE employee="{employee}" AND status="Active" AND 
            ('{curtime_plus_1}' BETWEEN start_datetime AND end_datetime)
        """
        shift = frappe.db.sql(sql, as_dict=1)
        if shift: # shift was checked 1hr ahead
            return shift[0]
        else:
            curtime_plus_1 = dt + timedelta(hours=-1)
            sql = f"""
                SELECT * FROM `tabShift Assignment`
                WHERE employee="{employee}" AND status="Active" AND 
                ('{curtime_plus_1}' BETWEEN start_datetime AND end_datetime)
            """
            shift = frappe.db.sql(sql, as_dict=1)
            if shift: # shift was checked 1hr in the past
                return shift[0]
    return False

@frappe.whitelist()
def _check_existing(shift):
    """API to determine the applicable Log type.
    The api checks employee's last lcheckin log type. and determine what next log type needs to be
    Returns:
        True: The log in was "IN", so his next Log Type should be "OUT".
        False: either no log type or last log type is "OUT", so his next Ltg Type should be "IN".
    """
    checkin = frappe.db.get_value("Employee Checkin", {
        'employee':shift.employee, 'shift_assignment':shift.name,
        'shift_actual_start':shift.start_datetime,
        'shift_actual_end':shift.end_datetime,
        'roster_type':shift.roster_type
    }, 'log_type')
	
	# #For Check IN
    if not checkin or checkin=='OUT':
        return False
    #For Check OUT
    else:
        return True
