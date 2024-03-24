import frappe, os, json, requests
from one_fm.operations.doctype.operations_shift.operations_shift import get_active_supervisor

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
            return get_active_supervisor(shift[0].shift)
            
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