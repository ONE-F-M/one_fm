import frappe
from frappe import _

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
        shift,type,assigned_shift,shift_supervisor = get_shift_details(employee,date)
        if shift and type and assigned_shift and shift_supervisor:
            doc = frappe.new_doc('Shift Permission')
            doc.employee = employee
            doc.date = date
            doc.permission_type = permission_type
            doc.reason = reason
            if permission_type == "Arrive Late":
                doc.arrival_time = arrival_time
            if permission_type == "Leave Early":
                doc.leaving_time = leaving_time
            doc.assigned_shift = assigned_shift
            doc.shift_supervisor = shift_supervisor
            doc.shift = shift
            doc.shift_type = type
            doc.save()
            frappe.db.commit()
            return doc

    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        return frappe.utils.response.report_error(e)

# Fetching shift details of the employee and adding them in shift permission record
def get_shift_details(employee,date):
    shift, type = frappe.db.get_value('Employee Schedule',{'employee':employee,'employee_availability':'Working','date':date,'roster_type':'Basic'},['shift','shift_type']) 
    shift_supervisor = frappe.db.get_value('Operations Shift',{'name':shift},['supervisor'])
    assigned_shift = frappe.db.get_value('Shift Assignment',{'employee':employee,'start_date':date},['name']) # start date and end date of HO employee are the same in the shift assignment
    return shift,type,assigned_shift,shift_supervisor
    
# This method is returning employee roles upon employee_id
@frappe.whitelist()
def get_employee_roles(employee_id):
    """
	Params:
	employee: HO employee ERP id
    Returns: roles of employee
	"""
    user_id = frappe.db.get_value('Employee',{'name':employee_id},['user_id'])
    user_roles = frappe.get_roles(user_id)
    return user_roles


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