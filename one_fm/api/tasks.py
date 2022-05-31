import itertools
from datetime import timedelta
from string import Template
from calendar import month, monthrange
from datetime import datetime, timedelta
from frappe import enqueue
import frappe, erpnext
from frappe import _
from frappe.utils import now_datetime, cstr, getdate, get_datetime, cint, add_to_date, datetime, today
from one_fm.api.doc_events import get_employee_user_id
from erpnext.payroll.doctype.payroll_entry.payroll_entry import get_end_date
from one_fm.api.doc_methods.payroll_entry import create_payroll_entry
from erpnext.hr.doctype.attendance.attendance import mark_attendance
from one_fm.api.mobile.roster import get_current_shift
from one_fm.api.api import push_notification_for_checkin, push_notification_rest_api_for_checkin

class DeltaTemplate(Template):
	delimiter = "%"

def strfdelta(tdelta, fmt):
	d = {"D": tdelta.days}
	hours, rem = divmod(tdelta.seconds, 3600)
	minutes, seconds = divmod(rem, 60)
	d["H"] = '{:02d}'.format(hours)
	d["M"] = '{:02d}'.format(minutes)
	d["S"] = '{:02d}'.format(seconds)
	t = DeltaTemplate(fmt)
	return t.substitute(**d)

@frappe.whitelist()
def send_checkin_hourly_reminder():
	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	shifts_list = get_active_shifts(now_time)

	title = "Hourly Reminder"
	category = "Attendance"
	#Send notifications to employees assigned to a shift for hourly checkin
	for shift in shifts_list:
		if strfdelta(shift.start_time, '%H:%M:%S') != cstr(get_datetime(now_time).time()) and strfdelta(shift.end_time, '%H:%M:%S') != cstr(get_datetime(now_time).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.user_id FROM `tabShift Assignment` tSA, `tabEmployee` emp
				WHERE
			  		tSA.employee = emp.name
				AND tSA.start_date='{date}'
				AND tSA.shift_type='{shift_type}'
				AND tSA.docstatus=1
			""".format(date=cstr(date), shift_type=shift.name), as_list=1)
			recipients = [recipient[0] for recipient in recipients if recipient[0]]

			subject = _("Hourly Reminder: Please checkin")
			message = _('<a class="btn btn-warning" href="/desk#face-recognition">Hourly Check In</a>')
			send_notification(title, subject, message, category, recipients)

def checkin_checkout_final_reminder():
	if not frappe.db.get_single_value('HR and Payroll Additional Settings', 'remind_employee_checkin_checkout'):
		return

	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	shifts_list = get_active_shifts(now_time)
	date = getdate()

	#Send final reminder to checkin or checkout to employees who have not even after shift has ended
	for shift in shifts_list:
		# shift_start is equal to now time - notification reminder in mins
		# Employee won't receive checkin notification when accepted Arrive Late shift permission is present
		if strfdelta(shift.start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.notification_reminder_after_shift_start))).time()):
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.user_id, emp.name FROM `tabShift Assignment` tSA, `tabEmployee` emp
				WHERE
			  		tSA.employee=emp.name
				AND tSA.start_date='{date}'
				AND tSA.shift_type='{shift_type}'
				AND tSA.docstatus=1
				AND tSA.employee
				NOT IN(SELECT employee FROM `tabShift Permission` emp_sp
				WHERE
					emp_sp.employee=emp.name
				AND emp_sp.workflow_state='Approved'
				AND emp_sp.shift_type='{shift_type}'
				AND emp_sp.date='{date}'
				AND emp_sp.permission_type="Arrive Late")
				AND tSA.employee
				NOT IN(SELECT employee FROM `tabEmployee Checkin` empChkin
				WHERE
					empChkin.log_type="IN"
				AND DATE_FORMAT(empChkin.time,'%Y-%m-%d')='{date}'
				AND empChkin.shift_type='{shift_type}')
				AND tSA.start_date
				NOT IN(SELECT holiday_date from `tabHoliday` h
				WHERE 
					h.parent = emp.holiday_list
				AND h.holiday_date = '{date}')
			""".format(date=cstr(date), shift_type=shift.name), as_dict=1)

			if len(recipients) > 0:
				frappe.enqueue(notify_checkin_checkout_final_reminder, recipients=recipients,log_type="IN", is_async=True, queue='long')

		# shift_end is equal to now time - notification reminder in mins
		# Employee won't receive checkout notification when accepted Leave Early shift permission is present
		if strfdelta(shift.end_time, '%H:%M:%S') == cstr((get_datetime(now_time)- timedelta(minutes=cint(shift.notification_reminder_after_shift_end))).time()):
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.user_id, emp.name FROM `tabShift Assignment` tSA, `tabEmployee` emp
				WHERE
			  		tSA.employee = emp.name
				AND tSA.start_date='{date}'
				AND tSA.shift_type='{shift_type}'
				AND tSA.docstatus=1
				AND tSA.employee
				NOT IN(SELECT employee FROM `tabShift Permission` emp_sp
				WHERE
					emp_sp.employee=emp.name
				AND emp_sp.workflow_state='Approved'
				AND emp_sp.shift_type='{shift_type}'
				AND emp_sp.date='{date}'
				AND emp_sp.permission_type="Leave Early")
				AND tSA.employee
				NOT IN(SELECT employee FROM `tabEmployee Checkin` empChkin
				WHERE
					empChkin.log_type="OUT"
				AND DATE_FORMAT(empChkin.time,'%Y-%m-%d')='{date}'
				AND empChkin.shift_type='{shift_type}')
				AND tSA.start_date
				NOT IN(SELECT holiday_date from `tabHoliday` h
				WHERE 
					h.parent = emp.holiday_list
				AND h.holiday_date = '{date}')
			""".format(date=cstr(date), shift_type=shift.name), as_dict=1)

			if len(recipients) > 0:
				frappe.enqueue(notify_checkin_checkout_final_reminder, recipients=recipients,log_type="OUT", is_async=True, queue='long')

#This function is the combination of two types of notification, email/log notifcation and push notification
@frappe.whitelist()
def notify_checkin_checkout_final_reminder(recipients,log_type):
	"""
	params:
	recipients: Dictionary consist of user ID and Emplloyee ID eg: [{'user_id': 's.shaikh@armor-services.com', 'name': 'HR-EMP-00001'}]
	log_type: In or Out
	"""
	#defining the subject and message
	title  = "Final Reminder"
	checkin_subject = _("Please checkin in the next five minutes.")
	checkin_message = _("""
					<a class="btn btn-success" href="/desk#face-recognition">Check In</a>&nbsp;
					<a class="btn btn-primary" href="/desk#shift-permission/new-shift-permission-1">Planning to arrive late?</a>&nbsp;
					""")
	notification_category = "Attendance"
	checkout_subject = _("Final Reminder: Please checkout in the next five minutes.")
	checkout_message = _("""<a class="btn btn-danger" href="/desk#face-recognition">Check Out</a>""")
	Notification_title = "Final Reminder"
	Notification_body = "Please checkin in the next five minutes."
	user_id_list = []

	#eg: recipient: {'user_id': 's.shaikh@armor-services.com', 'name': 'HR-EMP-00001'}
	for recipient in recipients:
		# Append the list of user ID to send notification through email.
		user_id_list.append(recipient.user_id)

		# Get Employee ID and User Role for the given recipient
		employee_id = recipient.name
		user_roles = frappe.get_roles(recipient.user_id)

		#cutomizing buttons according to log type.
		if log_type=="IN":
			#arrive late button is true only if the employee has the user role "Head Office Employee".
			if "Head Office Employee" in user_roles:
				push_notification_rest_api_for_checkin(employee_id, Notification_title, Notification_body, checkin=True,arriveLate=True,checkout=False)
			else:
				push_notification_rest_api_for_checkin(employee_id, Notification_title, Notification_body, checkin=True,arriveLate=False,checkout=False)
		if log_type=="OUT":
			push_notification_rest_api_for_checkin(employee_id, Notification_title, Notification_body, checkin=False,arriveLate=False,checkout=True)

			
	# send notification mail to list of employee using user_id
	if log_type == "IN":
		send_notification(title, checkin_subject, checkin_message,notification_category,user_id_list)
	elif log_type == "OUT":
		send_notification(title, checkout_subject, checkout_message, notification_category, user_id_list)


def checkin_checkout_supervisor_reminder():
	if not frappe.db.get_single_value('HR and Payroll Additional Settings', 'remind_supervisor_checkin_checkout'):
		return

	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	today_datetime = today()
	shifts_list = get_active_shifts(now_time)
	title = "Checkin Report"
	category = "Attendance"
	for shift in shifts_list:
		t = shift.supervisor_reminder_shift_start
		b = strfdelta(shift.start_time, '%H:%M:%S')

		# Send notification to supervisor of those who haven't checked in and don't have accepted Arrive Late shift permission
		if strfdelta(shift.start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.supervisor_reminder_shift_start))).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			checkin_time = today_datetime + " " + strfdelta(shift.start_time, '%H:%M:%S')
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.name, emp.employee_id, emp.employee_name, emp.reports_to, tSA.shift FROM `tabShift Assignment` tSA, `tabEmployee` emp
				WHERE
			  		tSA.employee=emp.name
				AND tSA.start_date='{date}'
				AND tSA.shift_type='{shift_type}'
				AND tSA.docstatus=1
				AND tSA.employee
				NOT IN(SELECT employee FROM `tabShift Permission` emp_sp
				WHERE
					emp_sp.employee=emp.name
				AND emp_sp.workflow_state="Approved"
				AND emp_sp.shift_type='{shift_type}'
				AND emp_sp.date='{date}'
				AND emp_sp.permission_type="Arrive Late")
				AND tSA.employee
				NOT IN(SELECT employee FROM `tabEmployee Checkin` empChkin
					WHERE
						empChkin.log_type="IN"
						AND empChkin.skip_auto_attendance=0
						AND date(empChkin.time)='{date}'
						AND empChkin.shift_type='{shift_type}')
				AND tSA.start_date
				NOT IN(SELECT holiday_date from `tabHoliday` h
				WHERE 
					h.parent = emp.holiday_list
				AND h.holiday_date = '{date}')
			""".format(date=cstr(date), shift_type=shift.name), as_dict=1)

			if len(recipients) > 0:
				for recipient in recipients:
					action_user, Role = get_action_user(recipient.name,recipient.shift)
					#for_user = get_employee_user_id(recipient.reports_to) if get_employee_user_id(recipient.reports_to) else get_notification_user(op_shift)
					subject = _("{employee} has not checked in yet.".format(employee=recipient.employee_name))
					action_message = _("""
					<a class="btn btn-success checkin" id='{employee}_{time}'>Approve</a>
					<br><br><div class='btn btn-primary btn-danger no-punch-in' id='{employee}_{date}_{shift}'>Issue Penalty</div>
					""").format(shift=recipient.shift, date=cstr(now_time), employee=recipient.name, time=checkin_time)
					if action_user is not None:
						send_notification(title, subject, action_message, category, [action_user])

					notify_message = _("""Note that {employee} from Shift {shift} has Not Checked in yet.""").format(employee=recipient.employee_name, shift=recipient.shift)
					if Role:
						notify_user = get_notification_user(recipient.name,recipient.shift, Role)
						if notify_user is not None:
							send_notification(title, subject, notify_message, category, notify_user)

		#Send notification to supervisor of those who haven't checked out and don't have accepted Leave Early shift permission
		if strfdelta(shift.end_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.supervisor_reminder_start_ends))).time()):
		 	date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
		 	checkin_time = today_datetime + " " + strfdelta(shift.end_time, '%H:%M:%S')
		 	recipients = frappe.db.sql("""
		 		SELECT DISTINCT emp.employee_name, emp.reports_to, tSA.shift FROM `tabShift Assignment` tSA, `tabEmployee` emp
		 		WHERE
		 	  		tSA.employee=emp.name
		 		AND tSA.start_date='{date}'
		 		AND tSA.shift_type='{shift_type}'
		 		AND tSA.docstatus=1
				AND tSA.employee
				NOT IN(SELECT employee FROM `tabShift Permission` emp_sp
				WHERE
					emp_sp.employee=emp.name
				AND emp_sp.workflow_state="Approved"
				AND emp_sp.shift_type='{shift_type}'
				AND emp_sp.date='{date}'
				AND emp_sp.permission_type="Leave Early")
				AND tSA.employee
		 		NOT IN(SELECT employee FROM `tabEmployee Checkin` empChkin
		 			WHERE
		 				empChkin.log_type="OUT"
		 				AND empChkin.skip_auto_attendance=0
		 				AND date(empChkin.time)='{date}'
		 				AND empChkin.shift_type='{shift_type}')
				AND tSA.start_date
				NOT IN(SELECT holiday_date from `tabHoliday` h
				WHERE 
					h.parent = emp.holiday_list
				AND h.holiday_date = '{date}')
		 	""".format(date=cstr(date), shift_type=shift.name), as_dict=1)

		 	if len(recipients) > 0:
		 		for recipient in recipients:
		 			action_user, Role = get_action_user(recipient.name,recipient.shift)
					#for_user = get_employee_user_id(recipient.reports_to) if get_employee_user_id(recipient.reports_to) else get_notification_user(op_shift)
		 			subject = _('{employee} has not checked in yet.'.format(employee=recipient.employee_name))
		 			action_message = _("""
						 <a class="btn btn-success checkin" id='{employee}_{time}'>Approve</a>
						 <br><br><div class='btn btn-primary btn-danger no-punch-in' id='{employee}_{date}_{shift}'>Issue Penalty</div>
						 """).format(shift=recipient.shift, date=cstr(now_time), employee=recipient.name, time=checkout_time)
		 			if action_user is not None:
						 send_notification(title, subject, action_message, category, [action_user])

		 			notify_message = _("""Note that {employee} from Shift {shift} has Not Checked Out yet.""").format(employee=recipient.employee_name, shift=recipient.shift)
		 			if Role:
						 notify_user = get_notification_user(recipient.name,recipient.shift, Role)
						 if notify_user is not None:
							 send_notification(title, subject, notify_message, category, notify_user)


def send_notification(title, subject, message, category, recipients):
	for user in recipients:
		notification = frappe.new_doc("Notification Log")
		notification.title = title
		notification.subject = subject
		notification.email_content = message
		notification.document_type = "Notification Log"
		notification.for_user = user
		notification.document_name = " "
		notification.category = category
		notification.one_fm_mobile_app = 1
		notification.save(ignore_permissions=True)
		notification.document_name = notification.name
		notification.save(ignore_permissions=True)
		frappe.db.commit()

def get_active_shifts(now_time):
	return frappe.db.sql("""
		SELECT
			name, start_time, end_time,
			notification_reminder_after_shift_start, late_entry_grace_period,
			notification_reminder_after_shift_end, allow_check_out_after_shift_end_time,
			supervisor_reminder_shift_start, supervisor_reminder_start_ends, deadline
		FROM `tabShift Type`
		WHERE
			CAST('{current_time}' as date)
			BETWEEN
				CAST(start_time as date)
			AND
				IF(end_time < start_time, DATE_ADD(CAST(end_time as date), INTERVAL 1 DAY), CAST(end_time as date))
	""".format(current_time=now_time), as_dict=1)

def get_action_user(employee, shift):
		"""
				Shift > Site > Project > Reports to
		"""

		Employee = frappe.get_doc("Employee", {"name":employee})
		operations_shift = frappe.get_doc("Operations Shift", shift)
		operations_site = frappe.get_doc("Operations Site", operations_shift.site)
		project = frappe.get_doc("Project", operations_site.project)
		report_to = get_employee_user_id(Employee.reports_to) if Employee.reports_to else ""

		if report_to:
			action_user = report_to
			Role = "Report To"
		else:
			if operations_shift.supervisor:
				shift_supervisor = get_employee_user_id(operations_shift.supervisor)
				if shift_supervisor != operations_shift.owner:
					action_user = shift_supervisor
					Role = "Shift Supervisor"

			elif operations_site.account_supervisor:
				site_supervisor = get_employee_user_id(operations_site.account_supervisor)
				if site_supervisor != operations_shift.owner:
					action_user = site_supervisor
					Role = "Site Supervisor"

			elif operations_site.project:
				if project.account_manager:
					project_manager = get_employee_user_id(project.account_manager)
					if project_manager != operations_shift.owner:
						action_user = project_manager
						Role = "Project Manager"

		return action_user, Role

def get_notification_user(employee, shift, Role):
	"""
			Shift > Site > Project > Reports to
	"""
	Employee = frappe.get_doc("Employee", {"name":employee})
	operations_shift = frappe.get_doc("Operations Shift", shift)
	operations_site = frappe.get_doc("Operations Site", operations_shift.site)
	project = frappe.get_doc("Project", operations_site.project)
	project_manager = site_supervisor = shift_supervisor = None

	report_to = get_employee_user_id(Employee.reports_to) if Employee.reports_to else ""

	if operations_site.project and project.account_manager and get_employee_user_id(project.account_manager) != operations_shift.owner:
		project_manager = get_employee_user_id(project.account_manager)
	if operations_site.account_supervisor and get_employee_user_id(operations_site.account_supervisor) != operations_shift.owner:
		site_supervisor = get_employee_user_id(operations_site.account_supervisor)
	elif operations_shift.supervisor and get_employee_user_id(operations_shift.supervisor) != operations_shift.owne:
		shift_supervisor = get_employee_user_id(operations_shift.supervisor)

	if Role == "Shift Supervisor" and site_supervisor and project_manager:
		notify_user = [site_supervisor,project_manager]
	elif Role == "Site Supervisor" and project_manager:
		notify_user = [project_manager]
	else:
		notify_user = []

	return notify_user

def get_location(shift):
	site = frappe.get_value("Operations Shift", {"shift_type":shift}, "site")
	location= frappe.db.sql("""
			SELECT loc.latitude, loc.longitude, loc.geofence_radius
			FROM `tabLocation` as loc
			WHERE
				loc.name in (SELECT site_location FROM `tabOperations Site` where name=%s)
			""",site, as_dict=1)
	return location

def checkin_deadline():
	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	today = now_datetime().strftime("%Y-%m-%d")
	shifts_list = get_active_shifts(now_time)
	penalty_code = "106"

	for shift in shifts_list:
		location = get_location(shift.name)

		if location:
			penalty_location = str(location[0].latitude)+","+str(location[0].longitude)
		else:
			penalty_location ="0,0"
		# shift_start is equal to now time + deadline
		if shift.deadline!=0 and strfdelta(shift.start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.deadline))).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.name FROM `tabShift Assignment` tSA, `tabEmployee` emp
				WHERE
					tSA.employee = emp.name
				AND tSA.start_date='{date}'
				AND tSA.shift_type='{shift_type}'
				AND tSA.docstatus=1
				AND tSA.employee
				NOT IN(SELECT employee FROM `tabShift Permission` emp_sp
            	WHERE
					emp_sp.employee=emp.name
				AND emp_sp.workflow_state="Approved"
				AND emp_sp.shift_type='{shift_type}'
				AND emp_sp.date='{date}'
				AND emp_sp.permission_type="Arrive Late")
				AND tSA.employee
				NOT IN(SELECT employee FROM `tabEmployee Checkin` empChkin
				WHERE
					empChkin.log_type="IN"
				AND empChkin.skip_auto_attendance=0
				AND date(empChkin.time)='{date}'
				AND empChkin.shift_type='{shift_type}')
				AND tSA.start_date
				NOT IN(SELECT holiday_date from `tabHoliday` h
				WHERE 
					h.parent = emp.holiday_list
				AND h.holiday_date = '{date}')
			""".format(date=cstr(date), shift_type=shift.name), as_list=1)

			if len(recipients) > 0:
				employees = [recipient[0] for recipient in recipients if recipient[0]]

				for employee in employees:
					op_shift =  frappe.get_doc("Operations Shift", {"shift_type":shift.name})
					action_user, Role = get_action_user(employee,op_shift.name)
					if Role:
						issuing_user = get_notification_user(employee,op_shift.name,Role) if get_notification_user(employee,op_shift.name,Role) else get_employee_user_id(frappe.get_value("Employee",{"name":employee},['reports_to']))
						curr_shift = get_current_shift(employee)
						issue_penalty(employee, today, penalty_code, curr_shift.shift, issuing_user, penalty_location)
						mark_attendance(employee, today, 'Absent', shift.name)

			frappe.db.commit()

def automatic_checkout():
	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	shifts_list = get_active_shifts(now_time)
	for shift in shifts_list:
		# shift_end is equal to now time - notification reminder in mins
		if strfdelta(shift.end_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.allow_check_out_after_shift_end_time))).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.name FROM `tabShift Assignment` tSA, `tabEmployee` emp
				WHERE
					tSA.employee = emp.name
				AND tSA.start_date='{date}'
				AND tSA.shift_type='{shift_type}'
				AND tSA.docstatus=1
				AND tSA.employee
				NOT IN(SELECT employee FROM `tabEmployee Checkin` empChkin
				WHERE
					empChkin.log_type="OUT"
				AND empChkin.skip_auto_attendance=0
				AND date(empChkin.time)='{date}'
				AND empChkin.shift_type='{shift_type}')
			""".format(date=cstr(date), shift_type=shift.name), as_list=1)
			if len(recipients) > 0:
				recipients = [recipient[0] for recipient in recipients if recipient[0]]
				for recipient in recipients:
					checkin = frappe.new_doc("Employee Checkin")
					checkin.employee = recipient
					checkin.log_type = "OUT"
					checkin.skip_auto_attendance = 0
					checkin.save()

			frappe.db.commit()

@frappe.whitelist()
def issue_penalty(employee, date, penalty_code, shift, issuing_user, penalty_location):
	issuing_employee = frappe.get_value("Employee", {"user_id": issuing_user})
	penalty = frappe.get_value("Penalty Type", {"penalty_code" : penalty_code})
	site, project = frappe.get_value("Operations Shift", shift, ["site", "project"])
	site_location = frappe.get_value("Operations Site", site, "site_location")

	employee_id, employee_name, designation = frappe.get_value("Employee", employee, ["name", "employee_name", "designation"])

	penalty_issuance = frappe.new_doc("Penalty Issuance")
	penalty_issuance.issuing_time = now_datetime()
	penalty_issuance.location = penalty_location
	penalty_issuance.penalty_location = "Head Office"
	penalty_issuance.penalty_occurence_time = date
	penalty_issuance.shift = shift
	penalty_issuance.site = site
	penalty_issuance.project = project
	penalty_issuance.site_location = site_location
	penalty_issuance.append("employees", {
		"employee_id": employee_id,
		"employee_name": employee_name,
		"designation": designation,
	})
	penalty_issuance.append("penalty_issuance_details",{
		"penalty_type": penalty,
		"exact_notes": penalty
	})
	penalty_issuance.issuing_employee = issuing_employee
	# penalty_issuance.employee_name = self.lead_name
	penalty_issuance.flags.ignore_permissions = True
	penalty_issuance.insert()
	penalty_issuance.submit()
	frappe.msgprint(_('A penalty has been issued against {0}'.format(employee_name)))


def automatic_shift_assignment():
	date = cstr(getdate())
	end_previous_shifts()
	roster = frappe.get_all("Employee Schedule", {"date": date, "employee_availability": "Working" , "roster_type": "Basic"}, ["*"])
	for schedule in roster:
		create_shift_assignment(schedule, date)

def end_previous_shifts():
	date = datetime.date.today() - datetime.timedelta(days=1)
	shifts=frappe.get_list("Shift Assignment",  filters = {"end_date": ('is', 'not set')})
	for shift in shifts:
		Shift_name = shift.name
		doc = frappe.get_doc("Shift Assignment",Shift_name)
		doc.end_date = date
		doc.submit()

def create_shift_assignment(schedule, date):
	try:
		shift_assignment = frappe.new_doc("Shift Assignment")
		shift_assignment.start_date = date
		shift_assignment.employee = schedule.employee
		shift_assignment.employee_name = schedule.employee_name
		shift_assignment.department = schedule.department
		shift_assignment.post_type = schedule.post_type
		shift_assignment.shift = schedule.shift
		shift_assignment.site = schedule.site
		shift_assignment.project = schedule.project
		shift_assignment.shift_type = schedule.shift_type
		shift_assignment.post_type = schedule.post_type
		shift_assignment.post_abbrv = schedule.post_abbrv
		shift_assignment.roster_type = schedule.roster_type
		shift_assignment.submit()
	except Exception:
			frappe.log_error(frappe.get_traceback())

def overtime_shift_assignment():
	"""
	This method is to generate Shift Assignment for Employee Scheduling 
	with roster type 'Over_Time'. It first looks up for Shift Assignment
	of the employee for the day if he has any. Change the Status to "Inactive"
	and proceeds with creating New shift Assignments with Roster Type OverTime.
	"""
	date = cstr(getdate())
	now_time = now_datetime().strftime("%H:%M:00")
	roster = frappe.get_all("Employee Schedule", {"date": date, "employee_availability": "Working" , "roster_type": "Over-Time"}, ["*"])
	frappe.enqueue(process_overtime_shift,roster=roster, date=date, time=now_time, is_async=True, queue='long')

def process_overtime_shift(roster, date, time):
	for schedule in roster:	
		#Check for employee's shift assignment of the day, if he has any.
		shift_assignment = frappe.get_doc("Shift Assignment", {"employee":schedule.employee, "start_date": date},["name","shift_type"])
		if shift_assignment:
			shift_end_time = frappe.get_value("Shift Type",shift_assignment.shift_type, "end_time")
			#check if the given shift has ended
			# Set status inactive before creating new shift
			if str(shift_end_time) == str(time):
				frappe.set_value("Shift Assignment", shift_assignment.name,'status', "Inactive")
				create_shift_assignment(schedule, date)
		else:
			create_shift_assignment(schedule, date)

def update_shift_type():
	today_datetime = now_datetime()
	minute = today_datetime.strftime("%M")
	if 0 <= int(minute)-15 < 15:
		now_time = today_datetime.strftime("%H:15:00")
	elif 0 <= int(minute)-30 < 15:
		now_time = today_datetime.strftime("%H:30:00")
	elif 0 <= int(minute)-45 < 15:
		now_time = today_datetime.strftime("%H:45:00")
	else:
		now_time = today_datetime.strftime("%H:00:00")
	shift_types = frappe.get_all("Shift Type", {"end_time": now_time},["name", "allow_check_out_after_shift_end_time"])
	for shift_type in shift_types:
		last_sync_of_checkin = add_to_date(today_datetime, minutes=cint(shift_type.allow_check_out_after_shift_end_time)+15, as_datetime=True)
		doc = frappe.get_doc("Shift Type", shift_type.name)
		doc.last_sync_of_checkin = last_sync_of_checkin
		doc.save()
		frappe.db.commit()

@frappe.whitelist()
def process_attendance():
	now_time = now_datetime().strftime("%y-%m-%d %H:%M:00")
	shift_types = frappe.get_all("Shift Type", {"last_sync_of_checkin": now_time})
	for shift_type in shift_types:
		frappe.enqueue(mark_auto_attendance, shift_type, worker='long')

def mark_auto_attendance(shift_type):
	doc = frappe.get_doc("Shift Type", shift_type.name)
	doc.process_auto_attendance()


def update_shift_details_in_attendance(doc, method):
	if frappe.db.exists("Shift Assignment", {"employee": doc.employee, "start_date": doc.attendance_date}):
		site, project, shift, post_type, post_abbrv, roster_type = frappe.get_value("Shift Assignment", {"employee": doc.employee, "start_date": doc.attendance_date}, ["site", "project", "shift", "post_type", "post_abbrv", "roster_type"])
		frappe.db.sql("""update `tabAttendance`
			set project = %s, site = %s, operations_shift = %s, post_type = %s, post_abbrv = %s, roster_type = %s
			where name = %s """, (project, site, shift, post_type, post_abbrv, roster_type, doc.name))

def generate_payroll():
	start_date = add_to_date(getdate(), months=-1)
	end_date = get_end_date(start_date, 'monthly')['end_date']

	# Hardcoded dates for testing, remove below 2 lines for live
	#start_date = "2021-08-01"
	#end_date = "2021-08-31"

	try:
			create_payroll_entry(start_date, end_date)
	except Exception:
			frappe.log_error(frappe.get_traceback())

def generate_penalties():
	start_date = add_to_date(getdate(), months=-1)
	end_date = get_end_date(start_date, 'monthly')['end_date']

	filters = {
		'penalty_issuance_time': ['between', (start_date, end_date)],
		'workflow_state': 'Penalty Accepted'
	}
	logs = frappe.db.get_list('Penalty', filters=filters, fields="*", order_by="recipient_employee,penalty_issuance_time")
	for key, group in itertools.groupby(logs, key=lambda x: (x['recipient_employee'])):
		employee_penalties = list(group)
		calculate_penalty_amount(key, start_date, end_date, employee_penalties)

def calculate_penalty_amount(employee, start_date, end_date, logs):
	"""This Funtion Calculates the Penalty Amount based on the occurance and employees basic salary.

	Args:
		employee (String): employee ID
		start_date (date): Start Date of the payroll
		end_date (date): Start Date of the payroll
		logs ([type]): Employee's Penalty Log
	"""
	filters = {
		'docstatus': 1,
		'employee': employee
	}

	salary_structure, base = frappe.get_value("Salary Structure Assignment", filters, ["salary_structure","base"], order_by="from_date desc")

	if salary_structure:
		basic = frappe.db.sql("""
		SELECT amount,amount_based_on_formula,formula FROM `tabSalary Detail`
		WHERE parenttype="Salary Structure"
		AND parent=%s
		AND salary_component="Basic"
		""",(salary_structure), as_dict=1)
		if basic[0].amount_based_on_formula == 1:
			formula = basic[0].formula
			percent = formula.replace('base*','')
			basic_salary = int(base)*float(percent)
		else:
			basic_salary = basic[0].amount

	#Single day salary of employee = Basic Salary(WP salary) divided by 26 days
	single_day_salary = basic_salary / 26

	#Existing balance amount
	existing_balance = 0.00
	if frappe.db.exists("Penalty Deduction", {'employee': employee}):
		existing_balance = frappe.get_value("Penalty Deduction", {'employee': employee}, "balance_amount", order_by='posting_time desc')

	#Calculate new amount
	references =  ', '.join(['"{}"'.format(log.name) for log in logs])

	# references = '"HR-EMP-00002-006", "HR-EMP-00002-004"'
	damages_amount = frappe.db.sql("""
		SELECT sum(py.damage_amount) as damages_amount, py.name
		FROM `tabPenalty` as py
		WHERE py.name in ({refs})
	""".format(refs=references), as_dict=1)

	days_deduction = frappe.db.sql("""
		SELECT sum(pd.deduction) as days_deduction, pd.name
		FROM `tabPenalty Issuance Details` as pd
		WHERE
			pd.parenttype="Penalty"
		AND pd.parent in ({refs})
	""".format(refs=references), as_dict=1)

	# Days deduction
	days_deduction_amount = days_deduction[0].days_deduction * single_day_salary

	# Damages amount
	damages_amount = damages_amount[0].damages_amount

	# Sum of previous balance amount, days deduction amount and damages amount
	total_penalty_amount = existing_balance + days_deduction_amount + damages_amount

	# Maxmimum allowed deductible salary according to Kuwaiti law (5 days for penalties)
	max_amount = single_day_salary * 5

	#Amount to be deducted this time
	if total_penalty_amount > max_amount:
		deducted_amount = max_amount
		balance_amount = total_penalty_amount - max_amount
	else:
		deducted_amount = total_penalty_amount
		balance_amount = 0

	#Create Penalty Deduction Doc that in return creates Addition Salary with penalty component.
	create_penalty_deduction(start_date, end_date, employee, total_penalty_amount, single_day_salary, max_amount, deducted_amount, balance_amount)


def create_penalty_deduction(start_date, end_date, employee, total_penalty_amount, single_day_amount, max_amount, deducted_amount, balance_amount):
	penalty_deduction = frappe.new_doc("Penalty Deduction")
	penalty_deduction.posting_time = get_datetime()
	penalty_deduction.employee = employee
	penalty_deduction.from_date = start_date
	penalty_deduction.to_date = end_date
	penalty_deduction.total_penalty_amount = total_penalty_amount
	penalty_deduction.single_day_amount = single_day_amount
	penalty_deduction.maximum_amount = max_amount
	penalty_deduction.deducted_amount = deducted_amount
	penalty_deduction.balance_amount = balance_amount
	penalty_deduction.insert()
	penalty_deduction.submit()
	frappe.db.commit()

#this function is to generate Site Allowance as Earing Component in Salary Slip. It is monthly calculated based on employees attendance
def generate_site_allowance():
	#get list of all site that includes Site Allowance.
	operations_site = frappe.get_all("Operations Site", {"include_site_allowance":"1"},["name","allowance_amount"])

	#Gather the required Date details such as start date, and respective end date. Get current year and month to get the no. of days in the current month.
	start_date = add_to_date(getdate(), months=-1)
	end_date = get_end_date(start_date, 'monthly')['end_date']
	currentMonth = datetime.datetime.now().month
	currentYear = datetime.datetime.now().year
	no_of_days = monthrange(currentYear, currentMonth)[1]

	#generate site allowance for each site. Gets the employee and his/her respective no. of days in a given site.
	if operations_site:
			for site in operations_site:
				employee_det = frappe.db.sql("""
							SELECT employee,count(attendance_date) FROM `tabAttendance`
							WHERE
								site = '{site}'
							AND attendance_date between '{start_date}' and '{end_date}'
							And status = "Present"
							GROUP BY employee
						""".format(site=site.name,start_date = cstr(start_date), end_date = cstr(end_date)), as_list=1)

				if employee_det:
					for employee in employee_det:
						#calculate Monthly_site_allowance with the rate of allowance per day.
						Monthly_site_allowance =  round(int(site.allowance_amount)/no_of_days, 3)*int(employee[1])
						create_additional_salary(employee[0], Monthly_site_allowance, "Site Allowance", end_date)

#this function creates additional salary for a given component.
def create_additional_salary(employee, amount, component, end_date):
	additional_salary = frappe.new_doc("Additional Salary")
	additional_salary.employee = employee
	additional_salary.salary_component = component
	additional_salary.amount = amount
	additional_salary.payroll_date = end_date
	additional_salary.company = erpnext.get_default_company()
	additional_salary.overwrite_salary_structure_amount = 1
	additional_salary.notes = "Site Allowance"
	additional_salary.insert()
	additional_salary.submit()
