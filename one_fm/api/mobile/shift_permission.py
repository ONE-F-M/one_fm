import frappe
from frappe import _

# This method is creating shift permission record and setting the the shift details
@frappe.whitelist()
def create_shift_permission(employee,permission_type,date,reason,leaving_time=None,arrival_time=None):
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
        












