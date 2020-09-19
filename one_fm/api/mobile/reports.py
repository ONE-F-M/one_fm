import frappe
from frappe.utils import cstr, cint, getdate, random_string
import json, base64, ast
from frappe.client import attach_file
from frappe.desk.form.load import get_attachments
from one_fm.api.mobile.roster import get_current_user_details
from frappe.desk.form.assign_to import add as assign_to
from frappe.desk.form.utils import add_comment

@frappe.whitelist()
def get_my_reports():
	try:
		user, user_roles, user_employee = get_current_user_details()
		return frappe.get_list("Shift Report", {"owner": user}, order_by="creation desc")
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)

@frappe.whitelist()
def get_shift_reports(shift):
	try:
		return frappe.get_list("Shift Report", {"shift": shift}, order_by="creation desc")
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)

@frappe.whitelist()
def get_report_detail(report_name):
	try:
		shift_report = frappe.get_doc("Shift Report", report_name)
		return {
			'doc': shift_report,
			'attachments': get_attachments(shift_report.doctype, shift_report.name)
		}
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)	

@frappe.whitelist()
def create_shift_report(shift, department, subject, report_type, importance, comments, request_for_action, attachments=[]):
	try:
		shift_report = frappe.new_doc("Shift Report")
		shift_report.shift = shift
		shift_report.department = department
		shift_report.subject = subject
		shift_report.importance = importance
		shift_report.comments = comments
		shift_report.request_for_action = request_for_action
		shift_report.save()

		for attachment in ast.literal_eval(attachments):
			attach_file(filename=random_string(6)+".jpg", filedata=base64.b64decode(attachment), doctype=shift_report.doctype, docname=shift_report.name)

		return {
			'doc': shift_report,
			'attachments': get_attachments(shift_report.doctype, shift_report.name)
		}
	except Exception as e:
		print(e)
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def delete_shift_report(report_name):
	try:
		frappe.delete_doc("Shift Report", report_name, ignore_permissions=True)
		return True
	except Exception as e:
		print(e)
		return frappe.utils.response.report_error(e.http_status_code)
		

@frappe.whitelist()
def edit_shift_report(report_name, importance=None, report_type=None, comments=None, request_for_action=None, images=[]):
	try:
		shift_report = frappe.get_doc("Shift Report", report_name)
		if importance:
			shift_report.importance = importance
		if report_type:
			shift_report.report_type = report_type
		if comments:
			shift_report.comments = comments
		if request_for_action:
			shift_report.request_for_action = request_for_action
		if len(images) > 0:
			attachments = get_attachments(shift_report.doctype, shift_report.name)
			images = json.loads(images)
			diff = [i for i in images + attachments if i not in images or i not in attachments]
			result = len(diff) == 0
		if not result:
			for image in diff:
				frappe.delete_doc("File", image["name"])
		return True

	except Exception as e:
		print(e)
		return frappe.utils.response.report_error(e.http_status_code)
		

@frappe.whitelist()
def add_report_comment(report_name, content):
	try:
		user, user_roles, user_employee = get_current_user_details()
		print(report_name, content, user)
		add_comment("Shift Report", report_name, content, user)
		return True
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)

