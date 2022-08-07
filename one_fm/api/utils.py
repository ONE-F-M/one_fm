import frappe

def response(code, title, msg, data=None):
    frappe.local.response['http_status_code'] = code
    frappe.local.response['message'] = {
        'title': title,
        'msg': msg,
        'data':data
    }


def get_reports_to_employee_name(employee):
    reports_to = None
    reports_to = frappe.db.get_value('Employee', employee, 'reports_to')
    if not reports_to:
        shift = frappe.db.get_list("Shift Assignment", filters={'employee':employee},
            fields=['shift'], order_by="start_date DESC", page_length=1)
        if len(shift):
            reports_to = frappe.db.get_value("Operations Shift", shift[0].shift, 'supervisor')

    # when no shift supervisor or reports to in employee use site and project
    if not reports_to:
        site = frappe.db.get_value('Employee', employee, 'site')
        if site:
            reports_to = frappe.db.get_value('Operations Site', site, 'account_supervisor')

    # if no site supervisor, get project manager
    if not reports_to:
        project = frappe.db.get_value('Employee', employee, 'project')
        if project:
            reports_to = frappe.db.get_value('Project', project, 'account_manager')

    if not reports_to:
        frappe.throw(f"Employee {employee} have no reports to.")

    return reports_to