from datetime import timedelta
import itertools

import frappe
from frappe import _
from frappe.utils import cstr, cint, get_datetime
from frappe.core.doctype.version.version import get_diff
from erpnext.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings
from one_fm.operations.doctype.operations_site.operations_site import create_notification_log

import datetime
import schedule, time
import rq
from redis import Redis
from rq import Queue, Worker
from rq.registry import StartedJobRegistry
from frappe.utils.background_jobs import get_redis_conn
from rq_scheduler import Scheduler

# @frappe.whitelist()
# def testing_scheduler():
# 	conn = Redis()
# 	print(conn)
# 	queuee = Queue('foo', connection=conn)
# 	queues = Queue.all(conn)
# 	workers = Worker.all(conn)
# 	utc_datetime = datetime.datetime.utcnow()
# 	print(utc_datetime.strftime("%Y-%m-%d %H:%M:%S"))
# 	print(get_datetime())
# 	scheduler = Scheduler(queue=queuee)
# 	# print(queuee.name, StartedJobRegistry)
# 	scheduler.enqueue_at(get_datetime(), hello) # Date time should be in UTC

# 	for queue in queues:
# 		registry = StartedJobRegistry(queue=queue)
# 		print(registry.get_job_ids())

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
@frappe.whitelist()
def checkin_after_insert(doc, method):
	shift_type = frappe.get_doc("Shift Type", doc.shift_type)
	operations_shift = frappe.get_doc("Operations Shift", doc.operations_shift)
	supervisor_user = get_employee_user_id(operations_shift.supervisor)
	prev_shift, curr_shift, next_shift = get_employee_shift_timings(doc.employee, get_datetime(doc.time))

	if curr_shift:	
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
		subject = _("{employee} has checked in on an unassigned shift.".format(employee=doc.employee_name))
		message = _("{employee} has checked in on an unassigned shift".format(employee=doc.employee_name))
		for_users = [supervisor_user]
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

