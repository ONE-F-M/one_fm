import frappe
from frappe import _
from frappe.utils import getdate, cint
from frappe.client import get_list
import json

@frappe.whitelist()
def get_roster(date, project=None, site=None, department=None, shift=None, post_type=None):
	try:
		user, user_roles, user_employee = get_current_user_details()
		if user_employee:
			if "Shift Supervisor" in user_roles:
				get_shift_supervisor_data(date, user_employee)
			if "Site Supervisor" in user_roles:
				get_site_supervisor_data(date, user_employee)
			if "Project Manager" in user_roles:
				get_project_manager_data(date, user_employee)
			if "Operations Manager" in user_roles:
				get_operations_manager_data(date, user_employee)
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)


def get_shift_supervisor_data(start_date, user_employee, shift=None, post_type=None):
	try:
		#Post Type > Employees
		filters = {"supervisor": user_employee}
		if shift:
			filters.update({"shift": shift})
		shifts_list = frappe.get_list("Operations Shift", filters)
		for shift in shifts_list:
			return frappe.get_list("Roster", {"date": start_date, "shift": shift}, ["employee_name", "availability", "post_type", "shift", "date"])
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)

def get_site_supervisor_data(start_date, user_employee, site=None, department=None, shift=None, post_type=None):
	filters = {"account_supervisor": user_employee}
	if site:
		filters.update({"name": site})
	sites_list = frappe.get_list("Operations Site", filters)
	

def get_project_manager_data(start_date, user_employee, project=None, site=None, department=None, shift=None, post_type=None):
	pass

def get_operations_manager_data(start_date, user_employee, project=None, site=None, department=None, shift=None, post_type=None):
	pass


@frappe.whitelist()
def get_weekly_staff_roster(start_date, end_date):
	try:
		user, user_roles, user_employee = get_current_user_details()
		user_employee = "HR-EMP-00026"
	
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

def get_current_user_details():
	user = frappe.session.user
	user_roles = frappe.get_roles(user)
	user_employee = frappe.get_value("Employee", {"user_id": user})
	return user, user_roles, user_employee


@frappe.whitelist()
def get_post_view(start_date, end_date, project=None, site=None, shift=None, department=None, post_type=None):
	try:
		start_date = getdate(start_date)
		end_date = getdate(end_date)
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

@frappe.whitelist(allow_guest=True)
def unschedule_staff(employee, date_list):
	try:
		date_list = json.loads(date_list)
		for date in date_list:
			if frappe.db.exists("Roster", {"employee": employee, "date": date}):
				roster = frappe.get_doc("Roster", {"employee": employee, "date": date})
				frappe.delete_doc("Roster", roster.name, ignore_permissions=True)

	except Exception as e:
		print(e)
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist(allow_guest=True)
def schedule_staff(employee, shift, post_type, date_list, day_off=[]):
	try:
		date_list = json.loads(date_list)
		for date in date_list:
			if frappe.db.exists("Roster", {"employee": employee, "date": date}):
				roster = frappe.get_doc("Roster", {"employee": employee, "date": date})
			else:
				roster = frappe.new_doc("Roster")
				roster.employee = employee
				roster.date = date
			roster.shift = shift
			roster.post_type = post_type
			roster.save(ignore_permissions=True)
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
