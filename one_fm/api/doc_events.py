from datetime import timedelta
import itertools

import frappe, erpnext
from frappe import _
from frappe.utils import cstr, cint, get_datetime, getdate, add_to_date
from frappe.core.doctype.version.version import get_diff
from erpnext.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings, get_actual_start_end_datetime_of_shift
from one_fm.operations.doctype.operations_site.operations_site import create_notification_log
import datetime
from frappe.permissions import remove_user_permission
from erpnext.hr.utils import get_holidays_for_employee

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
			name, assignment, shift_type = frappe.get_value("Shift Assignment", {"employee": doc.employee, "start_date": curr_shift.start_datetime.date(), "shift_type": curr_shift.shift_type.name}, ["name","shift", "shift_type"])
			doc.shift_assignment = name
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
	from one_fm.api.tasks import send_notification, issue_penalty
	# These are returned according to dates. Time is not taken into account
	prev_shift, curr_shift, next_shift = get_employee_shift_timings(doc.employee, get_datetime(doc.time))
	penalty_code_late_checkin = "102"
	penalty_code_early_checkout="103"

	log_exist = frappe.db.sql("""
			SELECT name FROM `tabEmployee Checkin` empChkin
		 			WHERE
		 				empChkin.log_type='{log_type}'
		 				AND empChkin.skip_auto_attendance=0
		 				AND date(empChkin.time)='{date}'
		 				AND empChkin.shift_type='{shift_type}'
						AND name !='{current_doc}'
			""".format(date=cstr(getdate()), shift_type=doc.shift_type,log_type=doc.log_type, current_doc=doc.name), as_dict=1)

	if not log_exist:
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
				#if get_datetime(doc.time) < get_datetime(curr_shift.actual_start):
				#	time_diff = get_datetime(curr_shift.start_datetime) - get_datetime(doc.time)
				#	hrs, mins, secs = cstr(time_diff).split(":")
				#	early = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
				#	subject = _("{employee} has checked in early by {early}. {location}".format(employee=doc.employee_name, early=early, location=message_suffix))
				#	message = _("{employee} has checked in early by {early}. {location}".format(employee=doc.employee_name, early=early, location=message_suffix))
				#	for_users = [supervisor_user]
				#	create_notification_log(subject, message, for_users, doc)

				# ON TIME
				#elif get_datetime(doc.time) >= get_datetime(doc.shift_actual_start) and get_datetime(doc.time) <= (get_datetime(doc.shift_start) + timedelta(minutes=shift_type.late_entry_grace_period)):
				#	subject = _("{employee} has checked in on time. {location}".format(employee=doc.employee_name, location=message_suffix))
				#	message = _("{employee} has checked in on time. {location}".format(employee=doc.employee_name, location=message_suffix))
				#	for_users = [supervisor_user]
				#	create_notification_log(subject, message, for_users, doc)

				# LATE: Checkin time is after [Shift Start + Late Grace Entry period]
				if shift_type.enable_entry_grace_period == 1 and get_datetime(doc.time) > (get_datetime(doc.shift_start) + timedelta(minutes=shift_type.late_entry_grace_period)):
					time_diff = get_datetime(doc.time) - get_datetime(doc.shift_start)
					hrs, mins, secs = cstr(time_diff).split(":")
					delay = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
					subject = _("{employee} has checked in late by {delay}. {location}".format(employee=doc.employee_name, delay=delay, location=message_suffix))
					message = _("{employee_name} has checked in late by {delay}. {location} <br><br><div class='btn btn-primary btn-danger late-punch-in' id='{employee}_{date}_{shift}'>Issue Penalty</div>".format(employee_name=doc.employee_name,shift=doc.operations_shift, date=cstr(doc.time), employee=doc.employee, delay=delay, location=message_suffix))
					for_users = [supervisor_user]
					issue_penalty(doc.employee, doc.time, penalty_code_late_checkin, doc.operations_shift, supervisor_user, doc.device_id)
					create_notification_log(subject, message, for_users, doc)

			elif doc.log_type == "IN" and doc.skip_auto_attendance == 1:
				subject = _("Hourly Report: {employee} checked in at {time}. {location}".format(employee=doc.employee_name, time=doc.time, location=message_suffix))
				message = _("Hourly Report: {employee} checked in at {time}. {location}".format(employee=doc.employee_name, time=doc.time, location=message_suffix))
				for_users = [supervisor_user]
				create_notification_log(subject, message, for_users, doc)

			elif doc.log_type == "OUT":
				# Automatic checkout

				if not doc.device_id:
					subject = _("Automated Checkout: {employee} forgot to checkout.".format(employee=doc.employee_name))
					message = _('<a class="btn btn-primary" href="/app/employee-checkin/{name}">Review check out</a>&nbsp;'.format(name=doc.name))
					for_users = [supervisor_user]
					print("124", doc.employee, supervisor_user)
					send_notification(subject, message, for_users)
				#EARLY: Checkout time is before [Shift End - Early grace exit time]
				elif shift_type.enable_exit_grace_period == 1 and doc.device_id and get_datetime(doc.time) < (get_datetime(curr_shift.end_datetime) - timedelta(minutes=shift_type.early_exit_grace_period)):
					time_diff = get_datetime(curr_shift.end_datetime) - get_datetime(doc.time)
					hrs, mins, secs = cstr(time_diff).split(":")
					early = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
					subject = _("{employee} has checked out early by {early}. {location}".format(employee=doc.employee_name, early=early, location=message_suffix))
					message = _("{employee_name} has checked out early by {early}. {location} <br><br><div class='btn btn-primary btn-danger early-punch-out' id='{employee}_{date}_{shift}'>Issue Penalty</div>".format(employee_name=doc.employee_name, shift=doc.operations_shift, date=cstr(doc.time), employee=doc.employee_name, early=early, location=message_suffix))
					for_users = [supervisor_user]
					create_notification_log(subject, message, for_users, doc)

				# ON TIME
				#elif doc.device_id and get_datetime(doc.time) <= get_datetime(doc.shift_actual_end) and get_datetime(doc.time) >= (get_datetime(doc.shift_end) - timedelta(minutes=shift_type.early_exit_grace_period)):
				#	subject = _("{employee} has checked out on time. {location}".format(employee=doc.employee_name, location=message_suffix))
				#	message = _("{employee} has checked out on time. {location}".format(employee=doc.employee_name, location=message_suffix))
				#	for_users = [supervisor_user]
				#	create_notification_log(subject, message, for_users, doc)

				# LATE: Checkin time is after [Shift End + Variable checkout time]
				#elif doc.device_id and get_datetime(doc.time) > get_datetime(doc.shift_actual_end):
				#	time_diff = get_datetime(doc.time) - get_datetime(doc.shift_end)
				#	hrs, mins, secs = cstr(time_diff).split(":")
				#	delay = "{hrs} hrs {mins} mins".format(hrs=hrs, mins=mins) if cint(hrs) > 0 else "{mins} mins".format(mins=mins)
				#	subject = _("{employee} has checked out late by {delay}. {location}".format(employee=doc.employee_name, delay=delay, location=message_suffix))
				#	message = _("{employee} has checked out late by {delay}. {location}".format(employee=doc.employee_name, delay=delay, location=message_suffix))
				#	for_users = [supervisor_user]
				#	create_notification_log(subject, message, for_users, doc)
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

@frappe.whitelist()
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

# Attendance
def create_additional_salary_for_overtime(doc, method):
	"""
	This function creates an additional salary document for a given by specifying the salary component for overtime set in the HR and Payroll Additional Settings,
	by obtaining the details from Attendance where the roster type is set to Over-Time.

	The over time rate is fetched from the project which is linked with the shift the employee was working in.
	The over time rate is calculated by multiplying the number of hours of the shift with the over time rate for the project.

	In case of no overtime rate is set for the project, overtime rates are fetched from HR and Payroll Additional Settings.
	Amount is calucated and additional salary is created as:
	1. If employee has an existing basic schedule on the same day - working day rate is applied
	2. Working on a holiday of type "weekly off: - day off rate is applied.
	3. Working on a holiday of type non "weekly off" - public/additional holiday.

	Args:
		doc: The attendance document

	"""
	roster_type_basic = "Basic"
	roster_type_overtime = "Over-Time"

	days_of_week = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

	# Check if attendance is for roster type: Over-Time
	if doc.roster_type == roster_type_overtime:

		payroll_date = cstr(getdate())

		# Fetch payroll details from HR and Payroll Additional Settings
		overtime_component = frappe.db.get_single_value("HR and Payroll Additional Settings", 'overtime_additional_salary_component')
		working_day_overtime_rate = frappe.db.get_single_value("HR and Payroll Additional Settings", 'working_day_overtime_rate')
		day_off_overtime_rate = frappe.db.get_single_value("HR and Payroll Additional Settings", 'day_off_overtime_rate')
		public_holiday_overtime_rate = frappe.db.get_single_value("HR and Payroll Additional Settings", 'public_holiday_overtime_rate')

		# Fetch project and duration of the shift employee worked in operations shift
		project, overtime_duration = frappe.db.get_value("Operations Shift", doc.operations_shift, ["project", "duration"])

		# Fetch overtime details from project
		project_has_overtime_rate, project_overtime_rate = frappe.db.get_value("Project", {'name': project}, ["has_overtime_rate", "overtime_rate"])

		# If project has a specified overtime rate, calculate amount based on overtime rate and create additional salary
		if project_has_overtime_rate:

			if project_overtime_rate > 0:
				amount = round(project_overtime_rate * overtime_duration, 3)
				notes = "Calculated based on overtime rate set for the project: {project}".format(project=project)

				create_additional_salary(doc.employee, amount, overtime_component, payroll_date, notes)

			else:
				frappe.throw(_("Overtime rate must be greater than zero for project: {project}".format(project=project)))

		# If no overtime rate is specified, follow labor law => (Basic Hourly Wage * number of worked hours * 1.5)
		else:
			# Fetch assigned shift, basic salary  and holiday list for the given employee
			assigned_shift, basic_salary, holiday_list = frappe.db.get_value("Employee", {'employee': doc.employee}, ["shift", "one_fm_basic_salary", "holiday_list"])

			if assigned_shift:
				# Fetch duration of the shift employee is assigned to
				assigned_shift_duration = frappe.db.get_value("Operations Shift", assigned_shift, ["duration"])

				if basic_salary and basic_salary > 0:
					# Compute hourly wage
					daily_wage = round(basic_salary/30, 3)
					hourly_wage = round(daily_wage/assigned_shift_duration, 3)

					# Check if a basic schedule exists for the employee and the attendance date
					if frappe.db.exists("Employee Schedule", {'employee': doc.employee, 'date': doc.attendance_date, 'employee_availability': "Working", 'roster_type': roster_type_basic}):

						if working_day_overtime_rate > 0:

							# Compute amount as per working day rate
							amount = round(hourly_wage * overtime_duration * working_day_overtime_rate, 3)
							notes = "Calculated based on working day rate => (Basic hourly wage) * (Duration of worked hours) * {working_day_overtime_rate}".format(working_day_overtime_rate=working_day_overtime_rate)

							create_additional_salary(doc.employee, amount, overtime_component, payroll_date, notes)

						else:
							frappe.throw(_("No Wroking Day overtime rate set in HR and Payroll Additional Settings."))

					# Check if attendance date falls in a holiday list
					elif holiday_list:

						# Pass last parameter as "False" to get weekly off days
						holidays_weekly_off = get_holidays_for_employee(doc.employee, doc.attendance_date, doc.attendance_date, False, False)

						# Pass last paramter as "True" to get non weekly off days, ie, public/additional holidays
						holidays_public_holiday = get_holidays_for_employee(doc.employee, doc.attendance_date, doc.attendance_date, False, True)

						# Check for weekly off days length and if description of day off is set as one of the weekdays. (By default, description is set to a weekday name)
						if len(holidays_weekly_off) > 0 and holidays_weekly_off[0].description in days_of_week:

							if day_off_overtime_rate > 0:

								# Compute amount as per day off rate
								amount = round(hourly_wage * overtime_duration * day_off_overtime_rate, 3)
								notes = "Calculated based on day off rate => (Basic hourly wage) * (Duration of worked hours) * {day_off_overtime_rate}".format(day_off_overtime_rate=day_off_overtime_rate)

								create_additional_salary(doc.employee, amount, overtime_component, payroll_date, notes)

							else:
								frappe.throw(_("No Day Off overtime rate set in HR and Payroll Additional Settings."))

						# Check for weekly off days set to "False", ie, Public/additional holidays in holiday list
						elif len(holidays_public_holiday) > 0:

							if public_holiday_overtime_rate > 0:

								# Compute amount as per public holiday rate
								amount = round(hourly_wage * overtime_duration * public_holiday_overtime_rate, 3)
								notes = "Calculated based on day off rate => (Basic hourly wage) * (Duration of worked hours) * {public_holiday_overtime_rate}".format(public_holiday_overtime_rate=public_holiday_overtime_rate)

								create_additional_salary(doc.employee, amount, overtime_component, payroll_date, notes)

							else:
								frappe.throw(_("No Public Holiday overtime rate set in HR and Payroll Additional Settings."))
					else:
						frappe.throw(_("No basic Employee Schedule or Holiday List found for employee: {employee}".format(employee=doc.employee)))

				else:
					frappe.throw(_("Basic Salary not set for employee: {employee} in the employee record.".format(employee=doc.employee)))

			else:
				frappe.throw(_("Shift not set for employee: {employee} in the employee record.".format(employee=doc.employee)))



def create_additional_salary(employee, amount, component, payroll_date, notes):
	"""
	This function creates a document in the Additonal Salary doctype.

	Args:
		employee: employee code (eg: HR-EMP-0001)
		amount: amount to be considered in the additional salary
		component: type of component
		payroll_date: date that falls in the range during which this additional salary must be considered for payroll
		notes: Any additional notes

	Raises:
		exception e: Any internal server error
	"""

	try:
		additional_salary = frappe.new_doc("Additional Salary")
		additional_salary.employee = employee
		additional_salary.salary_component = component
		additional_salary.amount = amount
		additional_salary.payroll_date = payroll_date
		additional_salary.company = erpnext.get_default_company()
		additional_salary.overwrite_salary_structure_amount = 1
		additional_salary.notes = notes
		additional_salary.insert()
		additional_salary.submit()

	except Exception as e:
		frappe.log_error(e)
		frappe.throw(_(e))
