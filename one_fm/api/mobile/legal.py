import frappe
from frappe.utils import cint
from one_fm.legal.doctype.penalty_issuance.penalty_issuance import get_filtered_employees
import json

@frappe.whitelist()
def get_employee_list(shift, penalty_occurence_time):
	try:
		return get_filtered_employees(shift, penalty_occurence_time, as_dict=1)
	except Exception as exc:
		print(frappe.get_traceback())
		frappe.log_error(frappe.get_traceback())
		return frappe.utils.response.report_error(exc)


@frappe.whitelist()
def get_penalty_types():
	try:
		return frappe.db.sql("""SELECT name, penalty_name_arabic FROM `tabPenalty Type` """, as_dict=1)
	except Exception as exc:
		print(frappe.get_traceback())
		frappe.log_error(frappe.get_traceback())
		return frappe.utils.response.report_error(exc)


@frappe.whitelist()
def get_all_shifts():
	try:
		return frappe.db.sql("""SELECT osh.name, osh.site, osh.project, ost.site_location 
			FROM `tabOperations Shift` osh, `tabOperations Site` ost  
			WHERE osh.site=ost.name
			ORDER BY name ASC """, as_dict=1)
	except Exception as exc:
		print(frappe.get_traceback())
		frappe.log_error(frappe.get_traceback())
		return frappe.utils.response.report_error(exc)


@frappe.whitelist()
def issue_penalty(penalty_category, issuing_time, issuing_location, penalty_location, penalty_occurence_time, company_damage, customer_property_damage, asset_damage, other_damages, shift=None, site=None, project=None, site_location=None, penalty_employees=[], penalty_details=[]):
	try:
		employee, employee_name, designation = frappe.get_value("Employee", {"user_id": frappe.session.user}, ["name","employee_name", "designation"])
		
		penalty_issuance = frappe.new_doc("Penalty Issuance")
		penalty_issuance.penalty_category = penalty_category
		
		penalty_issuance.issuing_time = issuing_time
		penalty_issuance.location = issuing_location
		penalty_issuance.penalty_location = penalty_location
		penalty_issuance.penalty_occurence_time = penalty_occurence_time

		penalty_issuance.issuing_employee = employee
		penalty_issuance.employee_name = employee_name
		penalty_issuance.designation = designation
		
		penalty_issuance.customer_property_damage = cint(customer_property_damage)
		penalty_issuance.company_damage = cint(company_damage)
		penalty_issuance.other_damages = cint(other_damages)
		penalty_issuance.asset_damage = cint(asset_damage)

		employees = json.loads(penalty_employees)
		for employee in employees:
			penalty_issuance.append('employees', employee)

		penalty_issuance_details = json.loads(penalty_details)
		for detail in penalty_issuance_details:
			penalty_issuance.append('penalty_issuance_details', detail)

		if penalty_category == "Performace":
			penalty_issuance.shift = shift
			penalty_issuance.site = site
			penalty_issuance.project = project
			penalty_issuance.site_location = site_location


		penalty_issuance.insert()
		penalty_issuance.submit()
		return penalty_issuance

	except Exception as exc:
		print(frappe.get_traceback())
		frappe.log_error(frappe.get_traceback())
		return frappe.utils.response.report_error(exc)

	
@frappe.whitelist()
def get_penalties(employee):
	return frappe.get_list("Penalty", filters={"recipient_employee": employee}, fields=["name", "penalty_issuance_time"], order_by="modified desc")


@frappe.whitelist()
def get_penalty_details(penalty_name):
	return frappe.get_list("Penalty", {"name": penalty_name}, ["*"])