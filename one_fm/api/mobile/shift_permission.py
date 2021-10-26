import frappe
from frappe import _

#This method is creating shift permission record and setting the mendatory fields
@frappe.whitelist()
def create_shift_permission(employee,permission_type,date,reason,leaving_time=None,arrival_time=None):
    """
	Params:
	employee: erp id
    permission_type,date,reason,leaving_time,arrival_time
	"""
    try:
        doc = frappe.new_doc('Shift Permission')
        doc.employee = employee
        doc.date = date
        doc.permission_type = permission_type
        doc.reason = reason
        if permission_type == "Arrive Late":
            doc.arrival_time = arrival_time
        if permission_type == "Leave Early":
            doc.leaving_time = leaving_time
        doc.save()
        frappe.db.commit()
        return doc
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(frappe.get_traceback())
        return frappe.utils.response.report_error(e)
    
