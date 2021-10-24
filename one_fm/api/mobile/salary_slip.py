import frappe
from frappe import _

#This function returns the list of salary slips of a given employee, within the dictionary with "name","start_date", "end_date", "status", "total_working_days".
@frappe.whitelist()
def get_salary_slip_list(employee_id):
    try:
        salary_list = frappe.get_all("Salary Slip", filters={'employee':employee_id}, fields=["name","start_date", "end_date", "status", "total_working_days"])
        return Salary_list 
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(frappe.get_traceback())
        return frappe.utils.response.report_error(e)

#This function returns the details of  given salary slips.
@frappe.whitelist()
def salary_slip_details(salary_slip_id):
    try:
        salary_slip_details = frappe.get_doc("Salary Slip", salary_slip_id, '*' ) 
        return salary_slip_details
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(frappe.get_traceback())
        return frappe.utils.response.report_error(e)
