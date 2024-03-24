import frappe, os, json, requests


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
