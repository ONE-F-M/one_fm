import frappe, base64
from frappe.utils import cint
from one_fm.legal.doctype.penalty_issuance.penalty_issuance import get_filtered_employees
from one_fm.legal.doctype.penalty.penalty import send_email_to_legal, upload_image
from frappe import _
import json
from one_fm.utils import response

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
			penalty_issuance.append('employees', employee)

		penalty_issuance_details = json.loads(penalty_details)
		for detail in penalty_issuance_details:
			if detail["attachments"] and detail["attachment_name"]:
				filename = detail["attachment_name"]
				attach = detail["attachments"]
				content = base64.b64decode(attach)

				OUTPUT_IMAGE_PATH = frappe.utils.cstr(frappe.local.site)+"/public/files/Legal/"+filename
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
		return penalty_issuance

	except Exception as exc:
		print(frappe.get_traceback())
		frappe.log_error(frappe.get_traceback())
		return frappe.utils.response.report_error(exc)

	
@frappe.whitelist()
def get_penalties(employee, Role):
	if Role == "Issuance":
		return frappe.get_list("Penalty", filters={"issuer_employee": employee}, fields=["name", "penalty_issuance_time", "workflow_state"], order_by="modified desc")
	else:
		return frappe.get_list("Penalty", filters={"recipient_employee": employee}, fields=["name", "penalty_issuance_time", "workflow_state"], order_by="modified desc")

@frappe.whitelist()
def get_penalty():
	user = frappe.session.user
	user_roles = frappe.get_roles(user)
	if user == "Administrator" or "Legal Manager" in user_roles:
		List = frappe.get_list("Penalty")
	else:
		employee = frappe.get_value("Employee", {"user_id": user}, ["name"])
		if "Penalty Recipient" in user_roles and "Penalty Issuer" in user_roles:
			penalty_issuer = frappe.get_list("Penalty", {"issuer_employee": employee})
			penalty_Recip = frappe.get_list("Penalty", {"recipient_employee": employee})
			penalty_issuer.append(penalty_Recip)
			List = penalty_issuer	
		elif "Penalty Issuer" in user_roles:
			List = frappe.get_list("Penalty", {"issuer_employee": employee})
		else:
			print(employee)
			List = frappe.get_list("Penalty", {"recipient_employee": employee})
	return List

@frappe.whitelist()
def get_penalty_details(penalty_name):
	return frappe.get_doc("Penalty", {"name": penalty_name})

@frappe.whitelist()
def accept_penalty(file, retries, docname):
	"""
	This is an API to accept penalty. To Accept Penalty, one needs to pass the face recognition test.
	Image file in base64 format is passed through face regonition test. And, employee is given 3 tries.
	If face recognition is true, the penalty gets accepted. 
	If Face recognition fails even after 3 tries, the image is sent to legal mangager for investigation. 

	Params:
	File: Base64 url of captured image.
	Retries: number of tries left out of three
	Docname: Name of the penalty doctype

	Returns: 
		'success' message upon verification || updated retries and 'error' message || Exception. 
	"""
	try:
		import grpc
		from one_fm.proto import facial_recognition_pb2_grpc, facial_recognition_pb2
		
		penalty_doc = frappe.get_doc("Penalty", docname)
		retries_left = cint(retries) - 1
		# setup channel
		face_recognition_service_url = frappe.local.conf.face_recognition_service_url
		channel = grpc.secure_channel(face_recognition_service_url, grpc.ssl_channel_credentials())
		# setup stub
		stub = facial_recognition_pb2_grpc.FaceRecognitionServiceStub(channel)

		# request body
		req = facial_recognition_pb2.FaceRecognitionRequest(
			username = frappe.session.user,
			media_type = "image",
			media_content = file,
		)
		# Call service stub and get response
		res = stub.FaceRecognition(req)
		if res.verification == "OK":
			if cint(penalty_doc.retries) == 0:
				penalty_doc.verified = 0
				send_email_to_legal(penalty_doc)
			else:
				penalty_doc.verified = 1		
				penalty_doc.workflow_state = "Penalty Accepted"
			penalty_doc.save(ignore_permissions=True)
			
			file_doc = frappe.get_doc({
				"doctype": "File",
				"file_url": "/private/files/"+frappe.session.user+".png",
				"file_name": frappe.session.user+".png",
				"attached_to_doctype": "Penalty",
				"attached_to_name": docname,
				"folder": "Home/Attachments",
				"is_private": 1
			})
			file_doc.flags.ignore_permissions = True
			file_doc.insert()

			frappe.db.commit()

			return response("Penalty accepted successfully.", {}, True ,200)
		else:
			penalty_doc.db_set("retries", retries_left)
			return response("Face Recognition Failed. You have "+str(retries_left)+" retries left." ,{"retries_left":retries_left},False,401)
			# frappe.throw(_("Face could not be recognized. You have {0} retries left.").format(frappe.bold(retries_left)), title='Validation Error')

	except Exception as exc:
		frappe.log_error(frappe.get_traceback())
		return response(exc,{},False, 500)

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
			return response("Penalty Rejected", {}, True, 200)
		else:
			return response("No penalty {docname} found." , {}, False, 401)
	except Exception as exc:
		frappe.log_error(frappe.get_traceback())
		return response(exc,{},False, 500)
