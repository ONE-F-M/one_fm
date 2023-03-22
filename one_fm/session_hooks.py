from werkzeug.wrappers import Request, Response
import frappe

def on_session_creation(login_manager):
    try:
        frappe.local.session.employee = frappe.db.get_value('Employee', {'user_id':frappe.session.user}, 'name')
        frappe.local.employee = frappe.session.employee
        frappe.local.user.employee = frappe.session.employee
        frappe.local.user_defaults = frappe.session.employee
        frappe.local.boot.user.employee = frappe.session.employee
    except Exception as e:
        frappe.session['employee'] = ''

def auth_hooks():
    if not frappe.cache().get_value(frappe.session.user):
        try:
            if not frappe.session.user:
                frappe.cache().set_value(frappe.session.user, frappe._dict({}))
            else:
                employee = frappe.db.get_value('Employee', {'user_id':frappe.session.user}, 'name')
                frappe.cache().set_value(frappe.session.user, frappe._dict({'employee':employee}))
        except:
            frappe.cache().set_value(frappe.session.user, frappe._dict({}))

def on_login(login_manager):
    """
        Process some actions when user logins in.
        Created log when admin logs in.
    """
    if frappe.session.user == 'Administrator':
        session = frappe.session.data
        environ = frappe._dict(frappe.local.request.environ)
        frappe.get_doc(
            {
            'doctype':'Administrator Auto Log',
            'ip': session.session_ip, 
            'datetime': session.last_updated, 
            'session_expiry': session.session_expiry,
            'device': session.desktop, 
            'session_country': session.session_country,
            'http_sec_ch_ua':environ.HTTP_SEC_CH_UA,
            'user_agent':environ.HTTP_USER_AGENT,
            'platform':environ.HTTP_SEC_CH_UA_PLATFORM,
            }
        ).insert()

