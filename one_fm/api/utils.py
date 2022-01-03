import frappe

def response(code, title, msg, data=None):
    frappe.local.response['http_status_code'] = code
    frappe.local.response['message'] = {
        'title': title,
        'msg': msg,
        'data':data
    }
