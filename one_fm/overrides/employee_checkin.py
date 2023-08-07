from datetime import timedelta, datetime
import random
from dateutil.parser import parse
import frappe
from frappe import _
from frappe.utils import cint, get_datetime, cstr, getdate, now_datetime, add_days, now, today
from hrms.hr.doctype.employee_checkin.employee_checkin import *
from one_fm.api.v1.roster import get_current_shift
from one_fm.api.tasks import send_notification, issue_penalty
from one_fm.operations.doctype.operations_site.operations_site import create_notification_log
from one_fm.api.doc_events import (
	get_notification_user, validate_location, get_employee_user_id,
)
from one_fm.api.api import push_notification_rest_api_for_checkin
from one_fm.processor import sendemail


perm_map = {
	"IN" : "Arrive Late",
	"OUT": "Leave Early"
}


class EmployeeCheckinOverride(EmployeeCheckin):
	#overrode employee checkin method
	@frappe.whitelist()
	def fetch_shift(self):
		pass

	def validate(self):
		validate_active_employee(self.employee)
		self.validate_duplicate_log()
		if frappe.db.get_single_value("HR and Payroll Additional Settings", 'validate_shift_permission_on_employee_checkin'):
			try:			
				existing_perm = None
				checkin_time = get_datetime(self.time)
				curr_shift = get_current_shift(self.employee)
				if curr_shift:
					curr_shift = curr_shift
					start_date = curr_shift["start_date"].strftime("%Y-%m-%d")
					existing_perm = frappe.db.sql(f""" select name from `tabShift Permission` where date = '{start_date}' and employee = '{self.employee}' and permission_type = '{perm_map[self.log_type]}' and workflow_state = 'Approved' """, as_dict=1)
					self.shift_assignment = curr_shift["name"]
					self.operations_shift = curr_shift["shift"]
					self.roster_type = curr_shift['roster_type']
					self.shift_type = curr_shift["shift_type"]

					if curr_shift["start_datetime"] and curr_shift["end_datetime"] and existing_perm:
						perm_doc = frappe.db.sql(f"""select date, arrival_time, leaving_time from `tabShift Permission` where name = %s """, existing_perm[0]["name"], as_dict=1)[0]
						permitted_time = get_datetime(perm_doc['date']) + (perm_doc["arrival_time"] if self.log_type == "IN" else perm_doc["leaving_time"])
						if self.log_type == "IN" and (checkin_time <= permitted_time and checkin_time >= curr_shift["start_datetime"]):
							self.time = curr_shift["start_datetime"]
							self.skip_auto_attendance = 0
							self.shift_permission = existing_perm[0]["name"]
						elif self.log_type == "OUT" and (checkin_time >= permitted_time and checkin_time <= curr_shift["start_datetime"]):
							self.time = curr_shift["end_datetime"]
							self.skip_auto_attendance = 0
							self.shift_permission = existing_perm[0]["name"]
			except Exception as e:
				frappe.throw(frappe.get_traceback())

	def validate_duplicate_log(self):
		doc = frappe.db.sql(f""" select name from `tabEmployee Checkin` where employee = '{self.employee}' and time = '{self.time}' and (NOT name = '{self.name}')""", as_dict=1)
		if doc:
			doc_link = frappe.get_desk_link("Employee Checkin", doc[0]["name"])
			frappe.throw(
				_("This employee already has a log with the same timestamp.{0}").format("<Br>" + doc_link)
			)
	def before_insert(self):
		self.date = str(self.time).split(' ')[0]
		if self.shift_permission:
			sp = frappe.get_doc("Shift Permission", self.shift_permission, ignore_permissions=True)
			sa = frappe.get_doc("Shift Assignment", sp.assigned_shift, ignore_permissions=True)
			self.shift_assignment = sa.name
			self.operations_shift = sa.shift
			self.shift_type = sa.shift_type
			self.shift_actual_start = sa.start_datetime
			self.shift_actual_end = sa.end_datetime

	def after_insert(self):
		frappe.db.commit()
		self.reload()
		if not (self.shift_assignment and self.shift_type and self.operations_shift and self.shift_actual_start and self.shift_actual_end):
			frappe.enqueue(after_insert_background, self=self.name)
		if self.log_type == "IN":
			frappe.enqueue(notify_supervisor_about_late_entry, checkin=self)

def after_insert_background(self):
	self = frappe.get_doc("Employee Checkin", self)
	try:
		# update shift if not exists
		curr_shift = get_current_shift(self.employee)
		if curr_shift:
			shift_type = frappe.db.sql(f"""SELECT * FROM `tabShift Type` WHERE name='{curr_shift.shift_type}' """, as_dict=1)[0]
			# calculate entry
			early_exit = 0
			late_entry = 0
			actual_time = str(self.time)
			if not '.' in actual_time:
				actual_time += '.000000'

			if self.log_type=='IN':
				if (datetime.strptime(actual_time, '%Y-%m-%d %H:%M:%S.%f') - timedelta(minutes=shift_type.late_entry_grace_period)) > curr_shift.start_datetime:
					late_entry = 1
			if self.log_type=='OUT':
				if (datetime.strptime(actual_time, '%Y-%m-%d %H:%M:%S.%f') + timedelta(minutes=shift_type.early_exit_grace_period)) < curr_shift.end_datetime:
					early_exit = 1

			query = f"""
				UPDATE `tabEmployee Checkin` SET
				shift_assignment="{curr_shift.name}", operations_shift="{curr_shift.shift}", shift_type='{curr_shift.shift_type}',
				shift='{curr_shift.shift_type}', shift_actual_start="{curr_shift.start_datetime}", shift_actual_end="{curr_shift.end_datetime}",
				shift_start="{curr_shift.start_datetime.date()}", shift_end="{curr_shift.end_datetime.date()}", early_exit={early_exit},
				late_entry={late_entry}, date='{curr_shift.start_date if self.log_type=='IN' else curr_shift.end_datetime}', 
				operations_site="{curr_shift.site}", post_abbrv="{curr_shift.post_abbrv}", project="{curr_shift.project}",
				company="{curr_shift.company}", operations_role="{curr_shift.operations_role}",
				roster_type='{curr_shift.roster_type}'
				WHERE name="{self.name}"
			"""
			frappe.db.sql(query, values=[], as_dict=1)
			frappe.db.commit()
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), 'Employee Checkin')
	
	# send notification
	# continue to notification
	# These are returned according to dates. Time is not taken into account
	
	start_time = get_datetime(cstr(getdate()) + " 00:00:00")
	end_time = get_datetime(cstr(getdate()) + " 23:59:59")

	log_exist = frappe.db.exists("Employee Checkin", {"log_type": self.log_type, "time": [ "between", (start_time, end_time)], "skip_auto_attendance": 0 ,"shift_type": self.shift_type, "name": ["!=", self.name]})

	if not log_exist:
		# In case of back to back shift
		if self.shift_type:
			shift_type = frappe.get_doc("Shift Type", self.shift_type)
			curr_shift = frappe._dict({
				'actual_start': self.shift_actual_start,
				'actual_end': self.shift_actual_end,
				'end_datetime': self.shift_end,
				'start_datetime': self.shift_start,
				'shift_type': shift_type
			})
			if curr_shift:
				supervisor_user = get_notification_user(self, self.employee)
				distance, radius = validate_location(self)
				message_suffix = _("Location logged is inside the site.") if distance <= radius else _("Location logged is {location}m outside the site location.").format(location=cstr(cint(distance)- radius))

				if self.log_type == "IN" and self.skip_auto_attendance == 0:
					# LATE: Checkin time is after [Shift Start + Late Grace Entry period]
					if shift_type.enable_entry_grace_period == 1 and get_datetime(self.time) > (get_datetime(self.shift_start) + timedelta(minutes=shift_type.late_entry_grace_period)):
						time_diff = get_datetime(self.time) - get_datetime(self.shift_start)
						hrs, mins, secs = cstr(time_diff).split(":")
						delay = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
						subject = _("{employee} has checked in late by {delay}. {location}".format(employee=self.employee_name, delay=delay, location=message_suffix))
						message = _("{employee_name} has checked in late by {delay}. {location} <br><br><div class='btn btn-primary btn-danger late-punch-in' id='{employee}_{date}_{shift}'>Issue Penalty</div>".format(employee_name=self.employee_name,shift=self.operations_shift, date=cstr(self.time), employee=self.employee, delay=delay, location=message_suffix))
						for_users = [supervisor_user]
						create_notification_log(subject, message, for_users, self)

				elif self.log_type == "IN" and self.skip_auto_attendance == 1:
					subject = _("Hourly Report: {employee} checked in at {time}. {location}".format(employee=self.employee_name, time=self.time, location=message_suffix))
					message = _("Hourly Report: {employee} checked in at {time}. {location}".format(employee=self.employee_name, time=self.time, location=message_suffix))
					for_users = [supervisor_user]
					create_notification_log(subject, message, for_users, self)

				elif self.log_type == "OUT":
					# Automatic checkout
					if not self.device_id:
						title = "Checkin Report"
						category = "Attendance"
						subject = _("Automated Checkout: {employee} forgot to checkout.".format(employee=self.employee_name))
						message = _('<a class="btn btn-primary" href="/app/employee-checkin/{name}">Review check out</a>&nbsp;'.format(name=self.name))
						for_users = [supervisor_user]
						send_notification(title, subject, message, category, for_users)
					#EARLY: Checkout time is before [Shift End - Early grace exit time]
					elif shift_type.enable_exit_grace_period == 1 and self.device_id and get_datetime(self.time) < (get_datetime(curr_shift.end_datetime) - timedelta(minutes=shift_type.early_exit_grace_period)):
						time_diff = get_datetime(curr_shift.end_datetime) - get_datetime(self.time)
						hrs, mins, secs = cstr(time_diff).split(":")
						early = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
						subject = _("{employee} has checked out early by {early}. {location}".format(employee=self.employee_name, early=early, location=message_suffix))
						message = _("{employee_name} has checked out early by {early}. {location} <br><br><div class='btn btn-primary btn-danger early-punch-out' id='{employee}_{date}_{shift}'>Issue Penalty</div>".format(employee_name=self.employee_name, shift=self.operations_shift, date=cstr(self.time), employee=self.employee_name, early=early, location=message_suffix))
						for_users = [supervisor_user]
						create_notification_log(subject, message, for_users, self)

			else:
				# When no shift assigned, supervisor of active shift of the nearest site is sent a notification about unassigned checkin.
				location = self.device_id
				# supervisor = get_closest_location(self.time, location)
				reporting_manager = frappe.get_value("Employee", {"user_id": self.owner}, "reports_to")
				supervisor = get_employee_user_id(reporting_manager)
				if supervisor:
					subject = _("{employee} has checked in on an unassigned shift".format(employee=self.employee_name))
					message = _("{employee} has checked in on an unassigned shift".format(employee=self.employee_name))
					for_users = [supervisor]
					create_notification_log(subject, message, for_users, self)




@frappe.whitelist()
def get_current_shift_checkin(employee):
	# fetch datetime
	current_datetime = now_datetime()

	# fetch the last shift assignment
	shift = frappe.db.sql(f""" select name, shift, shift_type, start_date, start_datetime, end_datetime, roster_type from `tabShift Assignment` where employee = '{employee}' order by creation desc limit 1 """, as_dict=1)
	if shift:
		before_time, after_time = frappe.db.sql(f""" select begin_check_in_before_shift_start_time, allow_check_out_after_shift_end_time from `tabShift Type` where name = '{shift[0]["shift_type"]}' """)[0]
		if shift[0]["start_datetime"] and shift[0]["end_datetime"]:
			# include early entry and late exit time
			start_time = shift[0]["start_datetime"] - timedelta(minutes=before_time)
			end_time = shift[0]["end_datetime"] + timedelta(minutes=after_time)

			# Check if current time is within the shift start and end time.
			if start_time <= current_datetime <= end_time:
				return shift


def get_shift_from_checkin(checkin):
	"""
		This method returns shift assignment for a specific checkin based on a specific date
	"""
	shifts = frappe.db.get_list(
		"Shift Assignment", 
		filters={'employee':checkin.employee, 
			'start_date': ["BETWEEN", [str(add_days(checkin.time.date(), -1)), str(checkin.time.date())]], 'docstatus':1},
		fields="*",
		ignore_permissions=1
	)
	for s in shifts:
		if ((s.start_datetime + timedelta(minutes=-70)) <= checkin.time <= (s.end_datetime + timedelta(minutes=60))):
			return s


def notify_supervisor_about_late_entry(checkin):
	"""
	This method notify the supervisor about the late entry of an employee
	"""
	try:
		auto_attendance_employee = frappe.get_value("Employee", {'name':checkin.employee}, ['auto_attendance'])
		if auto_attendance_employee == 0:
			shift_permission = frappe.db.sql(f""" select name from `tabShift Permission` where employee = '{checkin.employee}' and date = '{now_datetime().date()}' and log_type = 'IN' and permission_type = 'Arrive Late' and workflow_state = 'Approved' ;  """)
			if checkin.shift_assignment:
				last_shift_assignment = checkin.shift_assignment
				shift_late_minutes = frappe.db.get_value("Shift Type", {"name": checkin.shift_type}, ['supervisor_reminder_shift_start', 'start_time'], as_dict=1)
				the_roster_type = checkin.roster_type
				op_shift = frappe.get_doc("Operations Shift", checkin.operations_shift)

			else:
				last_shift_assignment = get_shift_from_checkin(checkin)
				if last_shift_assignment:
					shift_late_minutes = frappe.db.get_value("Shift Type", {"name": last_shift_assignment["shift_type"]}, ['supervisor_reminder_shift_start', 'start_time'], as_dict=1)
					the_roster_type = last_shift_assignment.roster_type
					op_shift = frappe.get_doc("Operations Shift", last_shift_assignment.shift)

			if last_shift_assignment and not shift_permission:
				if checkin.time.time() > datetime.strptime(str(shift_late_minutes["start_time"] + timedelta(minutes=shift_late_minutes['supervisor_reminder_shift_start'])), "%H:%M:%S").time():
					time_diff = calculate_time_diffrence_for_checkin(shift_late_minutes["start_time"], checkin.time)
					time_of_arrival = parse(str(checkin.time)).time()
					get_reports_to = frappe.db.get_value("Employee", {"name": checkin.employee}, ['reports_to'])
					if get_reports_to:
						return send_push_notification_for_late_entry(get_reports_to, checkin.employee_name, roster_type=the_roster_type if the_roster_type else "Basic", time_difference=time_diff, shift=op_shift, time_of_arrival=time_of_arrival)
					get_site = frappe.db.get_value("Employee", {"name": checkin.employee}, ['site'])
					if get_site:
						get_site_supervisor = frappe.db.get_value("Operations Site", {"name": get_site}, ['account_supervisor'])
						if get_site_supervisor:
							return send_push_notification_for_late_entry(get_site_supervisor, checkin.employee, roster_type=the_roster_type if the_roster_type else "Basic", time_difference=time_diff, shift=op_shift, time_of_arrival=time_of_arrival)
	except Exception as e:
		frappe.log_error(e)
		pass


def send_push_notification_for_late_entry(recipient, culprit_name, shift, time_of_arrival,  time_difference=(0, 0), roster_type="Basic"):
	"""
	This method sends a push notification and a mail to the supervisor
	"""
	title = f"Late Arrival Of {culprit_name}"
	body =  f"Hello, {culprit_name} has arrived late for work today."
	if roster_type != "Basic":
		body = f"Hello, {culprit_name} has arrived late for overtime work today."

	late_arrival_time_diffrence = f"{time_difference[0]} minutes late" if len(time_difference) == 1 else f"{time_difference[0]} hour, {time_difference[1]} minutes late"
	push_notification_rest_api_for_checkin(recipient, title, body, checkin=False, arriveLate=False, checkout=False)
	get_user_id = frappe.db.get_value("Employee", {"name": recipient}, ["user_id"], as_dict=1)
	user_id = get_user_id["user_id"] if get_user_id else ""
	msg = frappe.render_template('one_fm/templates/emails/late_arrival_notification.html', context={"time_diffrence": time_difference, "shift": shift, "roster_type": roster_type, "time_diff": late_arrival_time_diffrence, "employee": culprit_name, "time_of_arrival": time_of_arrival})
	sendemail(recipients=user_id, subject=title, content=msg)
	return "Messages Sent Successfully !!"


def calculate_time_diffrence_for_checkin(shift_time, checkin_time):
	datetime_shift = datetime.strptime(str(now_datetime().date()) + " " + str(shift_time), '%Y-%m-%d %H:%M:%S')
	time_diff_in_minutes = (checkin_time - datetime_shift).seconds // 60
	the_diff = divmod(time_diff_in_minutes, 60) 
	if the_diff[0] < 1:
		return [the_diff[1]]
	return list(the_diff)

@frappe.whitelist()
def auto_generate_checkin():
	date = today()
	employee_list = frappe.db.sql(f"""SELECT e.name as ename, sa.name as sname, sa.start_datetime, sa.end_datetime, sa.start_date
									from `tabEmployee` as e, `tabShift Assignment` as sa
									WHERE e.auto_attendance = 1
									AND sa.employee = e.name
									AND sa.start_date = '{date}'
					""", as_dict=1)
	
	if employee_list:
		frappe.enqueue(process_list, employee_list=employee_list, is_async=True, queue='long')

def process_list(employee_list):
	for e in employee_list:
		checkin_time = e.start_datetime + (e.start_datetime + timedelta(minutes=60) - e.start_datetime) * random.random()
		checkout_time = e.end_datetime + (e.end_datetime + timedelta(minutes=30) - e.end_datetime) * random.random()
		create_checkin_record(e.ename, "IN", checkin_time)
		create_checkin_record(e.ename, "OUT", checkout_time)

def create_checkin_record(employee, log_type, time):
	employee_checkin = frappe.new_doc('Employee Checkin')
	employee_checkin.employee = employee
	employee_checkin.log_type = log_type
	employee_checkin.time = time
	employee_checkin.flags.ignore_validate = True
	employee_checkin.save(ignore_permissions=True)
	employee_checkin.db_set('creation', str(time))
	employee_checkin.db_set('actual_time', str(time))
	frappe.db.commit()
		