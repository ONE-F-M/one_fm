import frappe
from frappe.utils import getdate
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
        
        check_timing_values(permission_type, leaving_time=None, arrival_time=None)# Validate time based on permission type
        shift, type, assigned_shift, shift_supervisor = get_shift_details(employee,date)
        if shift and type and assigned_shift and shift_supervisor:
            has_dublicate = validate_record(employee, date, assigned_shift, permission_type)
            if not has_dublicate:
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
                return {'message':"Shift Permission Successfully Created",'data':doc}
            elif has_dublicate:
                doc = frappe.get_doc('Shift Permission',{"employee": employee, "date":date, "assigned_shift": assigned_shift, "permission_type": permission_type})
                return {'message':"{0} has already applied for permission to {1} on {2}.".format(doc.emp_name, permission_type.lower(), date),'data':{}}

        elif not shift or not type or not assigned_shift or not shift_supervisor:
            return {'message':"Shift Details are missing, Please Make sure You are have a Scheduled record on {0}".format(date),'data':{}}
           
    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        return {'message':"Shift Permission Not Created Successfully",'data':{}}

# This method validates any dublicate permission for the employee on same day
def validate_record(employee, date, assigned_shift, permission_type):
    if frappe.db.exists("Shift Permission", {"employee": employee, "date":date, "assigned_shift": assigned_shift, "permission_type": permission_type}):
        return True
    else:
        return False 

# Check The time provide upon Permission time
def check_timing_values(permission_type, leaving_time=None, arrival_time=None):
        if permission_type == "Arrive Late" and not arrival_time:
            return {'message':"Arrive Time is Required to Complete Your Permission",'data':{}}
        if permission_type == "Leave Early" and not leaving_time:
            return {'message':"Leaving Time is Required to Complete Your Permission",'data':{}}

# Fetching shift details of the employee and adding them in shift permission record
def get_shift_details(employee, date):
    shift, type = frappe.db.get_value('Employee Schedule',{'employee':employee,'employee_availability':'Working','date':date,'roster_type':'Basic'},['shift','shift_type']) 
    if shift and type:
        shift_supervisor = frappe.db.get_value('Operations Shift',{'name':shift},['supervisor'])
        assigned_shift = frappe.db.get_value('Shift Assignment',{'employee':employee,'start_date':date},['name']) # start date and end date of HO employee are the same in the shift assignment
        if not assigned_shift:
            return {'message':"You Don't Have Shift Assignment on {date}".format(date=date),'data':{}}
        elif assigned_shift:
            return shift, type, assigned_shift, shift_supervisor
    elif not shift and not type:
        return {'message':"You Don't Have Shift on {date}".format(date=date),'data':{}}
    
    
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
    return {'messages':"Roles Are Successfully Listed ",'data':user_roles}