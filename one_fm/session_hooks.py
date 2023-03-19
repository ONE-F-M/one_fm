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