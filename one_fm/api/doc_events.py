from datetime import timedelta
import itertools

import frappe
from frappe import _
from frappe.utils import cstr, cint, get_datetime
from frappe.core.doctype.version.version import get_diff
from erpnext.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings, get_actual_start_end_datetime_of_shift
from one_fm.operations.doctype.operations_site.operations_site import create_notification_log
import datetime

#Shift Type
@frappe.whitelist()
def naming_series(doc, method):
	doc.name = doc.shift_type+"|"+doc.start_time+"-"+doc.end_time+"|"+cstr(doc.duration)+" hours"


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
		checkin_time = get_datetime(doc.time)
		shift_actual_timings = get_actual_start_end_datetime_of_shift(doc.employee, get_datetime(doc.time), True)
		prev_shift, curr_shift, next_shift = get_employee_shift_timings(doc.employee, get_datetime(doc.time))
		if curr_shift:
			existing_perm = frappe.db.exists("Shift Permission", {"date": curr_shift.start_datetime.strftime('%Y-%m-%d'), "employee": doc.employee, "permission_type": perm_map[doc.log_type], "workflow_state": "Approved"})
			assignment = frappe.get_value("Shift Assignment", {"employee": doc.employee, "date": curr_shift.start_datetime.date(), "shift_type": curr_shift.shift_type.name}, "shift")
			doc.operations_shift = assignment
	
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

	if curr_shift:
		shift_type = frappe.get_doc("Shift Type", curr_shift.shift_type.name)
		operations_shift = frappe.get_doc("Operations Shift", doc.operations_shift)
		supervisor_user = get_employee_user_id(operations_shift.supervisor)

		if doc.log_type == "IN" and doc.skip_auto_attendance == 0:
			#EARLY: Checkin time is before [Shift Start - Variable Checkin time] 
			if get_datetime(doc.time) < get_datetime(curr_shift.actual_start):
				time_diff = get_datetime(curr_shift.start_datetime) - get_datetime(doc.time)
				hrs, mins, secs = cstr(time_diff).split(":")
				delay = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
				subject = _("{employee} has checked in early by {delay}.".format(employee=doc.employee_name, delay=delay))
				message = _("{employee} has checked in early by {delay}.".format(employee=doc.employee_name, delay=delay))
				for_users = [supervisor_user]
				create_notification_log(subject, message, for_users, doc)

			# ON TIME
			elif get_datetime(doc.time) >= get_datetime(doc.shift_actual_start) and get_datetime(doc.time) <= (get_datetime(doc.shift_start) + timedelta(minutes=shift_type.late_entry_grace_period)):
				print(doc.time, doc.shift_actual_start, doc.time, cstr((get_datetime(doc.shift_start) + timedelta(minutes=shift_type.late_entry_grace_period))))
				subject = _("{employee} has checked in on time.".format(employee=doc.employee_name))
				message = _("{employee} has checked in on time.".format(employee=doc.employee_name))
				for_users = [supervisor_user]
				create_notification_log(subject, message, for_users, doc)

			# LATE: Checkin time is after [Shift Start + Late Grace Entry period]
			elif get_datetime(doc.time) > (get_datetime(doc.shift_start) + timedelta(minutes=shift_type.late_entry_grace_period)):
				time_diff = get_datetime(doc.time) - get_datetime(doc.shift_start)
				hrs, mins, secs = cstr(time_diff).split(":")
				delay = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
				subject = _("{employee} has checked in late by {delay}.".format(employee=doc.employee_name, delay=delay))
				message = _("{employee} has checked in late by {delay}.".format(employee=doc.employee_name, delay=delay))
				for_users = [supervisor_user]
				create_notification_log(subject, message, for_users, doc)

		elif doc.log_type == "OUT":
			#EARLY: Checkout time is before [Shift End - Early grace exit time] 
			if get_datetime(doc.time) < (get_datetime(curr_shift.end_datetime) - timedelta(minutes=shift_type.early_exit_grace_period)):
				time_diff = get_datetime(curr_shift.end_datetime) - get_datetime(doc.time)
				hrs, mins, secs = cstr(time_diff).split(":")
				delay = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
				subject = _("{employee} has checked out early by {delay}.".format(employee=doc.employee_name, delay=delay))
				message = _("{employee} has checked out early by {delay}.".format(employee=doc.employee_name, delay=delay))
				for_users = [supervisor_user]
				create_notification_log(subject, message, for_users, doc)

			# ON TIME
			elif get_datetime(doc.time) <= get_datetime(doc.shift_actual_end) and get_datetime(doc.time) >= (get_datetime(doc.shift_end) - timedelta(minutes=shift_type.early_exit_grace_period)):
				subject = _("{employee} has checked out on time.".format(employee=doc.employee_name))
				message = _("{employee} has checked out on time.".format(employee=doc.employee_name))
				for_users = [supervisor_user]
				create_notification_log(subject, message, for_users, doc)

			# LATE: Checkin time is after [Shift End + Variable checkout time]
			elif get_datetime(doc.time) > get_datetime(doc.shift_actual_end):
				time_diff = get_datetime(doc.time) - get_datetime(doc.shift_end)
				hrs, mins, secs = cstr(time_diff).split(":")
				delay = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
				subject = _("{employee} has checked out late by {delay}.".format(employee=doc.employee_name, delay=delay))
				message = _("{employee} has checked out late by {delay}.".format(employee=doc.employee_name, delay=delay))
				for_users = [supervisor_user]
				create_notification_log(subject, message, for_users, doc)
	else:
		# When no shift assigned, supervisor of active shift of the nearest site is sent a notification about unassigned checkin.
		location = doc.device_id
		supervisor = get_closest_location(doc.time, location)
		if supervisor:
			subject = _("{employee} has checked in on an unassigned shift.".format(employee=doc.employee_name))
			message = _("{employee} has checked in on an unassigned shift".format(employee=doc.employee_name))
			for_users = [supervisor]
			create_notification_log(subject, message, for_users, doc)


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
	# latitude, longitude = (13.039907,77.621564)  #
	# time = get_datetime('2020-06-04 00:18:46').strftime("%Y-%m-%d %H:%M")

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
