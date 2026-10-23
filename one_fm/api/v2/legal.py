import frappe, base64, json, grpc
from frappe.utils import cint
from one_fm.legal.doctype.penalty_issuance.penalty_issuance import get_filtered_employees
from frappe import _
from one_fm.proto import facial_recognition_pb2_grpc, facial_recognition_pb2
from one_fm.api.v1.utils import response
from one_fm.utils import check_path, create_path

def get_employee_list(shift: str = None, penalty_occurence_time: str = None) -> dict:

    if not shift:
        return response("Bad Request", 400, None, "shift required.")

    if not penalty_occurence_time:
        return response("Bad Request", 400, None, "penalty_ocurrence_time required.")

    if not isinstance(shift, str):
        return response("Bad Request", 400, None, "shift must be of type str.")

    if not isinstance(penalty_occurence_time, str):
        return response("Bad Request", 400, None, "penalty_ocurrence_time must be of type str.")

    try:
        result = get_filtered_employees(shift, penalty_occurence_time, as_dict=1)
        return response("Success", 200, result)
    except Exception as error:
        return response("Internal Server Error", 500, None, error)


@frappe.whitelist()
def get_penalty_types():
    """ This method gets the list of penalty types. """
    try:
        result = frappe.db.sql("""SELECT name, penalty_name_arabic FROM `tabPenalty Type` """, as_dict=1)
        return response("Success", 200, result)
    except Exception as error:
        return response("Internal Server Error", 500, None, error)


@frappe.whitelist()
def get_all_shifts():
    try:
        result = frappe.db.sql("""SELECT osh.name, osh.site, osh.project, ost.site_location 
			FROM `tabOperations Shift` osh, `tabOperations Site` ost  
			WHERE osh.site=ost.name
			ORDER BY name ASC """, as_dict=1)

        return response("Success", 200, result)
    except Exception as error:
        return response("Internal Server Error", 500, None, error)


def issue_penalty(penalty_category, issuing_time, issuing_location, penalty_location, penalty_occurence_time,company_damage, customer_property_damage, asset_damage, other_damages, shift=None, site=None, project=None, site_location=None, penalty_employees=[], penalty_details=[]):
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
			penalty_issuance.append('employees', {'employee_id':employee})

		penalty_issuance_details = json.loads(penalty_details)
		# check and make path for attachments
		path_name = frappe.utils.cstr(frappe.local.site)+"/public/files/Legal"
		if not check_path(path_name):
			create_path(path_name)

		for detail in penalty_issuance_details:
			if detail.get("attachments") and detail.get("attachment_name"):
				filename = detail["attachment_name"]
				attach = detail["attachments"]
				content = base64.b64decode(attach)

				OUTPUT_IMAGE_PATH = path_name+"/"+filename
				fh = open(OUTPUT_IMAGE_PATH, "wb")
				fh.write(content)
				fh.close()
				Attachment_file="/files/Legal/"+filename
				detail.update({'attachments': Attachment_file})

			detail.pop("attachment_name")
			penalty_issuance.append('penalty_issuance_details', detail)

		if penalty_category == "Performace":
			penalty_issuance.shift = shift
			penalty_issuance.site = site
			penalty_issuance.project = project
			penalty_issuance.site_location = site_location


		penalty_issuance.insert()
		penalty_issuance.submit()
		return response("Success", 201, penalty_issuance)

	except Exception as error:
		frappe.log_error(message=str(error), title='Penalty Issuance Error')
		return response("Internal Server Error", 500, None, error)@frappe.whitelist()


def get_penalties(employee_id: str = None, role: str = None) -> dict:

	if not employee_id:
		return response("Bad Request", 400, None, "employee_id required.")

	if not isinstance(employee_id, str):
		return response("Bad Request", 400, None, "employee_id must be of type str.")

	if role:
		if not isinstance(role, str):
			return response("Bad Request", 400, None ,"role must be of type str.")
	try:
		employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

		if not employee:
			return response("Resource not found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))

		if role and role == "Issuance":
			result = frappe.get_list("Penalty", filters={"issuer_employee": employee}, fields=["name", "penalty_issuance_time", "workflow_state"], order_by="modified desc")
			if len(result) > 0:
				return response("Success", 200, result)
			else:
				return response("Resource not found", 404, None, "No penalties found for {employee} with role as {role}".format(employee=employee, role=role))
		else:
			result = frappe.get_list("Penalty", filters={"recipient_employee": employee}, fields=["name", "penalty_issuance_time", "workflow_state"], order_by="modified desc")
			if len(result) > 0:
				return response("Success", 200, result)
			else:
				return response("Resource not found", 404, None, "No penalties found for {employee}".format(employee=employee))
	
	except Exception as error:
		return response("Internal Server Error", 500, None, error)

@frappe.whitelist()
def get_penalty_details(penalty_name: str = None) -> dict:
	"""This method gets the details of a specific penalty provided the name of the penalty document.

	Args:
		penalty_name (str): Name of the penalty document.

	Returns:
		dict: {
            message (str): Brief message indicating the response,
			status_code (int): Status code of response.
            data (dict): Penalty deatils.
            error (str): Any error handled.
		}
	"""
	if not penalty_name:
		return response("Bad Request", 400, None, "penalty_name required.")

	if not isinstance(penalty_name, str):
		return response("Bad Request", 400, None, "penalty_name must be of type str.")

	try:
		penalty_doc = frappe.get_doc("Penalty", {"name": penalty_name})
		if not penalty_doc:
			return response("Resource not found", 404, None, "No penalty of name {penalty_doc} found.".format(penalty_doc=penalty_doc))

		return response("Success", 200, penalty_doc.as_dict())
	
	except Exception as error:
		return response("Internal Server Error", 500, None, error)

@frappe.whitelist()
def accept_penalty(employee_id: str = None, file: str = None, docname: str = None) -> dict:
	"""Penalties are deducted at issuance; the endpoint stays for older app versions."""
	return response("OK", 200, None, "Penalties no longer need to be accepted or rejected.")


@frappe.whitelist()
def reject_penalty(rejection_reason: str = None, docname: str = None):
	"""Penalties are deducted at issuance; the endpoint stays for older app versions."""
	return response("OK", 200, None, "Penalties no longer need to be accepted or rejected.")

