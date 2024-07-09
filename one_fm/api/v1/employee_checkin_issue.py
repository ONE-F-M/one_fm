from decimal import Decimal

import frappe
from frappe import _
from one_fm.api.notification import create_notification_log
from one_fm.api.v1.utils import response, validate_date, validate_time
from one_fm.operations.doctype.employee_checkin_issue.employee_checkin_issue import fetch_approver

@frappe.whitelist()
def create_employee_checkin_issue(employee_id: str = None, log_type: str = None, issue_type: str = None, date: str = None,
	issue_details: str = None, latitude: str = None, longitude: str = None) -> dict:
	"""This method creates a employee checkin issue for a given employee.

	Args:
		employee (str): employee id
		log_type (str): type of log(IN/OUT).
		issue_type (str): type of issue requested.
		date (str): yyyy-mm-dd
		issue_details (str): reason to create a employee checkin issue
		latitude (float, optional): Latitude od user.
		longitude (float, optional): Longitude od user.

	Returns:
		dict: {
			message (str): Brief message indicating the response,
			status_code (int): Status code of response.
			data (dict): employee checkin issue created.
			error (str): Any error handled.
		}
	"""
	try:
		if not employee_id:
			return response("Bad Request", 400, None, "employee_id required.")

		if not log_type:
			return response("Bad Request", 400, None, "log_type required.")

		if not issue_type:
			return response("Bad Request", 400, None, "issue_type required.")

		if not date:
			return response("Bad Request", 400, None, "date required.")

		if issue_type == "Other":
			if not issue_details:
				return response("Bad Request", 400, None, "issue_details required.")
			if not isinstance(issue_details, str):
				return response("Bad Request", 400, None, "issue_details must be of type str.")

		if not isinstance(employee_id, str):
			return response("Bad Request", 400, None, "employee must be of type str.")

		if not isinstance(issue_type, str):
			return response("Bad Request", 400, None, "issue_type must be of type str.")

		if not latitude:
			return response("Bad Request", 400, None, "latitude required.")

		if not longitude:
			return response("Bad Request", 400, None, "longitude required.")

		try:
			latitude = Decimal(latitude)
			longitude = Decimal(longitude)
		except:
			return response("Bad Request", 400, None, "Latitude and longitude must be float.")

		if not isinstance(date, str):
			return response("Bad Request", 400, None, "date must be of type str.")

		if not validate_date(date):
			return response("Bad Request", 400, None, "date must be of type yyyy-mm-dd.")
		
		employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

		if not employee:
			return response("Resource Not Found", 404, None, "No employee found with {employee_id}"
				.format(employee_id=employee_id))

		shift_details = get_shift_details(employee)

		if shift_details.found:
			shift, shift_type, shift_assignment, shift_supervisor = shift_details.data
		else:
			return response("Resource Not Found", 404, None, "shift not found in employee schedule for {employee}"
				.format(employee=employee))

		if not shift_type:
			return response("Resource Not Found", 404, None, "shift type not found in employee schedule for {employee}"
				.format(employee=employee))

		if not shift_assignment:
			return response("Resource Not Found", 404, None, "shift assingment not found for {employee}"
				.format(employee=employee))

		if not shift_supervisor:
			return response("Resource Not Found", 404, None, "shift supervisor not found for {employee}"
				.format(employee=employee_id))

		if not frappe.db.exists("Employee Checkin Issue", {"employee": employee, "date": date,
			"assigned_shift": shift_assignment, "log_type": log_type, "issue_type": issue_type}):
			employee_checkin_issue_doc = frappe.new_doc('Employee Checkin Issue')
			employee_checkin_issue_doc.employee = employee
			employee_checkin_issue_doc.date = date
			employee_checkin_issue_doc.log_type = log_type
			employee_checkin_issue_doc.issue_type = issue_type
			if issue_type == "Other":
				employee_checkin_issue_doc.issue_details = issue_details
			employee_checkin_issue_doc.latitude = latitude if latitude else 0.0
			employee_checkin_issue_doc.longitude = longitude if longitude else 0.0
			employee_checkin_issue_doc.assigned_shift = shift_assignment
			employee_checkin_issue_doc.shift_supervisor = shift_supervisor
			employee_checkin_issue_doc.shift = shift
			employee_checkin_issue_doc.shift_type = shift_type
			employee_checkin_issue_doc.save()
			frappe.db.commit()
			return response("Success", 201, employee_checkin_issue_doc.as_dict())

		else:
			frappe.log_error(title="API Authentication", message=frappe.get_traceback())
			return response("Duplicate", 422, None, "Employee Checkin Issue is already created for {employee}"
				.format(employee=employee_id))

	except Exception as error:
		return response("Internal Server Error", 500, None, error)

def get_shift_details(employee):
	shift = shift_type = shift_assignment = shift_supervisor = None

	shift_details = fetch_approver(employee=employee)
	shift_assignment = shift_details.get("assigned_shift") 
	shift_supervisor = shift_details.get("shift_supervisor"),
	shift = shift_details.get("shift")
	shift_type = shift_details.get("shift_type")
	
	if not shift_assignment:
		return frappe._dict({'found':False})

	return frappe._dict({'found':True, 'data':[shift, shift_type, shift_assignment, shift_supervisor]})

@frappe.whitelist()
def list_employee_checkin_issue(employee_id: str = None):
	if not employee_id:
		return response("Bad Request", 400, None, "employee_id required.")

	if not isinstance(employee_id, str):
		return response("Bad Request", 400, None, "employee_id must be of type str.")

	try:
		employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

		if not employee:
			return response("Resource Not Found", 404, None, "No employee found with {employee_id}"
				.format(employee_id=employee_id))

		employee_checkin_issue_list = frappe.get_list("Employee Checkin Issue",
			filters={'employee': employee}, fields=["name", "date", "workflow_state"])
		return response("Success", 200, employee_checkin_issue_list)

	except Exception as error:
		return response("Internal Server Error", 500, None, error)

@frappe.whitelist()
def employee_checkin_issue_details(employee_checkin_issue_id: str = None):
	if not employee_checkin_issue_id:
		return response("Bad Request", 400, None, "employee_checkin_issue_id required.")

	if not isinstance(employee_checkin_issue_id, str):
		return response("Bad Request", 400, None, "employee_checkin_issue_id must be of type str.")

	if frappe.db.exists("Employee Checkin Issue", {'name': employee_checkin_issue_id}):
		try:
			employee_checkin_issue_doc = frappe.get_doc("Employee Checkin Issue", {'name': employee_checkin_issue_id})
			return response("Success", 200, employee_checkin_issue_doc.as_dict())
		except Exception as error:
			return response("Internal Server Error", 500, None, error)
	else:
		return response("Resource Not Found", 404, None, "Employee Checkin Issue {employee_checkin_issue_id} not found"
			.format(employee_checkin_issue_id=employee_checkin_issue_id))

@frappe.whitelist()
def approve_employee_checkin_issue(employee_id: str = None, employee_checkin_issue_id: str = None):
	if not employee_id:
		return response("Bad Request", 400, None, "employee_id required.")

	if not isinstance(employee_id, str):
		return response("Bad Request", 400, None, "employee_id must be of type str.")

	if not employee_checkin_issue_id:
		return response("Bad Request", 400, None, "employee_checkin_issue_id required.")

	if not isinstance(employee_checkin_issue_id, str):
		return response("Bad Request", 400, None, "employee_checkin_issue_id must be of type str.")

	try:
		employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

		if not employee:
			return response("Resource Not Found", 404, None, "No employee found with {employee_id}"
				.format(employee_id=employee_id))

		if frappe.db.exists("Employee Checkin Issue", {'name': employee_checkin_issue_id}):
			employee_checkin_issue_doc = frappe.get_doc('Employee Checkin Issue', employee_checkin_issue_id)

			shift_supervisor = frappe.db.get_value('Employee Checkin Issue',
				{'name': employee_checkin_issue_id},['shift_supervisor'])
			if not shift_supervisor:
				return response("Resource Not Found", 404, None, "No shift supervisor found for {employee_checkin_issue_id}"
					.format(employee_checkin_issue_id=employee_checkin_issue_id))

			if shift_supervisor != employee:
				return response("Forbidden", 403, None, "{employee_id} cannot approve this employee checkin issue."
					.format(employee_id=employee_id))

			if employee_checkin_issue_doc.workflow_state == "Pending":
				employee_checkin_issue_doc.workflow_state="Approved"
				employee_checkin_issue_doc.save()
				frappe.db.commit()

				user_id, supervisor_name = frappe.db.get_value('Employee', {'name': shift_supervisor}, ['user_id', 'employee_name'])
				message = _("{name} has approved the Employee Checkin Issue for {type} on {date}."
					.format(name=supervisor_name, type=employee_checkin_issue_doc.log_type, date=employee_checkin_issue_doc.date))
				notify_for_employee_checkin_issue_status(message, message, user_id, employee_checkin_issue_doc, 1)
				return response("Success", 201, employee_checkin_issue_doc.as_dict())
			else:
				return response("Bad Request", 400, None, "Employee Checkin Issue is in {workflow_state} state."
					.format(workflow_state=employee_checkin_issue_doc.workflow_state))
		else:
			return response("Resource Not Found", 404, None, "Employee checkin issue with {employee_checkin_issue_id} not found"
				.format(employee_checkin_issue_id=employee_checkin_issue_id))

	except Exception as error:
		return response("Internal Server Error", 500, None, error)

@frappe.whitelist()
def reject_employee_checkin_issue(employee_id: str = None, employee_checkin_issue_id: str = None):
	if not employee_id:
		return response("Bad Request", 400, None, "employee_id required.")

	if not isinstance(employee_id, str):
		return response("Bad Request", 400, None, "employee_id must be of type str.")

	if not employee_checkin_issue_id:
		return response("Bad Request", 400, None, "employee_checkin_issue_id required.")

	if not isinstance(employee_checkin_issue_id, str):
		return response("Bad Request", 400, None, "employee_checkin_issue_id must be of type str.")

	try:
		employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

		if not employee:
			return response("Resource Not Found", 404, None, "No employee found with {employee_id}"
				.format(employee_id=employee_id))

		if frappe.db.exists("Employee Checkin Issue", {'name': employee_checkin_issue_id}):
			employee_checkin_issue_doc = frappe.get_doc('Employee Checkin Issue', employee_checkin_issue_id)
			shift_supervisor = frappe.db.get_value('Employee Checkin Issue', {'name': employee_checkin_issue_id},['shift_supervisor'])
			if not shift_supervisor:
				return response("Resource Not Found", 404, None, "No shift supervisor found for {employee_checkin_issue_id}"
					.format(employee_checkin_issue_id=employee_checkin_issue_id))

			if shift_supervisor != employee:
				return response("Forbidden", 403, None, "{employee_id} cannot approve this employee checkin issue."
					.format(employee_id=employee_id))

			if employee_checkin_issue_doc.workflow_state == "Pending":
				employee_checkin_issue_doc.workflow_state="Rejected"
				employee_checkin_issue_doc.save()
				frappe.db.commit()

				user_id, supervisor_name= frappe.db.get_value('Employee',{'name':shift_supervisor},['user_id','employee_name'])
				message = _("{name} has rejected the employee checkin issue for {type} on {date}."
					.format(name=supervisor_name, type=employee_checkin_issue_doc.log_type,
						date=employee_checkin_issue_doc.date))
				notify_for_employee_checkin_issue_status(message, message, user_id, employee_checkin_issue_doc, 1)

				return response("Success", 201, employee_checkin_issue_doc.as_dict())

			else:
				return response("Bad Request", 400, None, "Employee Checkin Issue is in {workflow_state} state."
					.format(workflow_state=employee_checkin_issue_doc.workflow_state))
		else:
			return response("Resource Not Found", 404, None, "Employee checkin issue with {employee_checkin_issue_id} not found"
				.format(employee_checkin_issue_id=employee_checkin_issue_id))

	except Exception as error:
		return response("Internal Server Error", 500, None, error)

def notify_for_employee_checkin_issue_status(subject, message, user, employee_checkin_issue_doc, mobile_notification):
	create_notification_log(subject, message, [user], employee_checkin_issue_doc, mobile_notification)




@frappe.whitelist(methods=["GET"])
def get_issue_type():
	try:
		doctype = frappe.get_meta("Employee Checkin Issue")
		if not doctype:
			return response("Doctype does not exist", 400, None)

		field = next((field for field in doctype.fields if field.fieldname == "issue_type"), None)
		if not field or field.fieldtype != 'Select':
			return response("Field not found or is not a Select field", 400, None)

		options = field.options.split("\n")
		return response("Operation Successful", 200, options)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), _("Error while fetching issue type (Employee Checkin Issue)"))
		return response("Internal Server Error", 500, None, str(e))



@frappe.whitelist(methods=["POST"])
def get_checkin_issue_list(employee_id: str):
	try:
		if not employee_id:
			return response("error", 400, {}, "Employee ID is required.")
		employee = frappe.db.get_value("Employee", {"employee_id": employee_id}, ["name", "user_id"], as_dict=1)
		if employee:
			my_checkin_issues = frappe.db.get_list("Employee Checkin Issue", {"employee": employee.name}, ["name", "employee_name", "workflow_state", "log_type", "issue_type", "date"], order_by='creation desc')
			reports_to_issues = frappe.db.get_list("Employee Checkin Issue", {"shift_supervisor": employee.name}, ["name", "employee_name", "workflow_state", "log_type", "issue_type", "date"], order_by='creation desc')

			data = {
				"my_checkin_issues": my_checkin_issues,
				"reports_to_issues": reports_to_issues
			}
			return response("Operation Successful", 200, data, None)
		return response("Resource not found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), _("Error while fetching Employee Checkin Issue"))
		return response("Internal Server Error", 500, None, str(e))