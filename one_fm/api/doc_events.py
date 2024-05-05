from datetime import timedelta
from uuid import uuid4
import itertools

import frappe, erpnext
from frappe import _
from frappe.utils import cstr, cint, get_datetime, getdate, add_to_date
from frappe.core.doctype.version.version import get_diff
from one_fm.operations.doctype.operations_site.operations_site import create_notification_log
import datetime
from frappe.permissions import remove_user_permission
from hrms.hr.utils import get_holidays_for_employee

#Shift Type
@frappe.whitelist()
def naming_series(doc, method):
		if frappe.db.exists("Shift Type", {'name':doc.shift_type+"|"+doc.start_time+"-"+doc.end_time+"|"+cstr(doc.duration)+" hours"}):
			frappe.throw(doc.shift_type+"|"+doc.start_time+"-"+doc.end_time+"|"+cstr(doc.duration)+" hours Already exists")
		doc.name = doc.shift_type+"|"+doc.start_time+"-"+doc.end_time+"|"+cstr(doc.duration)+" hours"


#Operations Shift
def shift_after_insert(doc, method):
	shift_type = frappe.get_doc("Shift Type", doc.shift_type)
	start_time = get_datetime(doc.start_time) + timedelta(minutes=shift_type.notification_reminder_after_shift_start)
	if doc.start_time <= doc.end_time:
		pass
	elif doc.start_time > doc.end_time:
		pass


def get_notification_user(doc, employee=None):
	"""
		Shift > Site > Project > Reports to
	"""
	if not doc.operations_shift:
		return
	
	operations_shift = frappe.get_doc("Operations Shift", doc.operations_shift)

	if operations_shift.supervisor:
		supervisor = get_employee_user_id(operations_shift.supervisor)
		if supervisor != doc.owner:
			return supervisor

	operations_site = frappe.get_doc("Operations Site", operations_shift.site)

	if operations_site.account_supervisor:
		account_supervisor = get_employee_user_id(operations_site.account_supervisor)
		if account_supervisor != doc.owner:
			return account_supervisor

	if operations_site.project:
		project = frappe.get_doc("Project", operations_site.project)
		if project.account_manager:
			account_manager = get_employee_user_id(project.account_manager)
			if account_manager != doc.owner:
				return account_manager
	reporting_manager = frappe.get_value("Employee", {"name": employee}, "reports_to")
	return get_employee_user_id(reporting_manager)

def validate_location(doc):
	checkin_lat, checkin_lng = doc.device_id.split(",") if doc.device_id else (0, 0)
	site_name = frappe.get_value("Operations Shift", doc.operations_shift, "site")
	site_location = frappe.get_value("Operations Site", site_name, "site_location")
	site_lat, site_lng, radius = frappe.get_value("Location", site_location, ["latitude","longitude", "geofence_radius"] )
	distance =  haversine(site_lat, site_lng, checkin_lat, checkin_lng)
	return distance, radius


# Project
@frappe.whitelist()
def project_on_update(doc, method):
	doc_before_save = doc.get_doc_before_save()
	notify_poc_changes(doc, doc_before_save)


def notify_poc_changes(doc, doc_before_save):
	changes = get_diff(doc_before_save, doc, for_child=True)
	if not changes and changes.changed:
		return

	# Variables needed for notification
	project = doc.name
	modified_by = doc.modified_by
	subject = "{modified_by} made some changes to {project} POC.".format(project=project, modified_by=modified_by)
	message = ''

	if changes.row_changed:
		for change in changes.row_changed:
			message = message + "Details of {poc_name} modified.\n".format(poc_name=doc.poc[change[1]].poc)
	if changes.added:
		for change in changes.added:
			if(change[0] == "poc"):
				message = message + "{poc_name} has been added as a POC.\n".format(poc_name=change[1].poc)
	if changes.removed:
		for change in changes.removed:
			if(change[0] == "poc"):
				message = message + "{poc_name} has been removed as a POC.\n".format(poc_name=change[1].poc)

	recipients = get_recipients(doc)
	create_notification_log(_(subject), _(message), recipients, doc)

def get_recipients(doc):
		"""
			Get line managers. Site Supervisor, Project Manager, Operations Manager.
		"""
		project_manager_user = get_employee_user_id(doc.account_manager)
		operations_manager = frappe.get_list("Employee", {"designation": "Operations Manager"}, ignore_permissions=True)
		recipient_list = []

		for manager in operations_manager:
			manager_user = get_employee_user_id(manager.name)
			recipient_list.append(manager_user)
		recipient_list.append(project_manager_user)
		return recipient_list

@frappe.whitelist()
def get_employee_user_id(employee):
	return frappe.get_value("Employee", {"name": employee}, ["user_id"])

def get_closest_location(time, location):
	time = get_datetime(time).strftime("%Y-%m-%d %H:%M")
	latitude, longitude = location.split(",")

	#Get the closest site according to the checkin location
	site = frappe.db.sql("""
		SELECT
			(((acos(
				sin(( {latitude} * pi() / 180))
				*
				sin(( loc.latitude * pi() / 180)) + cos(( {latitude} * pi() /180 ))
				*
				cos(( loc.latitude  * pi() / 180)) * cos((( {longitude} - loc.longitude) * pi()/180))
			))
			* 180/pi()) * 60 * 1.1515 * 1.609344 * 1000
			)AS distance, os.name FROM `tabLocation` AS loc, `tabOperations Site` AS os
		WHERE os.site_location = loc.name ORDER BY distance ASC """.format(latitude=latitude, longitude=longitude), as_dict=1)

	site_name = site[0].name
	# Unused for now
	distance = site[0].distance

	#Check for active shift at the closest site.
	active_shift = frappe.db.sql("""
		SELECT
			supervisor
		FROM `tabOperations Shift`
		WHERE
			site="{site_name}" AND
			CAST("{current_time}" as datetime)
			BETWEEN
				CAST(start_time as datetime)
			AND
				IF(end_time < start_time, DATE_ADD(CAST(end_time as datetime), INTERVAL 1 DAY), CAST(end_time as datetime))

	""".format(current_time=time, site_name=site_name), as_dict=1)

	if len(active_shift) > 0:
		# Return supervisor user and distance
		return get_employee_user_id(active_shift[0].supervisor)
	else:
		return ''


def haversine(ofc_lat, ofc_lng, emp_lat, emp_lng):
	"""
	Calculate the great circle distance between two points
	on the earth (specified in decimal degrees)
	"""
	from math import radians, cos, sin, asin, sqrt
	# convert decimal degrees to radians
	try:
		lon1, lat1, lon2, lat2 = map(
			radians, [float(ofc_lng), float(ofc_lat), float(emp_lng), float(emp_lat)])
		# haversine formula
		dlon = lon2 - lon1
		dlat = lat2 - lat1
		a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
		c = 2 * asin(sqrt(a))
		r = 6371000  # Radius of earth in meters. Use 3956 for miles or 6371 for kilometres
		return c * r
	except Exception as e:
		print(frappe.get_traceback())


#Training Result
@frappe.whitelist()
def update_certification_data(doc, method):
	"""
	This function adds/updates the Training Program Certificate doctype
	by checking the pass/fail criteria of the employees based on the Training Result.
	Also adds the training event data to the Employee Skill Map.
	"""
	passed_employees = []

	training_program_name, has_certificate, min_score, validity, company, trainer_name, trainer_email, end_datetime = frappe.db.get_value("Training Event", {'event_name': doc.training_event}, ["training_program", "has_certificate", "minimum_score", "validity", "company", "trainer_name", "trainer_email", "end_time"])

	if has_certificate:

		expiry_date = None
		issue_date = cstr(end_datetime).split(" ")[0]
		if validity > 0:
			expiry_date = add_to_date(issue_date, months=validity)

		for employee in doc.employees:
			if employee.grade and min_score and cint(employee.grade) >= min_score:
				passed_employees.append(employee.employee)

		for passed_employee in passed_employees:
			if frappe.db.exists("Training Program Certificate", {'training_program_name': training_program_name, 'employee': passed_employee}):
				update_training_program_certificate(training_program_name, passed_employee, issue_date, expiry_date)
			else:
				create_training_program_certificate(training_program_name, passed_employee, issue_date, expiry_date,company, trainer_name, trainer_email)

def update_training_program_certificate(training_program_name, passed_employee, issue_date, expiry_date=None):
	doc = frappe.get_doc("Training Program Certificate", {'training_program_name': training_program_name, 'employee': passed_employee})
	doc.issue_date = issue_date
	doc.expiry_date = expiry_date
	doc.save()

def create_training_program_certificate(training_program_name, passed_employee, issue_date, expiry_date=None, company=None, trainer_name=None, trainer_email=None):
	doc = frappe.new_doc("Training Program Certificate")
	doc.training_program_name = training_program_name
	doc.company = company
	doc.trainer_name = trainer_name
	doc.trainer_email = trainer_email
	doc.employee = passed_employee
	doc.issue_date = issue_date
	doc.expiry_date = expiry_date
	doc.save()


#Training Event
@frappe.whitelist()
def update_training_event_data(doc, method):
	for employee in doc.employees:
		if frappe.db.exists("Employee Skill Map", employee.employee):
			doc_esm = frappe.get_doc("Employee Skill Map", employee.employee)
			doc_esm.append("trainings",{
				'training': doc.event_name,
			})
			doc_esm.save()

def clear_cache(doc):
	if doc.has_value_changed('account_manager'):
		frappe.cache.delete_key('user_permissions')

def on_project_update_switch_shift_site_post_to_inactive(doc, method):
    clear_cache(doc)
    if doc.is_active == "No" and  doc.project_type == "External":
        list_of_shift = frappe.db.sql(f""" select name from `tabOperations Shift` where project = "{doc.name}" """)

        list_of_sites = frappe.db.sql(f""" select name from `tabOperations Site` where project = "{doc.name}" """)
        if list_of_sites:
            for site in list_of_sites:
                frappe.db.set_value("Operations Site", site, {
                    "status": "Inactive"
                })
		
        if list_of_shift:
            for shift in list_of_shift:
                frappe.db.set_value("Operations Shift", shift, {
                    "status": "Not Active"
                })

        list_of_role = frappe.db.sql(f""" select name from `tabOperations Role` where project = "{doc.name}" """)
        if list_of_role:
            for role in list_of_role:
                frappe.db.set_value("Operations Role", role, {
                    "is_active": False
                })

        list_of_post = frappe.db.sql(f""" select name from `tabOperations Post` where project = "{doc.name}" """)
        if list_of_post:
            for post in list_of_post:
                frappe.db.set_value("Operations Post", post, {
                    "status": "Inactive"
                })


