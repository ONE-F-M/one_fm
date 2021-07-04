from datetime import timedelta
import itertools

import frappe
from frappe import _
from frappe.utils import cstr, cint, get_datetime, getdate, add_to_date
from frappe.core.doctype.version.version import get_diff
from erpnext.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings, get_actual_start_end_datetime_of_shift
from one_fm.operations.doctype.operations_site.operations_site import create_notification_log
import datetime
from frappe.permissions import remove_user_permission

#Shift Type
@frappe.whitelist()
def naming_series(doc, method):
	doc.name = doc.name+"|"+doc.shift_type+"|"+doc.start_time+"-"+doc.end_time+"|"+cstr(doc.duration)+" hours"


#Operations Shift
def shift_after_insert(doc, method):
	shift_type = frappe.get_doc("Shift Type", doc.shift_type)
	start_time = get_datetime(doc.start_time) + timedelta(minutes=shift_type.notification_reminder_after_shift_start)
	if doc.start_time <= doc.end_time:
		pass
	elif doc.start_time > doc.end_time:
		pass 

#Employee Checkin
def employee_checkin_validate(doc, method):
	try:
		perm_map = {
			"IN" : "Arrive Late",
			"OUT": "Leave Early"
		}
		existing_perm = None
		checkin_time = get_datetime(doc.time)
		shift_actual_timings = get_actual_start_end_datetime_of_shift(doc.employee, get_datetime(doc.time), True)
		prev_shift, curr_shift, next_shift = get_employee_shift_timings(doc.employee, get_datetime(doc.time))
		if curr_shift:
			existing_perm = frappe.db.exists("Shift Permission", {"date": curr_shift.start_datetime.strftime('%Y-%m-%d'), "employee": doc.employee, "permission_type": perm_map[doc.log_type], "workflow_state": "Approved"})
			assignment, shift_type = frappe.get_value("Shift Assignment", {"employee": doc.employee, "date": curr_shift.start_datetime.date(), "shift_type": curr_shift.shift_type.name}, ["shift", "shift_type"])
			doc.operations_shift = assignment
			doc.shift_type = shift_type
	
		if shift_actual_timings[0] and shift_actual_timings[1]:
			if existing_perm:
				perm_doc = frappe.get_doc("Shift Permission", existing_perm)
				permitted_time = get_datetime(perm_doc.date) + (perm_doc.arrival_time if doc.log_type == "IN" else perm_doc.leaving_time)
				if doc.log_type == "IN" and (checkin_time <= permitted_time and checkin_time >= curr_shift.start_datetime):
					doc.time = 	curr_shift.start_datetime
					doc.skip_auto_attendance = 0
					doc.shift_permission = existing_perm
				elif doc.log_type == "OUT" and (checkin_time >= permitted_time and checkin_time <= curr_shift.start_datetime):
					doc.time = 	curr_shift.end_datetime
					doc.skip_auto_attendance = 0
					doc.shift_permission = existing_perm
	except Exception as e:
		frappe.throw(frappe.get_traceback())

@frappe.whitelist()
def checkin_after_insert(doc, method):
	print("CALLED CHECKIN AFTER INSERT")
	# These are returned according to dates. Time is not taken into account
	prev_shift, curr_shift, next_shift = get_employee_shift_timings(doc.employee, get_datetime(doc.time))
	
	# In case of back to back shift
	if doc.shift_type:
		shift_doc = frappe.get_doc("Shift Type", doc.shift_type)
		curr_shift = frappe._dict({
			'actual_start': doc.shift_actual_start,
			'actual_end': doc.shift_actual_end, 
			'end_datetime': doc.shift_end, 
			'start_datetime': doc.shift_start, 
			'shift_type': shift_doc
		})
	# print("72", prev_shift.end_datetime, curr_shift.end_datetime, next_shift.end_datetime)
	if curr_shift:
		shift_type = frappe.get_doc("Shift Type", curr_shift.shift_type.name)
		supervisor_user = get_notification_user(doc, doc.employee)
		distance, radius = validate_location(doc)
		message_suffix = _("Location logged is inside the site.") if distance <= radius else _("Location logged is {location}m outside the site location.").format(location=cstr(cint(distance)- radius))

		if doc.log_type == "IN" and doc.skip_auto_attendance == 0:
			#EARLY: Checkin time is before [Shift Start - Variable Checkin time] 
			if get_datetime(doc.time) < get_datetime(curr_shift.actual_start):
				time_diff = get_datetime(curr_shift.start_datetime) - get_datetime(doc.time)
				hrs, mins, secs = cstr(time_diff).split(":")
				early = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
				subject = _("{employee} has checked in early by {early}. {location}".format(employee=doc.employee_name, early=early, location=message_suffix))
				message = _("{employee} has checked in early by {early}. {location}".format(employee=doc.employee_name, early=early, location=message_suffix))
				for_users = [supervisor_user]
				create_notification_log(subject, message, for_users, doc)

			# ON TIME
			elif get_datetime(doc.time) >= get_datetime(doc.shift_actual_start) and get_datetime(doc.time) <= (get_datetime(doc.shift_start) + timedelta(minutes=shift_type.late_entry_grace_period)):
				subject = _("{employee} has checked in on time. {location}".format(employee=doc.employee_name, location=message_suffix))
				message = _("{employee} has checked in on time. {location}".format(employee=doc.employee_name, location=message_suffix))
				for_users = [supervisor_user]
				create_notification_log(subject, message, for_users, doc)

			# LATE: Checkin time is after [Shift Start + Late Grace Entry period]
			elif get_datetime(doc.time) > (get_datetime(doc.shift_start) + timedelta(minutes=shift_type.late_entry_grace_period)):
				time_diff = get_datetime(doc.time) - get_datetime(doc.shift_start)
				hrs, mins, secs = cstr(time_diff).split(":")
				delay = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
				subject = _("{employee} has checked in late by {delay}. {location}".format(employee=doc.employee_name, delay=delay, location=message_suffix))
				message = _("{employee_name} has checked in late by {delay}. {location} <br><br><div class='btn btn-primary btn-danger late-punch-in' id='{employee}_{date}_{shift}'>Issue Penalty</div>".format(employee_name=doc.employee_name,shift=doc.shift, date=cstr(doc.time), employee=doc.employee, delay=delay, location=message_suffix))
				for_users = [supervisor_user]
				create_notification_log(subject, message, for_users, doc)

		elif doc.log_type == "IN" and doc.skip_auto_attendance == 1:
			subject = _("Hourly Report: {employee} checked in at {time}. {location}".format(employee=doc.employee_name, time=doc.time, location=message_suffix))
			message = _("Hourly Report: {employee} checked in at {time}. {location}".format(employee=doc.employee_name, time=doc.time, location=message_suffix))
			for_users = [supervisor_user]
			create_notification_log(subject, message, for_users, doc)

		elif doc.log_type == "OUT":
			# Automatic checkout
			if not doc.device_id:
				from one_fm.api.tasks import send_notification
				subject = _("Automated Checkout: {employee} forgot to checkout.".format(employee=doc.employee_name))
				message = _('<a class="btn btn-primary" href="/desk#Form/Employee Checkin/{name}">Review check out</a>&nbsp;'.format(name=doc.name))
				for_users = [supervisor_user]
				print("124", doc.employee, supervisor_user)
				send_notification(subject, message, for_users)
			#EARLY: Checkout time is before [Shift End - Early grace exit time] 
			elif doc.device_id and get_datetime(doc.time) < (get_datetime(curr_shift.end_datetime) - timedelta(minutes=shift_type.early_exit_grace_period)):
				time_diff = get_datetime(curr_shift.end_datetime) - get_datetime(doc.time)
				hrs, mins, secs = cstr(time_diff).split(":")
				early = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
				subject = _("{employee} has checked out early by {early}. {location}".format(employee=doc.employee_name, early=early, location=message_suffix))
				message = _("{employee_name} has checked out early by {early}. {location} <br><br><div class='btn btn-primary btn-danger early-punch-out' id='{employee}_{date}_{shift}'>Issue Penalty</div>".format(employee_name=doc.employee_name, shift=doc.shift, date=cstr(doc.time), employee=doc.employee_name, early=early, location=message_suffix))
				for_users = [supervisor_user]
				create_notification_log(subject, message, for_users, doc)

			# ON TIME
			elif doc.device_id and get_datetime(doc.time) <= get_datetime(doc.shift_actual_end) and get_datetime(doc.time) >= (get_datetime(doc.shift_end) - timedelta(minutes=shift_type.early_exit_grace_period)):
				subject = _("{employee} has checked out on time. {location}".format(employee=doc.employee_name, location=message_suffix))
				message = _("{employee} has checked out on time. {location}".format(employee=doc.employee_name, location=message_suffix))
				for_users = [supervisor_user]
				create_notification_log(subject, message, for_users, doc)

			# LATE: Checkin time is after [Shift End + Variable checkout time]
			elif doc.device_id and get_datetime(doc.time) > get_datetime(doc.shift_actual_end):
				time_diff = get_datetime(doc.time) - get_datetime(doc.shift_end)
				hrs, mins, secs = cstr(time_diff).split(":")
				delay = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
				subject = _("{employee} has checked out late by {delay}. {location}".format(employee=doc.employee_name, delay=delay, location=message_suffix))
				message = _("{employee} has checked out late by {delay}. {location}".format(employee=doc.employee_name, delay=delay, location=message_suffix))
				for_users = [supervisor_user]
				create_notification_log(subject, message, for_users, doc)
	else:
		# When no shift assigned, supervisor of active shift of the nearest site is sent a notification about unassigned checkin.
		location = doc.device_id
		# supervisor = get_closest_location(doc.time, location)
		reporting_manager = frappe.get_value("Employee", {"user_id": doc.owner}, "reports_to")
		supervisor = get_employee_user_id(reporting_manager)
		if supervisor:
			subject = _("{employee} has checked in on an unassigned shift".format(employee=doc.employee_name))
			message = _("{employee} has checked in on an unassigned shift".format(employee=doc.employee_name))
			for_users = [supervisor]
			create_notification_log(subject, message, for_users, doc)


def get_notification_user(doc, employee=None):
	"""
		Shift > Site > Project > Reports to
	"""
	operations_shift = frappe.get_doc("Operations Shift", doc.operations_shift)
	print(operations_shift.supervisor, operations_shift.name)
	if operations_shift.supervisor:
		supervisor = get_employee_user_id(operations_shift.supervisor)
		if supervisor != doc.owner:
			return supervisor
	
	operations_site = frappe.get_doc("Operations Site", operations_shift.site)
	print(operations_site.account_supervisor, operations_site.name)
	if operations_site.account_supervisor:
		account_supervisor = get_employee_user_id(operations_site.account_supervisor)
		if account_supervisor != doc.owner:
			return account_supervisor
	
	if operations_site.project:
		project = frappe.get_doc("Project", operations_site.project)
		print(project.account_manager, project.name)
		if project.account_manager:
			account_manager = get_employee_user_id(project.account_manager)
			if account_manager != doc.owner:
				return account_manager
	reporting_manager = frappe.get_value("Employee", {"name": employee}, "reports_to")
	print("191", employee, doc.owner, reporting_manager)
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

def get_employee_user_id(employee):
	return frappe.get_value("Employee", {"name": employee}, "user_id")

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


def employee_before_validate(doc, method):
	from erpnext.hr.doctype.employee.employee import Employee
	Employee.validate = employee_validate



def employee_validate(self):
	from erpnext.controllers.status_updater import validate_status
	validate_status(self.status, ["Active", "Court Case", "Absconding", "Left"])

	self.employee = self.name
	self.set_employee_name()
	self.validate_date()
	self.validate_email()
	self.validate_status()
	self.validate_reports_to()
	self.validate_preferred_email()
	if self.job_applicant:
		self.validate_onboarding_process()

	if self.user_id:
		self.validate_user_details()
	else:
		existing_user_id = frappe.db.get_value("Employee", self.name, "user_id")
		if existing_user_id:
			remove_user_permission(
				"Employee", self.name, existing_user_id)

#Training Result
@frappe.whitelist()
def update_certification_data(doc, method):
	""" 
	This function adds/updates the Training Program Certificate doctype 
	by checking the pass/fail criteria of the employees based on the Training Result. 
	Also adds the certificate to the Employee Skill Map.
	"""
	passed_employees = []
	
	training_program_name, has_certificate, min_score, validity, company, trainer_name, trainer_email = frappe.db.get_value("Training Event", {'event_name': doc.training_event}, ["training_program", "has_certificate", "minimum_score", "validity", "company", "trainer_name", "trainer_email"])	
	
	if has_certificate:
		issue_date = cstr(getdate())
		if validity:
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