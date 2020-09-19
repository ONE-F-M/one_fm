import frappe
from frappe import _
from frappe.utils import getdate, cint, cstr, random_string
from frappe.client import get_list
import pandas as pd
import json, base64, ast
from frappe.client import attach_file
from one_fm.one_fm.page.roster.roster import get_post_view as _get_post_view, get_roster_view as _get_roster_view

@frappe.whitelist(allow_guest=True)
def get_roster_view(start_date, end_date, all=1, assigned=0, scheduled=0, project=None, site=None, shift=None, department=None, post_type=None):
	try:
		return _get_roster_view(start_date, end_date, all, assigned, scheduled, project, site, shift, department, post_type)
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist(allow_guest=True)
def get_weekly_staff_roster(start_date, end_date):
	try:
		user, user_roles, user_employee = get_current_user_details()
		# user_employee = "HR-EMP-00026"
	
		roster = frappe.db.sql("""
			SELECT shift, employee, date, employee_availability, post_type
			FROM `tabRoster`
			WHERE employee="{emp}"
			AND date BETWEEN date("{start_date}") AND date("{end_date}")
		""".format(emp=user_employee, start_date=start_date, end_date=end_date), as_dict=1)
		print(roster)
		return roster
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_current_user_details():
	user = frappe.session.user
	user_roles = frappe.get_roles(user)
	user_employee = frappe.get_value("Employee", {"user_id": user}, ["name", "employee_name", "image", "enrolled"], as_dict=1)
	return user, user_roles, user_employee


@frappe.whitelist(allow_guest=True)
def get_post_view(start_date, end_date,  project=None, site=None, shift=None, post_type=None, active_posts=1):
	try:
		return _get_post_view(start_date, end_date, project, site, shift, post_type, active_posts)
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist(allow_guest=True)
def edit_post(post_type, shift, post_status, date_list, paid=0, repeat=None):
	"""
		post_status: Post Off/Suspend Post/Cancel Post
		date_list: List of dates
		paid: 1/0 if the changes are paid/unpaid
		repeat: If changes are to be repeated. List of dates when to repeat this.
	"""
	try:
		date_list = json.loads(date_list)
		for date in date_list:
			if frappe.db.exists("Post Schedule", {"date": date, "post_type": post_type, "shift": shift}):
				post_schedule = frappe.get_doc("Post Schedule", {"date": date, "post_type": post_type, "shift": shift})
			else:
				post_schedule = frappe.new_doc("Post Schedule")
				post_schedule.post = post_type
				post_schedule.date = date
			post_schedule.post_status = post_status
			if cint(paid):
				print("81",post_schedule.paid,post_schedule.unpaid)
				post_schedule.paid = 1
				post_schedule.unpaid = 0
			else:
				print("85",post_schedule.paid,post_schedule.unpaid)
				post_schedule.unpaid = 1
				post_schedule.paid = 0
			post_schedule.save(ignore_permissions=True)
			# print(post_schedule.as_dict())
		print(post_status, date_list, type(date_list))
		frappe.db.commit()

	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_unassigned_project_employees(project, date, limit_start=None, limit_page_length=20):
	try:
		#Todo add date range
		return frappe.get_list("Employee", fields=["name", "employee_name"], filters={"project": project}, order_by="name asc",
			limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True)
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)	


@frappe.whitelist()
def get_assigned_employees(shift, date, limit_start=None, limit_page_length=20):
	try:
		#Todo add date range
		return frappe.get_list("Roster", fields=["employee", "employee_name", "post_type"], filters={"shift": shift, "date": date}, order_by="employee_name asc",
			limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True)
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_assigned_projects(employee_id):
	try:
		user, user_roles, user_employee = get_current_user_details()
		if "Operations Manager" in user_roles:
			return frappe.get_list("Project", {"project_type": "External"}, limit_page_length=9999)

		if "Projects Manager" in user_roles:
			return frappe.get_list("Project", {"account_manager": employee_id}, limit_page_length=9999)
		return []
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)
	

@frappe.whitelist()
def get_assigned_sites(employee_id, project=None):
	try:
		user, user_roles, user_employee = get_current_user_details()
		print(user_roles)
		if project is None and ("Operations Manager" in user_roles or "Projects Manager" in user_roles):
			return frappe.get_list("Operations Site", limit_page_length=9999)

		if "Operations Manager" in user_roles or "Projects Manager" in user_roles:
			print(frappe.get_list("Operations Site", {"project": project}))
			return frappe.get_list("Operations Site", {"project": project}, limit_page_length=9999)

		if "Site Supervisor" in user_roles:
			return frappe.get_list("Operations Site", {"project": project, "account_supervisor": employee_id}, limit_page_length=9999)
		return []
	
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)
	

@frappe.whitelist()
def get_assigned_shifts(employee_id, site=None):
	try:
		user, user_roles, user_employee = get_current_user_details()
		print(user_roles)
		if site is None and ("Operations Manager" in user_roles or "Projects Manager" in user_roles or "Site Supervisor" in user_roles):
			return frappe.get_list("Operations Shift", limit_page_length=9999)

		if "Operations Manager" in user_roles or "Projects Manager" in user_roles or "Site Supervisor" in user_roles:
			print(frappe.get_list("Operations Shift", {"site": site}))
			return frappe.get_list("Operations Shift", {"site": site}, limit_page_length=9999)

		if "Shift Supervisor" in user_roles:
			return frappe.get_list("Operations Shift", {"site": site, "supervisor": employee_id}, limit_page_length=9999)
		return []
	
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_departments():
	try:
		print(frappe.get_list("Department", limit_page_length=9999))
		return frappe.get_list("Department",{"is_group": 0}, limit_page_length=9999)
	
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_post_types(shift=None):
	try:
		user, user_roles, user_employee = get_current_user_details()
		print(user_roles)

		if shift is None and ("Operations Manager" in user_roles or "Projects Manager" in user_roles or "Site Supervisor" in user_roles):
			return frappe.get_list("Post Type", limit_page_length=9999)

		if "Operations Manager" in user_roles or "Projects Manager" in user_roles or "Site Supervisor" in user_roles or "Shift Supervisor" in user_roles:
			return frappe.get_list("Operations Post",{"site_shift": shift}, "post_template",limit_page_length=9999)

		return []

	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_post_details(post_name):
	try:
		return frappe.get_value("Operations Post", post_name, "*")
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist(allow_guest=True)
def unschedule_staff(employee, start_date, end_date=None, never_end=0):
	try:
		if never_end:
			rosters = frappe.get_all("Employee Schedule", {"employee": employee,"date": ('>=', start_date)})
			for roster in rosters:
				frappe.delete_doc("Employee Schedule", roster.name, ignore_permissions=True)
			return True
		else:
			for date in	pd.date_range(start=start_date, end=end_date):
				if frappe.db.exists("Employee Schedule", {"employee": employee, "date":  cstr(date.date())}):
					roster = frappe.get_doc("Employee Schedule", {"employee": employee, "date":  cstr(date.date())})
					frappe.delete_doc("Employee Schedule", roster.name, ignore_permissions=True)
			return True
	except Exception as e:
		print(e)
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist(allow_guest=True)
def schedule_staff(employee, shift, post_type, start_date, end_date=None, never=0, day_off=None):
	try:
		print(getdate(start_date).strftime('%A'))
		# print(employee, shift, post_type, start_date, end_date=None, never=0, day_off=None)
		if never:
			end_date = cstr(getdate().year) + '-12-31'
			print(end_date)
			for date in	pd.date_range(start=start_date, end=end_date):
				if frappe.db.exists("Employee Schedule", {"employee": employee, "date": cstr(date.date())}):
					roster = frappe.get_doc("Employee Schedule", {"employee": employee, "date": cstr(date.date())})
				else:
					roster = frappe.new_doc("Employee Schedule")
					roster.employee = employee
					roster.date = cstr(date.date())
				
				if day_off and date.date().strftime('%A') == day_off:
					roster.employee_availability = "Day Off"				
				else:
					roster.employee_availability = "Working"
					roster.shift = shift
					roster.post_type = post_type
				print(roster.as_dict())
				roster.save(ignore_permissions=True)
			return True
		else:		
			for date in	pd.date_range(start=start_date, end=end_date):
				if frappe.db.exists("Employee Schedule", {"employee": employee, "date":  cstr(date.date())}):
					roster = frappe.get_doc("Employee Schedule", {"employee": employee, "date":  cstr(date.date())})
				else:
					roster = frappe.new_doc("Employee Schedule")
					roster.employee = employee
					roster.date =  cstr(date.date())
				if day_off and date.date().strftime('%A') == day_off:
					roster.employee_availability = "Day Off"				
				else:
					roster.employee_availability = "Working"
					roster.shift = shift
					roster.post_type = post_type
					roster.post_type = post_type
				print(roster.as_dict())
				roster.save(ignore_permissions=True)
			return True
	except Exception as e:
		frappe.log_error(e)
		frappe.throw(_(e))


@frappe.whitelist(allow_guest=True)
def schedule_leave(employee, leave_type, start_date, end_date):
	try:
		for date in	pd.date_range(start=start_date, end=end_date):
			print(employee, date.date())
			if frappe.db.exists("Employee Schedule", {"employee": employee, "date": cstr(date.date())}):
				roster = frappe.get_doc("Employee Schedule", {"employee": employee, "date":  cstr(date.date())})
				roster.shift = None
				roster.shift_type = None
				roster.project = None
				roster.site = None
			else:
				roster = frappe.new_doc("Employee Schedule")
				roster.employee = employee
				roster.date =  cstr(date.date())
			roster.employee_availability = leave_type
			roster.save(ignore_permissions=True)
		return True
	except Exception as e:
		print(e)
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def post_handover(post, date, initiated_by, handover_to, docs_check, equipment_check, items_check, docs_comment=None, equipment_comment=None, items_comment=None, attachments=[]):
	try:
		handover = frappe.new_doc("Post Handover")
		handover.post = post
		handover.date = date
		handover.initiated_by = initiated_by
		handover.handover_to = handover_to
		handover.docs_check = docs_check
		handover.equipment_check = equipment_check
		handover.items_check = items_check
		handover.docs_comment = docs_comment
		handover.equipment_comment = equipment_comment
		handover.items_comment = items_comment
		handover.save()

		for attachment in ast.literal_eval(attachments):
			attach_file(filename=random_string(6)+".jpg", filedata=base64.b64decode(attachment), doctype=handover.doctype, docname=handover.name)

		return True
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_handover_posts(shift=None):
	try:
		filters = {"handover": 1}
		if shift:
			filters.update({"site_shift": shift})
		return frappe.get_list("Operations Post", filters)
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def get_report_comments(report_name):
	try:
		comments = frappe.get_list("Comment", {"reference_doctype": "Shift Report", "reference_name": report_name, "comment_type": "Comment"}, "*")
		return comments
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)