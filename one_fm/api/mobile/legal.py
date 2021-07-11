import frappe
from frappe.utils import cint
from one_fm.legal.doctype.penalty_issuance.penalty_issuance import get_filtered_employees
from one_fm.legal.doctype.penalty.penalty import send_email_to_legal, recognize_face
from frappe import _
import pickle, face_recognition
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
	return frappe.get_list("Penalty", filters={"recipient_employee": employee}, fields=["name", "penalty_issuance_time", "workflow_state"], order_by="modified desc")


@frappe.whitelist()
def get_penalty_details(penalty_name):
	return frappe.get_list("Penalty", {"name": penalty_name}, ["*"])

@frappe.whitelist()
def accept_penalty(file, retries, docname):
	"""
	Params:
	File: Base64 url of captured image.
	Retries: number of tries left out of three
	Docname: Name of the penalty doctype

	Returns: 
		'success' message upon verification || updated retries and 'error' message || Exception. 
	"""
	try:
		print(retries)
		retries_left = cint(retries) - 1
		OUTPUT_IMAGE_PATH = frappe.utils.cstr(frappe.local.site)+"/private/files/"+frappe.session.user+".png"
		penalty = frappe.get_doc("Penalty", docname)
		if recognize_face(file, OUTPUT_IMAGE_PATH, retries_left) or retries_left == 0:
			if retries_left == 0:
				penalty.verified = 0
				send_email_to_legal(penalty)
			else:
				penalty.verified = 1		
			penalty.workflow_state = "Penalty Accepted"
			penalty.save(ignore_permissions=True)
			
			file_doc = frappe.get_doc({
				"doctype": "File",
				"file_url": "/private/files/"+frappe.session.user+".png",
				"file_name": frappe.session.user+".png",
				"attached_to_doctype": "Penalty",
				"attached_to_name": docname,
				"folder": "Home/Attachments",
				"is_private": 1
			})
			print(file_doc.as_dict())
			file_doc.flags.ignore_permissions = True
			file_doc.insert()

			frappe.db.commit()

			return {
				'message': 'success'
			}
		else:
			penalty.db_set("retries", retries_left)
			frappe.throw(_("Face could not be recognized. You have {0} retries left.").format(frappe.bold(retries_left)), title='Validation Error')

	except Exception as exc:
		print(frappe.get_traceback())
		frappe.log_error(frappe.get_traceback())
		return frappe.utils.response.report_error(exc)

@frappe.whitelist()
def reject_penalty(rejection_reason, docname):
	"""
	Params:
	Reason for rejection: Basis and/or reasoning due to which the employee is rejecting the issuance of penalty.
	Docname: Name of the penalty doctype

	Returns: 
		'success' message upon successful rejection of the penalty || 'No penalty found' if the penalty doesnt exist || Exception. 
	"""
	try:
		penalty = frappe.get_doc("Penalty", docname)
		if penalty.workflow_state == 'Penalty Issued':
			penalty.reason_for_rejection = rejection_reason
			penalty.workflow_state = "Penalty Rejected"
			penalty.save(ignore_permissions=True)
			frappe.db.commit()
			return {
					'message': 'success'
				}
		else:
			return {
					'message': f'No penalty {docname} found'
				}
	except Exception as exc:
		print(frappe.get_traceback())
		frappe.log_error(frappe.get_traceback())
		return frappe.utils.response.report_error(exc)
