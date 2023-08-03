import itertools
from datetime import timedelta
from string import Template
from calendar import month, monthrange
from datetime import datetime, timedelta
from frappe import enqueue
import frappe, erpnext
from frappe import _
from frappe.model.workflow import apply_workflow
from frappe.utils import (
	now_datetime,nowtime, cstr, getdate, get_datetime, cint, add_to_date,
	datetime, today, add_days, now
)
from one_fm.api.doc_events import get_employee_user_id
from hrms.payroll.doctype.payroll_entry.payroll_entry import get_end_date
from one_fm.api.doc_methods.payroll_entry import auto_create_payroll_entry
from one_fm.utils import (
	mark_attendance, get_holiday_today, production_domain, get_today_leaves, get_salary_amount,
	get_leave_payment_breakdown
)
from one_fm.api.v1.roster import get_current_shift
from one_fm.processor import sendemail
from one_fm.api.api import push_notification_for_checkin, push_notification_rest_api_for_checkin
from one_fm.operations.doctype.employee_checkin_issue.employee_checkin_issue import approve_open_employee_checkin_issue
from hrms.hr.utils import get_holidays_for_employee

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
			message = _('<a class="btn btn-warning" href="/app/face-recognition">Hourly Check In</a>')
			send_notification(title, subject, message, category, recipients)

def checkin_checkout_initial_reminder():
	"""
	This function sends a push notification to users to remind them to checkin/checkout at the start/end time of their shift.
	"""
	try:
		if not frappe.db.get_single_value('HR and Payroll Additional Settings', 'remind_employee_checkin_checkout') and not production_domain():
			return

		# Get current date and time
		now_time = now_datetime().strftime("%Y-%m-%d %H:%M")

		# Get list of active shifts
		shifts_list = get_active_shifts(now_time)

		frappe.enqueue(schedule_initial_reminder, shifts_list=shifts_list, now_time=now_time, is_async=True, queue='long')

	except Exception as error:
		frappe.log_error(str(error), 'Checkin/checkout initial reminder failed')

def schedule_initial_reminder(shifts_list, now_time):
	notification_title = _("Checkin/Checkout reminder")
	notification_subject_in = _("Don't forget to Checkin!")
	notification_subject_out = _("Don't forget to CheckOut!")

	for shift in shifts_list:
		date = getdate()
		if shift.start_time < shift.end_time and nowtime() < cstr(shift.start_time):
			date = getdate() - timedelta(days=1)

		# Current time == shift start time => Checkin
		if strfdelta(shift.start_time, '%H:%M:%S') == cstr((get_datetime(now_time)).time()):
			recipients = checkin_checkout_query(date=cstr(date), shift_type=shift.name, log_type="IN")
			if len(recipients) > 0:
				notify_checkin_checkout_final_reminder(recipients=recipients,log_type="IN", notification_title= notification_title, notification_subject=notification_subject_in)

		# current time == shift end time => Checkout
		if strfdelta(shift.end_time, '%H:%M:%S') == cstr((get_datetime(now_time)).time()):
			recipients = checkin_checkout_query(date=cstr(date), shift_type=shift.name, log_type="OUT")

			if len(recipients) > 0:
				notify_checkin_checkout_final_reminder(recipients=recipients,log_type="OUT", notification_title= notification_title, notification_subject=notification_subject_out)

def checkin_checkout_final_reminder():
	"""
	This function sends a final notification to users to remind them to checkin/checkout.
	"""
	try:
		if not frappe.db.get_single_value('HR and Payroll Additional Settings', 'remind_employee_checkin_checkout') and not production_domain():
			return

		now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
		shifts_list = get_active_shifts(now_time)

		#Send final reminder to checkin or checkout to employees who have not even after shift has ended
		frappe.enqueue(schedule_final_notification, shifts_list=shifts_list, now_time=now_time, is_async=True, queue='long')
	except Exception as error:
		frappe.log_error(str(error), 'Checkin/checkout final reminder failed')

def schedule_final_notification(shifts_list, now_time):
	notification_title = _("Final Reminder")
	notification_subject_in =  _("Please checkin within the next 3 hours or you will be marked absent.")
	notification_subject_out =  _("Please checkout in the next five minutes.")


	for shift in shifts_list:
		date = getdate()
		if shift.start_time < shift.end_time and nowtime() < cstr(shift.start_time):
			date = getdate() - timedelta(days=1)
		# shift_start is equal to now time - notification reminder in mins
		# Employee won't receive checkin notification when accepted Arrive Late shift permission is present
		if (strfdelta(shift.start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.notification_reminder_after_shift_start))).time())) or (shift.has_split_shift == 1 and strfdelta(shift.second_shift_start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.notification_reminder_after_shift_start))).time())):
			recipients = checkin_checkout_query(date=cstr(date), shift_type=shift.name, log_type="IN")

			if len(recipients) > 0:
				notify_checkin_checkout_final_reminder(recipients=recipients,log_type="IN", notification_title= notification_title, notification_subject=notification_subject_in, is_after_grace_checkin=1)

		# shift_end is equal to now time - notification reminder in mins
		# Employee won't receive checkout notification when accepted Leave Early shift permission is present
		if (strfdelta(shift.end_time, '%H:%M:%S') == cstr((get_datetime(now_time)- timedelta(minutes=cint(shift.notification_reminder_after_shift_end))).time())) or (shift.has_split_shift == 1 and strfdelta(shift.first_shift_end_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.notification_reminder_after_shift_end))).time())):
			recipients = checkin_checkout_query(date=cstr(date), shift_type=shift.name, log_type="OUT")

			if len(recipients) > 0:
				notify_checkin_checkout_final_reminder(recipients=recipients, log_type="OUT", notification_title=notification_title, notification_subject=notification_subject_out)

#This function is the combination of two types of notification, email/log notifcation and push notification
@frappe.whitelist()
def notify_checkin_checkout_final_reminder(recipients, log_type, notification_title, notification_subject,  is_after_grace_checkin=0):
	"""
	params:
	recipients: Dictionary consist of user ID and Emplloyee ID eg: [{'user_id': 's.shaikh@armor-services.com', 'name': 'HR-EMP-00001'}]
	log_type: In or Out
	"""
	#defining the subject and message
	notification_category = "Attendance"

	checkin_message_body = """
					<a class="btn btn-success" href="/app/face-recognition">Check In</a>&nbsp;
					<br/>
					Submit a Shift Permission if you are planing to arrive late or forgot to checkin
					<a class="btn btn-primary" href="/app/shift-permission/new-shift-permission-1?log_type=IN&&permission_type=Arrive Late">Submit Shift Permission</a>&nbsp;
					<br/>
					Submit a Employee Checkin Issue if there are issues in checkin
					<a class="btn btn-secondary" href="/app/employee-checkin-issue/new-employee-checkin-issue-1?log_type=IN">Submit Employee Checkin Issue</a>&nbsp;
					<br/>
					<h3>{0}</h3>
					"""
	checkin_message = _(checkin_message_body.format("DON'T FORGET TO CHECKIN"))

	if is_after_grace_checkin:
		checkin_message = _(checkin_message_body.format("IF YOU DO NOT CHECK-IN WITHIN THE NEXT 3 HOURS, YOU WOULD BE MARKED AS ABSENT"))

	checkout_message = _("""
		<a class="btn btn-danger" href="/app/face-recognition">Check Out</a>
		<br/>
		Submit a Shift Permission if you are planing to leave early or forget to checkout
		<a class="btn btn-primary" href="/app/shift-permission/new-shift-permission-1?log_type=OUT&&permission_type=Leave Early"">Submit Shift Permission</a>&nbsp;
		<br/>
		Submit a Employee Checkin Issue if there are issues in checkout
		<a class="btn btn-secondary" href="/app/employee-checkin-issue/new-employee-checkin-issue-1?log_type=OUT">Submit Employee Checkin Issue</a>&nbsp;
		""")

	user_id_list = []

	#eg: recipient: {'user_id': 's.shaikh@armor-services.com', 'name': 'HR-EMP-00001'}
	for recipient in recipients:
		# Append the list of user ID to send notification through email.
		user_id_list.append(recipient.user_id)

		# Get Employee ID and User Role for the given recipient
		employee_id = recipient.name
		user_roles = frappe.get_roles(recipient.user_id)

		#cutomizing buttons according to log type.
		# check if employee yet to have record for attendance
		if log_type=="IN":
			#arrive late button is true only if the employee has the user role "Head Office Employee".
			if "Head Office Employee" in user_roles:
				push_notification_rest_api_for_checkin(employee_id, notification_title, notification_subject, checkin=True,arriveLate=True,checkout=False)
			else:
				push_notification_rest_api_for_checkin(employee_id, notification_title, notification_subject, checkin=True,arriveLate=False,checkout=False)
		if log_type=="OUT":
			push_notification_rest_api_for_checkin(employee_id, notification_title, notification_subject, checkin=False,arriveLate=False,checkout=True)


	# send notification mail to list of employee using user_id
	if log_type == "IN":
		send_notification(notification_title, notification_subject, checkin_message,notification_category,user_id_list)
	elif log_type == "OUT":
		send_notification(notification_title, notification_subject, checkout_message, notification_category, user_id_list)

@frappe.whitelist()
def checkin_checkout_supervisor_reminder():
	if not frappe.db.get_single_value('HR and Payroll Additional Settings', 'remind_employee_checkin_checkout') and not production_domain():
		return

	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	today_datetime = today()
	shifts_list = get_active_shifts(now_time)

	for shift in shifts_list:
		"""
			Send notification to supervisor of those who haven't checked in and don't have accepted shift permission
			with permission type Arrive Late/Forget to Checkin/Checkin Issue
		"""
		frappe.enqueue(supervisor_reminder,shift = shift,today_datetime = today_datetime ,now_time=now_time, is_async=True, queue='long')

def supervisor_reminder(shift, today_datetime, now_time):
	title = "Checkin Report"
	category = "Attendance"
	date = getdate()
	if shift.start_time < shift.end_time and nowtime() < cstr(shift.start_time):
		date = getdate() - timedelta(days=1)

	if (strfdelta(shift.start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.supervisor_reminder_shift_start))).time())) or (shift.has_split_shift == 1 and strfdelta(shift.second_shift_start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.supervisor_reminder_shift_start))).time())):
		checkin_time = today_datetime + " " + strfdelta(shift.start_time, '%H:%M:%S')
		recipients = checkin_checkout_query(date=cstr(date), shift_type=shift.name, log_type="IN")

		if len(recipients) > 0:
			for recipient in recipients:
				action_user, Role = get_action_user(recipient.name,recipient.shift)
				#for_user = get_employee_user_id(recipient.reports_to) if get_employee_user_id(recipient.reports_to) else get_notification_user(op_shift)
				subject = _("{employee} has not checked in yet.".format(employee=recipient.employee_name))
				action_message = _("""
				Submit a Shift Permission for the employee to give an excuse and not need to penalize
				<a class="btn btn-primary" href="/app/shift-permission/new-shift-permission-1">Submit Shift Permission</a>&nbsp;
				<br/><br/>
				Issue penalty for the employee
				<a class='btn btn-primary btn-danger no-punch-in' id='{employee}_{date}_{shift}' href="/app/penalty-issuance/new-penalty-issuance-1">Issue Penalty</a>
				""").format(shift=recipient.shift, date=cstr(now_time), employee=recipient.name, time=checkin_time)
				if action_user is not None:
					send_notification(title, subject, action_message, category, [action_user])

				notify_message = _("""Note that {employee} from Shift {shift} has Not Checked in yet.""").format(employee=recipient.employee_name, shift=recipient.shift)
				if Role:
					notify_user = get_notification_user(recipient.name,recipient.shift, Role)
					if notify_user is not None:
						send_notification(title, subject, notify_message, category, notify_user)

	"""
		Send notification to supervisor of those who haven't checked in and don't have accepted shift permission
		with permission type Leave Early/Forget to Checkout/Checkout Issue
	"""
	if (strfdelta(shift.end_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.supervisor_reminder_start_ends))).time())) or (shift.has_split_shift == 1 and strfdelta(shift.first_shift_end_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.supervisor_reminder_end_start))).time())):
		checkout_time = today_datetime + " " + strfdelta(shift.end_time, '%H:%M:%S')

		recipients = recipients = checkin_checkout_query(date=cstr(date), shift_type=shift.name, log_type="OUT")

		if len(recipients) > 0:
			for recipient in recipients:
				action_user, Role = get_action_user(recipient.name,recipient.shift)
				#for_user = get_employee_user_id(recipient.reports_to) if get_employee_user_id(recipient.reports_to) else get_notification_user(op_shift)
				subject = _('{employee} has not checked out yet.'.format(employee=recipient.employee_name))
				action_message = _("""
					Submit a Shift Permission for the employee to give an excuse and not need to penalize
					<a class="btn btn-primary" href="/app/shift-permission/new-shift-permission-1">Submit Shift Permission</a>&nbsp;
					<br/><br/>
					Issue penalty for the employee
					<a class='btn btn-primary btn-danger no-punch-in' id='{employee}_{date}_{shift}' href="/app/penalty-issuance/new-penalty-issuance-1">Issue Penalty</a>
					""").format(shift=recipient.shift, date=cstr(now_time), employee=recipient.name, time=checkout_time)
				if action_user is not None:
						send_notification(title, subject, action_message, category, [action_user])

				notify_message = _("""Note that {employee} from Shift {shift} has Not Checked Out yet.""").format(employee=recipient.employee_name, shift=recipient.shift)
				if Role:
						notify_user = get_notification_user(recipient.name,recipient.shift, Role)
						if notify_user is not None:
							send_notification(title, subject, notify_message, category, notify_user)
@frappe.whitelist()
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
			has_split_shift, first_shift_end_time, second_shift_start_time,
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

def checkin_checkout_query(date, shift_type, log_type):
	if log_type == "IN":
		permission_type = ("Arrive Late", "Forget to Checkin", "Checkin Issue")
	else:
		permission_type = ("Leave Early", "Forget to Checkout", "Checkout Issue")

	query = frappe.db.sql("""SELECT DISTINCT emp.user_id, emp.name , emp.employee_name, emp.holiday_list, tSA.shift
					FROM `tabShift Assignment` tSA, `tabEmployee` emp
					WHERE
						tSA.employee=emp.name
					AND tSA.start_date='{date}'
					AND tSA.shift_type='{shift_type}'
					AND tSA.docstatus=1
					AND emp.auto_attendance = 0
					and emp.status = "Active"
					AND tSA.start_date NOT IN
					(SELECT holiday_date from `tabHoliday` h
					WHERE
						h.parent = emp.holiday_list
					AND h.holiday_date = '{date}')
					AND emp.name NOT IN
					(SELECT employee FROM `tabShift Permission` emp_sp
						WHERE
							emp_sp.workflow_state='Approved'
						AND emp_sp.shift_type='{shift_type}'
						AND emp_sp.date='{date}'
						AND emp_sp.permission_type IN {permission_type}
					UNION ALL
					SELECT employee FROM `tabAttendance Request` att_req
						WHERE
							att_req.workflow_state='Approved'
						AND att_req.reason='Work From Home'
						AND CAST('{date} ' as date) BETWEEN att_req.from_date AND att_req.to_date
					UNION ALL
					SELECT employee FROM `tabLeave Application` LA
						WHERE
							LA.workflow_state='Approved'
						AND CAST('{date} ' as date) BETWEEN LA.from_date AND LA.to_date
					UNION ALL
					SELECT employee FROM `tabEmployee Checkin` empChkin
						WHERE
							empChkin.log_type='{log_type}'
						AND empChkin.skip_auto_attendance=0
						AND date(empChkin.time)='{date}'
						AND empChkin.shift_type='{shift_type}')
					""".format(date=cstr(date), shift_type=shift_type, log_type=log_type, permission_type=permission_type), as_dict=1)
	return query

@frappe.whitelist()
def get_action_user(employee, shift):
	"""
			Shift > Site > Project > Reports to
	"""
	action_user = None
	Role = None

	operations_shift = frappe.get_doc("Operations Shift", shift)
	operations_site = frappe.get_doc("Operations Site", operations_shift.site)
	project = frappe.get_doc("Project", operations_site.project)
	report_to = frappe.get_value("Employee", {"name":employee},["reports_to"])
	current_user = frappe.get_value("Employee", {"name":employee},["user_id"])

	if report_to:
		action_user = get_employee_user_id(report_to)
		Role = "Report To"
	else:
		if operations_shift.supervisor:
			shift_supervisor = get_employee_user_id(operations_shift.supervisor)
			if shift_supervisor != operations_shift.owner and shift_supervisor != current_user:
				action_user = shift_supervisor
				Role = "Shift Supervisor"

		elif operations_site.account_supervisor:
			site_supervisor = get_employee_user_id(operations_site.account_supervisor)
			if site_supervisor != operations_shift.owner and site_supervisor != current_user:
				action_user = site_supervisor
				Role = "Site Supervisor"

		elif operations_site.project:
			if project.account_manager:
				project_manager = get_employee_user_id(project.account_manager)
				if project_manager != operations_shift.owner and project_manager != current_user:
					action_user = project_manager
					Role = "Project Manager"

	return action_user, Role

def issue_penalties():
	"""This function to issue penalty to employee if employee checkin late without Shift Permission to Arrive Late.
	Also, if employee check out early withou Shift Permission to Leave Early
	"""
	# check if issue_penalty is enabled in the setting
	if not frappe.db.get_single_value('HR and Payroll Additional Settings', 'issue_penalty'):
		return

	#Define the constant
	penalty_code_late_checkin = "102"
	penalty_code_early_checkout="103"
	date = cstr(getdate())

	#Fetch the day's attendance
	attendance_list = frappe.get_list("Attendance",{"attendance_date":date},["*"])

	for attendance in attendance_list:
		#fetch location of the shift.
		location = get_location(attendance.operations_shift)

		if location:
			penalty_location = str(location[0].latitude)+","+str(location[0].longitude)
		else:
			penalty_location ="0,0"

		#Fetch Supervisor
		action_user, Role = get_action_user(attendance.employee,attendance.operations_shift)
		if Role:
			issuing_user = get_notification_user(attendance.employee,attendance.operations_shift,Role) if get_notification_user(attendance.employee,attendance.operations_shift,Role) else get_employee_user_id(frappe.get_value("Employee",{"name":attendance.employee},['reports_to']))
		else:
			issuing_user= get_employee_user_id(frappe.get_value("Employee",{"name":attendance.employee},['reports_to']))

		#Check if Shift Permission exists.
		shift_permission_late_entry = frappe.db.exists("Shift Permission",{'employee':attendance.employee,"date":date, "permission_type":"Arrive Late"})
		shift_permission_early_exit = frappe.db.exists("Shift Permission",{'employee':attendance.employee,"date":date, "permission_type":"Leave Early"})

		if attendance.late_entry == 1 and not shift_permission_late_entry:
			issue_penalty(attendance.employee, now_datetime(), penalty_code_late_checkin, attendance.operations_shift, issuing_user, penalty_location)

		if attendance.early_exit == 1 and not shift_permission_early_exit:
			issue_penalty(attendance.employee, now_datetime(), penalty_code_early_checkout, attendance.operations_shift, issuing_user, penalty_location)

@frappe.whitelist()
def get_notification_user(employee, shift, Role):
	"""
			Shift > Site > Project > Reports to
	"""
	operations_shift = frappe.get_doc("Operations Shift", shift)
	operations_site = frappe.get_doc("Operations Site", operations_shift.site)
	project = frappe.get_doc("Project", operations_site.project)
	project_manager = site_supervisor = shift_supervisor = None

	reports_to = frappe.get_value("Employee", {"name":employee},["reports_to"])

	if operations_site.project and project.account_manager and get_employee_user_id(project.account_manager) != operations_shift.owner:
		project_manager = get_employee_user_id(project.account_manager)
	if operations_site.account_supervisor and get_employee_user_id(operations_site.account_supervisor) != operations_shift.owner:
		site_supervisor = get_employee_user_id(operations_site.account_supervisor)
	elif operations_shift.supervisor and get_employee_user_id(operations_shift.supervisor) != operations_shift.owner:
		shift_supervisor = get_employee_user_id(operations_shift.supervisor)

	if Role == "Report To" and reports_to:
		notify_user = [get_employee_user_id(reports_to)]
	elif Role == "Shift Supervisor" and site_supervisor and project_manager:
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

	if not frappe.db.get_single_value('HR and Payroll Additional Settings', 'checkin_deadline'):
		return

	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	shifts_list = get_active_shifts(now_time)

	frappe.enqueue(mark_deadline_attendance, shifts_list=shifts_list, now_time = now_time, is_async=True, queue='long')

def mark_deadline_attendance(shifts_list, now_time):
	for shift in shifts_list:
		date = getdate()
		if shift.start_time < shift.end_time and nowtime() < cstr(shift.start_time):
			date = getdate() - timedelta(days=1)

		if shift.deadline==1:
			recipients = []
			if shift.has_split_shift == 1 and (now_time == shift.start_time + ((shift.first_shift_end_time - shift.start_time)/2) or now_time == shift.second_shift_start_time + ((shift.end_time -shift.second_shift_start_time)/2)):
				start_time_1 = datetime.datetime.strptime(cstr(date)+" "+cstr(shift.start_time - timedelta(minutes=cint(shift.begin_check_in_before_shift_start_time))), '%Y-%m-%d %H:%M:%S')
				start_time_2 = datetime.datetime.strptime(cstr(date)+" "+cstr(shift.second_shift_start_time - timedelta(minutes=cint(shift.begin_check_in_before_shift_start_time))), '%Y-%m-%d %H:%M:%S')
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
					NOT IN(SELECT employee FROM `tabAttendance Request` att_req
					WHERE
						att_req.employee=emp.name
					AND att_req.workflow_state='Approved'
					AND att_req.reason='Work From Home'
					AND CAST('{date} ' as date) BETWEEN att_req.from_date AND att_req.to_date)
					AND tSA.employee
					NOT IN(SELECT employee FROM `tabLeave Application` LA
					WHERE
						LA.employee=emp.name
					AND LA.workflow_state='Approved'
					AND CAST('{date} ' as date) BETWEEN LA.from_date AND LA.to_date)
					AND tSA.employee
					NOT IN(SELECT employee FROM `tabEmployee Checkin` empChkin
					WHERE
						empChkin.log_type="IN"
					AND empChkin.skip_auto_attendance=0
					AND date(empChkin.time)='{date}'
					AND empChkin.time BETWEEN '{start_time_1}' and '{now_time}'
					OR empChkin.time BETWEEN '{start_time_2}' and '{now_time}'
					AND empChkin.shift_type='{shift_type}')
					AND tSA.start_date
					NOT IN(SELECT holiday_date from `tabHoliday` h
					WHERE
						h.parent = emp.holiday_list
					AND h.holiday_date = '{date}')
				""".format(date=cstr(date), shift_type=shift.name, start_time_1 = start_time_1, start_time_2 = start_time_2, now_time = now_time), as_list=1)

			elif now_time == shift.start_time + ((shift.end_time - shift.start_time)/2):
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
					NOT IN(SELECT employee FROM `tabAttendance Request` att_req
					WHERE
						att_req.employee=emp.name
					AND att_req.workflow_state='Approved'
					AND att_req.reason='Work From Home'
					AND CAST('{date} ' as date) BETWEEN att_req.from_date AND att_req.to_date)
					AND tSA.employee
					NOT IN(SELECT employee FROM `tabLeave Application` LA
					WHERE
						LA.employee=emp.name
					AND LA.workflow_state='Approved'
					AND CAST('{date} ' as date) BETWEEN LA.from_date AND LA.to_date)
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
					mark_attendance(employee=employee, attendance_date=date, status='Absent', shift=shift.name)

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
	penalty_issuance.flags.ignore_permissions = True
	penalty_issuance.insert()
	penalty_issuance.submit()
	frappe.msgprint(_('A penalty has been issued against {0}'.format(employee_name)))

def fetch_non_shift(date, s_type):
	if s_type == "AM":
		roster = frappe.db.sql("""SELECT @roster_type := 'Basic' as roster_type, @start_datetime := "{date} 08:00:00" as start_datetime, @end_datetime := "{date} 17:00:00" as end_datetime,
				name as employee, employee_name, department, holiday_list, default_shift as shift_type, checkin_location, shift, site from `tabEmployee` E
				WHERE E.shift_working = 0
				AND E.status='Active'
				AND E.attendance_by_timesheet != 1
				AND E.default_shift IN(
					SELECT name from `tabShift Type` st
					WHERE st.start_time >= '01:00:00'
					AND  st.start_time < '13:00:00')
				AND NOT EXISTS(SELECT * from `tabHoliday` h
					WHERE
						h.parent = E.holiday_list
					AND h.holiday_date = '{date}')
		""".format(date=cstr(date)), as_dict=1)
	else:
		roster = frappe.db.sql("""SELECT @roster_type := 'Basic' as roster_type, name as employee, employee_name, department, holiday_list, default_shift as shift_type, checkin_location, shift, site from `tabEmployee` E
				WHERE E.shift_working = 0 
				AND E.status='Active' 
				AND E.attendance_by_timesheet != 1
				AND E.default_shift IN(
					SELECT name from `tabShift Type` st
					WHERE st.start_time < '01:00:00' OR st.start_time >= '13:00:00'
					)
				AND NOT EXISTS(SELECT * from `tabHoliday` h
					WHERE
						h.parent = E.holiday_list
					AND h.holiday_date = '{date}')
		""".format(date=cstr(date)), as_dict=1)
	print(roster)
	return roster


def assign_am_shift():
	date = cstr(getdate())
	end_previous_shifts("AM")
	roster = frappe.db.sql("""
			SELECT * from `tabEmployee Schedule` ES
			WHERE
			ES.date = '{date}'
			AND ES.employee_availability = "Working"
			AND ES.roster_type = "Basic"
			AND ES.shift_type IN(
				SELECT name from `tabShift Type` st
				WHERE st.start_time >= '01:00:00'
				AND  st.start_time < '13:00:00')
			AND ES.employee IN(
				SELECT name from `tabEmployee`
				WHERE status = "Active")
	""".format(date=cstr(date)), as_dict=1)

	non_shift = fetch_non_shift(date, "AM")
	if non_shift:
		roster.extend(non_shift)

	create_shift_assignment(roster, date, 'AM')


def assign_pm_shift():
	date = cstr(getdate())
	end_previous_shifts("PM")
	roster = frappe.db.sql("""
			SELECT * from `tabEmployee Schedule` ES
			WHERE
			ES.date = '{date}'
			AND ES.employee_availability = "Working"
			AND ES.roster_type = "Basic"
			AND ES.shift_type IN(
				SELECT name from `tabShift Type` st
				WHERE st.start_time < '01:00:00' OR st.start_time >= '13:00:00'
				)
			AND ES.employee IN(
				SELECT name from `tabEmployee` 
				WHERE status = "Active")
	""".format(date=cstr(date)), as_dict=1)

	non_shift = fetch_non_shift(date, "PM")
	if non_shift:
		roster.extend(non_shift)

	create_shift_assignment(roster, date, 'PM')


def end_previous_shifts(time):
	shift_type = get_shift_type(time)
	query = f"""
		UPDATE `tabShift Assignment`
		SET end_date=DATE(end_datetime)
		WHERE
		end_date IS NULL AND shift_type IN {tuple(shift_type)} AND docstatus=1 AND roster_type in ('Basic', 'Over-Time')
	;"""
	shift_assignments = frappe.db.sql(query, values=[], as_dict=1)
	frappe.db.commit()

def get_shift_type(time):
	if time == "AM":
		shift_type = frappe.get_list("Shift Type", {"start_time": [">=", "01:00"], "start_time": ["<", "13:00"]},['name'], pluck='name')
	else:
		shift_type = frappe.get_list("Shift Type", {"start_time": [">=", "13:00"]},['name'], pluck='name')
	return shift_type

def create_shift_assignment(roster, date, time):
	try:
		owner = frappe.session.user
		creation = now()
		shift_type = get_shift_type(time)
		shift_types = frappe.db.get_list("Shift Type", filters={'name':['IN', shift_type]},
			fields=['name', 'shift_type', 'start_time', 'end_time'])
		shift_types_dict = {}
		for i in shift_types:
			i.start_datetime = f"{date} {(datetime.datetime.min + i.start_time).time()}"
			if i.end_time.total_seconds() < i.start_time.total_seconds():
				i.end_datetime = f"{add_days(date, 1)} {(datetime.datetime.min + i.end_time).time()}"
			else:
				i.end_datetime = f"{date} {(datetime.datetime.min + i.end_time).time()}"
			shift_types_dict[i.name] = i
		default_shift = frappe.get_doc("Shift Type", '"Standard|Morning|08:00:00-17:00:00|9 hours"').as_dict()


		existing_shift = frappe.db.get_list("Shift Assignment", filters={
			'start_date': date,
			'shift_type': ['IN', shift_type],
			'docstatus': 1,
			'roster_type': ['IN', ['Basic']],
			'status':'Active',
			},
			fields=['employee']
		)

		existing_shift_list = [i.employee for i in existing_shift]
		shift_request = frappe.db.get_list("Shift Request", filters={
			'employee': ['IN', [i.employee for i in roster]],
			'from_date': ['<=', date],
			'to_date': ['>=', date],
			'workflow_state': 'Approved'
			},
			fields=['name', 'employee', 'check_in_site', 'check_out_site']
		)
		shift_request_dict = {}
		for i in shift_request:
			shift_request_dict[i.employee] = i

		sites = []
		for i in roster:
			if not i.site in sites:
				sites.append(i.site)
		sites_list = frappe.db.get_list("Operations Site", filters={'name': ['IN', sites]}, fields=['name', 'site_location'])
		sites_list_dict = {}
		for i in sites_list:
			sites_list_dict[i.name] = i.site_location

		# remove employees with approved leaves
		todays_leaves = get_today_leaves(str(date))
		roster = [i for i in roster if not i.employee in todays_leaves]
		if roster:
			query = """
				INSERT INTO `tabShift Assignment` (`name`, `company`, `docstatus`, `employee`, `employee_name`, `shift_type`, `site`, `project`, `status`,
				`shift_classification`, `site_location`, `start_date`, `start_datetime`, `end_datetime`, `department`,
				`shift`, `operations_role`, `post_abbrv`, `roster_type`, `owner`, `modified_by`, `creation`, `modified`,
				`shift_request`, `check_in_site`, `check_out_site`)
				VALUES
			"""
			# check if all roster has been done
			has_rostered = []
			for r in roster:
				if not r.employee in existing_shift_list:
					_shift_type = shift_types_dict.get(r.shift_type) or default_shift

					query += f"""
					(
						"HR-SHA-{date}-{r.employee}", "{frappe.defaults.get_user_default('company')}", 1, "{r.employee}", "{r.employee_name}", '{r.shift_type}',
						"{r.site or ''}", "{r.project or ''}", 'Active', "{_shift_type.shift_type}", "{sites_list_dict.get(r.site) or ''}", "{date}",
						"{_shift_type.start_datetime or str(date)+' 08:00:00'}",
						"{_shift_type.end_datetime or str(date)+' 17:00:00'}", "{r.department}", "{r.shift or ''}", "{r.operations_role or ''}", "{r.post_abbrv or ''}", "{r.roster_type}",
						"{owner}", "{owner}", "{creation}", "{creation}" """
					if shift_request_dict.get(r.employee):
						_shift_request = shift_request_dict.get(r.employee)
						query += f""", "{_shift_request.name}", "{_shift_request.check_in_site}", "{_shift_request.check_out_site}"), """
					else:
						query += """, '', '', ''),"""
				else:
					has_rostered.append(r.employee_name)
			query = query[:-1]
			query += f"""
				ON DUPLICATE KEY UPDATE
				modified_by = VALUES(modified_by),
				docstatus = VALUES(docstatus),
				modified = "{creation}",
				operations_role = VALUES(operations_role),
				post_abbrv = VALUES(post_abbrv),
				roster_type = VALUES(roster_type),
				shift = VALUES(shift),
				project = VALUES(project),
				site = VALUES(site),
				shift_type = VALUES(shift_type),
				employee = VALUES(employee),
				employee_name = VALUES(employee_name),
				site_location = VALUES(site_location),
				start_datetime = VALUES(start_datetime),
				end_datetime = VALUES(end_datetime),
				department = VALUES(department),
				shift_request = VALUES(shift_request),
				check_in_site = VALUES(check_in_site),
				check_out_site = VALUES(check_out_site),
				shift_classification = VALUES(shift_classification),
				status = VALUES(status)
			"""
			frappe.db.sql(query, values=[], as_dict=1)
			frappe.db.commit()

			if has_rostered:
				frappe.log_error(str(has_rostered), 'Duplicate Shift Assignment')
	except Exception as e:
		sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
		recipient = frappe.get_value("Email Account", {"name":"Support"}, ["email_id"])
		msg = frappe.render_template('one_fm/templates/emails/missing_shift_assignment.html', context={"rosters": roster})
		sendemail(sender=sender, recipients= recipient, content=msg, subject="Shift Assignment Failed", delayed=False)

def validate_am_shift_assignment():
	date = cstr(getdate())
	end_previous_shifts("PM")
	roster = frappe.db.sql("""
			SELECT * from `tabEmployee Schedule` ES
			WHERE
			ES.date = '{date}'
			AND ES.employee_availability = "Working"
			AND ES.roster_type = "Basic"
			AND ES.shift_type IN(
				SELECT name from `tabShift Type` st
				WHERE st.start_time >= '01:00:00'
				AND  st.start_time < '13:00:00')
			AND ES.employee
			NOT IN (Select employee from `tabShift Assignment` tSA
			WHERE
				tSA.employee = ES.employee
				AND tSA.start_date='{date}'
				AND tSA.roster_type = "Basic"
				AND tSA.shift_type IN(
					SELECT name from `tabShift Type` st
					WHERE st.start_time >= '01:00:00'
					AND  st.start_time < '13:00:00'	))
			AND ES.employee
			NOT IN (Select employee from `tabEmployee` E
			WHERE
				E.name = ES.employee
				AND E.status = "Left")
	""".format(date=cstr(date)), as_dict=1)

	non_shift = fetch_non_shift(date, "PM")
	if non_shift:
		roster.extend(non_shift)

	# remove approved leaves for today
	todays_leaves = get_today_leaves(str(date))
	roster = [i for i in roster if not i.employee in todays_leaves]

	if len(roster)>0:
		sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
		recipient = frappe.get_value("Email Account", {"name":"Support"}, ["email_id"])
		msg = frappe.render_template('one_fm/templates/emails/missing_shift_assignment.html', context={"rosters": roster})
		sendemail(sender=sender, recipients= recipient, content=msg, subject="Missed Shift Assignments List", delayed=False)
		frappe.enqueue(create_shift_assignment, roster = roster, date = date, time='AM', is_async=True, queue='long')

def validate_pm_shift_assignment():
	date = cstr(getdate())
	end_previous_shifts("PM")
	roster = frappe.db.sql("""
			SELECT * from `tabEmployee Schedule` ES
			WHERE
			ES.date = '{date}'
			AND ES.employee_availability = "Working"
			AND ES.roster_type = "Basic"
			AND ES.shift_type IN(
				SELECT name from `tabShift Type` st
				WHERE st.start_time < '01:00:00' OR st.start_time >= '13:00:00'
				)
			AND ES.employee
			NOT IN (Select employee from `tabShift Assignment` tSA
			WHERE
				tSA.employee = ES.employee
				AND tSA.start_date='{date}'
				AND tSA.roster_type = "Basic"
				AND tSA.shift_type IN(
					SELECT name from `tabShift Type` st
					WHERE st.start_time < '01:00:00' OR st.start_time >= '13:00:00'))
			AND ES.employee
			NOT IN (Select employee from `tabEmployee` E
			WHERE
				E.name = ES.employee
				AND E.status = "Left")
	""".format(date=cstr(date)), as_dict=1)
	non_shift = fetch_non_shift(date, "PM")
	if non_shift:
		roster.extend(non_shift)

	# remove approved leaves for today
	todays_leaves = get_today_leaves(str(date))
	roster = [i for i in roster if not i.employee in todays_leaves]

	if len(roster)>0:
		sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
		recipient = frappe.get_value("Email Account", {"name":"Support"}, ["email_id"])
		msg = frappe.render_template('one_fm/templates/emails/missing_shift_assignment.html', context={"rosters": roster})
		sendemail(sender=sender, recipients= recipient, content=msg, subject="Missed Shift Assignments List", delayed=False)
		frappe.enqueue(create_shift_assignment, roster = roster, date = date, time='PM', is_async=True, queue='long')


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
		try:
			shift_assignment = frappe.get_doc("Shift Assignment", {"employee":schedule.employee, "start_date": date},["name","shift_type"])
			if shift_assignment:
				shift_end_time = frappe.get_value("Shift Type",shift_assignment.shift_type, "end_time")
				#check if the given shift has ended
				# Set status inactive before creating new shift
				if str(shift_end_time) == str(time):
					frappe.set_value("Shift Assignment", shift_assignment.name,'status', "Inactive")
					create_overtime_shift_assignment(schedule, date)
			else:
				create_overtime_shift_assignment(schedule, date)
		except Exception as e:
			pass

def create_overtime_shift_assignment(schedule, date):
	if (not frappe.db.exists("Shift Assignment",{"employee":schedule.employee, "start_date":getdate(date), "status":"Active"}) and
			frappe.db.exists('Employee', {'employee':schedule.employee, 'status':'Active'})):
		try:
			shift_assignment = frappe.new_doc("Shift Assignment")
			shift_assignment.start_date = date
			shift_assignment.employee = schedule.employee
			shift_assignment.employee_name = schedule.employee_name
			shift_assignment.department = schedule.department
			shift_assignment.operations_role = schedule.operations_role
			shift_assignment.shift = schedule.shift
			shift_assignment.site = schedule.site
			shift_assignment.project = schedule.project
			shift_assignment.shift_type = schedule.shift_type
			shift_assignment.operations_role = schedule.operations_role
			shift_assignment.post_abbrv = schedule.post_abbrv
			shift_assignment.roster_type = schedule.roster_type
			shift_assignment.site_location = schedule.checkin_location
			if frappe.db.exists("Shift Request", {'employee':schedule.employee, 'from_date':['<=',date],'to_date':['>=',date]}):
				shift_request, check_in_site, check_out_site = frappe.get_value("Shift Request", {'employee':schedule.employee, 'from_date':['<=',date],'to_date':['>=',date]},["name","check_in_site","check_out_site"])
				shift_assignment.shift_request = shift_request
				shift_assignment.check_in_site = check_in_site
				shift_assignment.check_out_site = check_out_site
			shift_assignment.submit()
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Create Shift Assignment")


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


def generate_payroll():
	'''
		Method to generate payroll on 24th of each month(method calling form cron job for 24th in hooks.py)
	'''
	try:
		auto_create_payroll_entry()
	except Exception:
		frappe.log_error(frappe.get_traceback())

def generate_penalties():
	# start_date = add_to_date(getdate(), months=-1)
	# end_date = get_end_date(start_date, 'monthly')['end_date']

	#fetch Payroll date's day
	date = frappe.db.get_single_value('HR and Payroll Additional Settings', 'payroll_date')
	year = getdate().year - 1 if getdate().day < cint(date) and  getdate().month == 1 else getdate().year
	month = getdate().month if getdate().day >= cint(date) else getdate().month - 1

	#calculate Payroll date, start and end date.

	payroll_date = datetime.datetime(year, month, cint(date)).strftime("%Y-%m-%d")
	start_date = add_to_date(payroll_date, months=-1)
	end_date = add_to_date(payroll_date, days=-1)

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
	if frappe.db.exists('Employee', {'employee':employee, 'status':'Left'}):
		return

	if frappe.db.get_single_value('HR and Payroll Additional Settings', 'basic_salary_component'):
		basic_salary_component = frappe.db.get_single_value('HR and Payroll Additional Settings', 'basic_salary_component')
	else:
		frappe.throw("Please Add Basic Salary Component in HR and Payroll Additional Settings.")

	salary_structure, base = frappe.get_value("Salary Structure Assignment", filters, ["salary_structure","base"], order_by="from_date desc")

	if salary_structure:
		basic = frappe.db.sql("""
		SELECT amount,amount_based_on_formula,formula FROM `tabSalary Detail`
		WHERE parenttype="Salary Structure"
		AND parent=%s
		AND salary_component=%s
		""",(salary_structure, basic_salary_component), as_dict=1)
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
	operations_site = frappe.get_all("Operations Site", {"include_site_allowance":"1"},["name","allowance_amount", "project"])

	component_name = frappe.db.get_single_value('HR and Payroll Additional Settings', 'site_allowance_additional_salary_component')
	if not component_name:
		component_name = "Site Allowance"


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
							SELECT employee, employee_name, count(attendance_date) as count FROM `tabAttendance`
							WHERE
								site = '{site}'
							AND attendance_date between '{start_date}' and '{end_date}'
							And status = "Present"
							GROUP BY employee
						""".format(site=site.name,start_date = cstr(start_date), end_date = cstr(end_date)), as_dict=1)

				if employee_det:
					for employee in employee_det:
						#calculate Monthly_site_allowance with the rate of allowance per day.
						Monthly_site_allowance =  round(int(site.allowance_amount)/no_of_days, 3)*int(employee["count"])
						notes = f"Project: {site.project} \nSite: {site.name} \nNumber of days worked: {employee['count']} \n\n"
						create_additional_salary(employee["employee"], Monthly_site_allowance, component_name, end_date, notes)

#this function creates additional salary for a given component.
def create_additional_salary(employee, amount, component, end_date, notes):
	try:
		check_add_sal_exists = frappe.db.exists("Additional Salary",
			{"employee": employee, "payroll_date": end_date, "salary_component": component, "docstatus": 1}
		)
		if check_add_sal_exists:
			additional_salary = frappe.get_doc("Additional Salary", check_add_sal_exists)
			additional_salary.amount += amount
			if additional_salary.notes:
				additional_salary.notes += notes
			else:
				additional_salary.notes = notes
			additional_salary.flags.ignore_validate_update_after_submit = True
			additional_salary.save(ignore_permissions=1)
		else:
			additional_salary = frappe.new_doc("Additional Salary")
			additional_salary.employee = employee
			additional_salary.salary_component = component
			additional_salary.amount = amount
			additional_salary.payroll_date = end_date
			additional_salary.company = erpnext.get_default_company()
			additional_salary.overwrite_salary_structure_amount = 1
			additional_salary.notes = notes
			additional_salary.insert()
			additional_salary.submit()
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), 'Additional Salary - {0}'.format(component))

def generate_ot_additional_salary():
	# Gather the required Date details such as start date, and respective end date.
	start_date = add_to_date(getdate(), months=-1)
	end_date = get_end_date(start_date, 'monthly')['end_date']

	# Fetch payroll details from HR and Payroll Additional Settings
	overtime_component = frappe.db.get_single_value("HR and Payroll Additional Settings", 'overtime_additional_salary_component')
	working_day_overtime_rate = frappe.db.get_single_value("HR and Payroll Additional Settings", 'working_day_overtime_rate')
	day_off_overtime_rate = frappe.db.get_single_value("HR and Payroll Additional Settings", 'day_off_overtime_rate')
	public_holiday_overtime_rate = frappe.db.get_single_value("HR and Payroll Additional Settings", 'public_holiday_overtime_rate')

	# Get the OverTime Attendance for the date range
	attendance_list = frappe.db.sql("""
		SELECT
			*
		FROM
			`tabAttendance`
		WHERE
			attendance_date between '{start_date}' and '{end_date}'
			AND status = "Present" AND roster_type = "Over-Time" AND docstatus = 1
		GROUP BY
			employee, attendance_date
	""".format(start_date = cstr(start_date), end_date = cstr(end_date)), as_dict=1)

	if attendance_list and len(attendance_list) > 0:
		for attendance_doc in attendance_list:
			process_attendance_for_ot_additional_salary(attendance_doc, overtime_component, working_day_overtime_rate, day_off_overtime_rate, public_holiday_overtime_rate, end_date)

def process_attendance_for_ot_additional_salary(attendance_doc, overtime_component, working_day_overtime_rate, day_off_overtime_rate, public_holiday_overtime_rate, end_date):
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
	roster_type_overtime = "Over-Time"

	days_of_week = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

	# Check if attendance is for roster type: Over-Time
	if attendance_doc.roster_type == roster_type_overtime:

		payroll_date = cstr(attendance_doc.attendance_date)

		overtime_duration = attendance_doc.working_hours
		project_has_overtime_rate = False
		project_overtime_rate = 0

		if attendance_doc.operations_shift:
			# Fetch project and duration of the shift employee worked in operations shift
			project, overtime_duration = frappe.db.get_value("Operations Shift", attendance_doc.operations_shift, ["project", "duration"])
			# Fetch overtime details from project
			project_has_overtime_rate, project_overtime_rate = frappe.db.get_value("Project", {'name': project}, ["has_overtime_rate", "overtime_rate"])

		# If project has a specified overtime rate, calculate amount based on overtime rate and create additional salary
		if project_has_overtime_rate:
			if project_overtime_rate > 0:
				amount = round(project_overtime_rate * overtime_duration, 3)
				notes = f"Attendance: {attendance_doc.name} \nProject: {project} \nCalculated based on ot rate set for the project\nProject ot rate: {project_overtime_rate} \n\n"
				create_additional_salary(attendance_doc.employee, amount, overtime_component, end_date, notes)
			else:
				error_msg = _("Overtime rate must be greater than zero for project: {project}".format(project=project))
				frappe.log_error(error_msg, 'OT Additional Salary - Attendance {0}'.format(attendance_doc.name))

		# If no overtime rate is specified, follow labor law => (Basic Hourly Wage * number of worked hours * 1.5)
		else:
			# Fetch assigned shift, basic salary  and holiday list for the given employee
			assigned_shift, holiday_list = frappe.db.get_value("Employee", {'employee': attendance_doc.employee}, ["shift", "holiday_list"])
			basic_salary = get_salary_amount(attendance_doc.employee)
			if assigned_shift:
				# Fetch duration of the shift employee is assigned to
				assigned_shift_duration = frappe.db.get_value("Operations Shift", assigned_shift, ["duration"])

				if basic_salary and basic_salary > 0:
					# Compute hourly wage
					daily_wage = round(basic_salary/30, 3)
					hourly_wage = round(daily_wage/assigned_shift_duration, 3)

					# Check if a OverTime schedule exists for the employee in the attendance date
					if frappe.db.exists("Employee Schedule", {'employee': attendance_doc.employee, 'date': attendance_doc.attendance_date, 'employee_availability': "Working", 'roster_type': roster_type_overtime}):

						if working_day_overtime_rate > 0:

							# Compute amount as per working day rate
							amount = round(hourly_wage * overtime_duration * working_day_overtime_rate, 3)
							notes = f"Attendance: {attendance_doc.name} \nCalculated based on working day rate => Basic hourly wage*Duration of worked hours*Working day overtime rate => {hourly_wage}*{overtime_duration}*{working_day_overtime_rate} = {amount} \n\n"
							create_additional_salary(attendance_doc.employee, amount, overtime_component, end_date, notes)
						else:
							error_msg = _("No Wroking Day overtime rate set in HR and Payroll Additional Settings.")
							frappe.log_error(error_msg, 'OT Additional Salary - Attendance {0}'.format(attendance_doc.name))

					# Check if attendance date falls in a holiday list
					elif holiday_list:

						# Pass last parameter as "False" to get weekly off days
						holidays_weekly_off = get_holidays_for_employee(attendance_doc.employee, attendance_doc.attendance_date, attendance_doc.attendance_date, False, False)

						# Pass last paramter as "True" to get non weekly off days, ie, public/additional holidays
						holidays_public_holiday = get_holidays_for_employee(attendance_doc.employee, attendance_doc.attendance_date, attendance_doc.attendance_date, False, True)

						# Check for weekly off days length and if description of day off is set as one of the weekdays. (By default, description is set to a weekday name)
						if len(holidays_weekly_off) > 0 and holidays_weekly_off[0].description in days_of_week:

							if day_off_overtime_rate > 0:
								# Compute amount as per day off rate
								amount = round(hourly_wage * overtime_duration * day_off_overtime_rate, 3)
								notes = f"Attendance: {attendance_doc.name} \nCalculated based on day off rate => Basic hourly wage*Duration of worked hours*Day off overtime rate => {hourly_wage}*{overtime_duration}*{day_off_overtime_rate} = {amount} \n\n"
								create_additional_salary(attendance_doc.employee, amount, overtime_component, end_date, notes)
							else:
								error_msg = _("No Day Off overtime rate set in HR and Payroll Additional Settings.")
								frappe.log_error(error_msg, 'OT Additional Salary - Attendance {0}'.format(attendance_doc.name))

						# Check for weekly off days set to "False", ie, Public/additional holidays in holiday list
						elif len(holidays_public_holiday) > 0:

							if public_holiday_overtime_rate > 0:
								# Compute amount as per public holiday rate
								amount = round(hourly_wage * overtime_duration * public_holiday_overtime_rate, 3)
								notes = f"Attendance: {attendance_doc.name} \nCalculated based on day off rate => Basic hourly wage*Duration of worked hours*Public holiday overtime rate => ({hourly_wage}*{overtime_duration}*{public_holiday_overtime_rate}={amount})\n\n"
								create_additional_salary(attendance_doc.employee, amount, overtime_component, end_date, notes)
							else:
								error_msg = _("No Public Holiday overtime rate set in HR and Payroll Additional Settings.")
								frappe.log_error(error_msg, 'OT Additional Salary - Attendance {0}'.format(attendance_doc.name))
					else:
						error_msg = _("No basic Employee Schedule or Holiday List found for employee: {employee}".format(employee=attendance_doc.employee))
						frappe.log_error(error_msg, 'OT Additional Salary - Attendance {0}'.format(attendance_doc.name))
				else:
					error_msg = _("Basic Salary not set for employee: {employee} in the employee record.".format(employee=attendance_doc.employee))
					frappe.log_error(error_msg, 'OT Additional Salary - Attendance {0}'.format(attendance_doc.name))
			else:
				error_msg = _("Shift not set for employee: {employee} in the employee record.".format(employee=attendance_doc.employee))
				frappe.log_error(error_msg, 'OT Additional Salary - Attendance {0}'.format(attendance_doc.name))

def generate_sick_leave_deduction():
	# Gather the required Date details such as start date, and respective end date.
	start_date = add_to_date(getdate(), months=-1)
	end_date = get_end_date(start_date, 'monthly')['end_date']
	# Get the OverTime Attendance for the date range
	leave_list = frappe.db.sql("""
		select
			la.name, la.employee, la.leave_type, la.total_leave_days, lt.one_fm_paid_sick_leave_deduction_salary_component
		from
			`tabLeave Application` la, `tabLeave Type` lt
		where
			(
				la.from_date between '{start_date}' and '{end_date}'
				or
				la.to_date between '{start_date}' and '{end_date}'
				or
				(
					la.from_date < '{start_date}' and la.to_date > '{end_date}'
				)
			)
			and
				lt.one_fm_is_paid_sick_leave = 1
			and
				lt.name = la.leave_type
			and
				la.status = 'Approved'
 		group by
			employee, from_date
	""".format(start_date = cstr(start_date), end_date = cstr(end_date)), as_dict=1)

	if leave_list and len(leave_list) > 0:
		for leave in leave_list:
			deduct_for_paid_sick_leave(leave, end_date)

def deduct_for_paid_sick_leave(doc, end_date):
	salary = get_salary_amount(doc.employee)
	daily_rate = salary/30
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details
	leave_details = get_leave_details(doc.employee, end_date)
	curr_year_applied_days = 0
	if doc.leave_type in leave_details['leave_allocation'] and leave_details['leave_allocation'][doc.leave_type]:
		curr_year_applied_days = leave_details['leave_allocation'][doc.leave_type]['leaves_taken']
	if curr_year_applied_days == 0:
		curr_year_applied_days = doc.total_leave_days

	leave_payment_breakdown = get_leave_payment_breakdown(doc.leave_type)

	total_payment_days = 0
	if leave_payment_breakdown:
		threshold_days = 0
		for payment_breakdown in leave_payment_breakdown:
			payment_days = 0
			threshold_days += payment_breakdown.threshold_days
			if total_payment_days < doc.total_leave_days:
				if curr_year_applied_days >= threshold_days and (curr_year_applied_days - doc.total_leave_days) < threshold_days:
					payment_days = threshold_days - (curr_year_applied_days-doc.total_leave_days) - total_payment_days
				elif curr_year_applied_days <= threshold_days: # Gives true this also doc.total_leave_days <= threshold_days:
					payment_days = doc.total_leave_days - total_payment_days
				if payment_days > 0:
					create_additional_salary_for_paid_sick_leave(doc, daily_rate, salary, payment_days, end_date, payment_breakdown)
				total_payment_days += payment_days

		if total_payment_days < doc.total_leave_days and doc.total_leave_days-total_payment_days > 0:
			payment_days = doc.total_leave_days-total_payment_days
			if payment_days > 0:
				create_additional_salary_for_paid_sick_leave(doc, daily_rate, salary, payment_days, end_date)

def create_additional_salary_for_paid_sick_leave(doc, daily_rate, salary, payment_days, end_date, payment_breakdown=False):
	deduction_percentage = 1
	salary_component = doc.one_fm_paid_sick_leave_deduction_salary_component
	if payment_breakdown:
		deduction_percentage = payment_breakdown.salary_deduction_percentage/100
		salary_component = payment_breakdown.salary_component
	amount = payment_days*daily_rate*deduction_percentage
	if amount > 0:
		deduction_notes = """
			Leave Application: <b>{0}</b><br>
			Employee Salary: <b>{1}</b><br>
			Daily Rate: <b>{2}</b><br>
			Deduction Days Number: <b>{3}</b><br>
			Deduction Percent: <b>{4}%</b><br/>
			Deduct Amount: <b>{5}</b><br/><br/>
		""".format(doc.name, salary, daily_rate, payment_days, deduction_percentage*100, amount)
		create_additional_salary(doc.employee, amount, salary_component, end_date, deduction_notes)


def get_current_schedules(employee, log_type=None):
	# check if employee has logs in
	# Employee Checkin, Shift Request, Shift Permission
	# Attendance Request, Leaves
	employee_doc = frappe.db.get_value("Employee", employee, ['name', 'holiday_list'])
	start_date = str(getdate())
	curr_shift = get_current_shift(employee)
	# check day off
	if frappe.db.exists('Employee Schedule', {
			'employee':employee,
			'date':start_date,
			'employee_availability':'Day Off'
			}
		):
		return False

	# check holiday
	if get_holiday_today(start_date).get(employee_doc.holiday_list):
		return False

	if curr_shift:
		# check for leaves
		if frappe.db.sql(f"""
				SELECT name, employee FROM `tabLeave Application`
				WHERE employee='{employee}' AND status IN ('Open', 'Approved')
				AND '{start_date}' BETWEEN from_date AND to_date;
			""", as_dict=1):
			return False
		# check for shift permission:
		if frappe.db.exists('Shift Permission', {
			'employee':employee,
			'assigned_shift': curr_shift.name,
			'log_type':log_type
			}):
			return False

		# check for shift request:
		if frappe.db.sql(f"""
				SELECT name, employee FROM `tabShift Request`
				WHERE employee='{employee}' AND docstatus=1
				AND '{start_date}' BETWEEN from_date AND to_date;
			""", as_dict=1):
			return False
		# check attendance request
		if frappe.db.sql(f"""
				SELECT name, employee FROM `tabAttendance Request`
				WHERE employee='{employee}' AND docstatus=1
				AND '{start_date}' BETWEEN from_date AND to_date;
			""", as_dict=1):
			return False
		# check employee checkin
		if frappe.db.exists('Employee Checkin', {
			'employee':employee,
			'shift_assignment': curr_shift.name,
			'log_type':log_type
			}):
			return False
		return True
	else:
		return False




# Notifications reminder
def fetch_employees_not_in_checkin():
	"""
	This method fetch list of employees yet to checkin or have shift permission,
	attendance request, shift request, leave application based on log_type and
	if their shift start or end falls withing the current hour
	"""
	if not production_domain():
		return
	# if not frappe.db.get_single_value('HR and Payroll Additional Settings', 'remind_employee_checkin_checkout') and not production_domain():
	# 	return

	shift_start_time = f"{now_datetime().time().hour}:00:00"
	minute = now_datetime().time().minute
	hour = now_datetime().time().hour
	cur_date = str(getdate())
	return_data = []
	log_types = ['IN', 'OUT']
	for log_type in log_types:
		# capture current minute
		if log_type=='IN':
			reminder_minutes = [i.minute for i in frappe.db.sql("""
				SELECT notification_reminder_after_shift_start as minute FROM `tabShift Type`
				WHERE notification_reminder_after_shift_start>0
				GROUP BY notification_reminder_after_shift_start;
			""", as_dict=1)]
			supervisor_reminder_minutes = [i.minute for i in frappe.db.sql("""
				SELECT supervisor_reminder_shift_start as minute FROM `tabShift Type`
				WHERE supervisor_reminder_shift_start>0
				GROUP BY supervisor_reminder_shift_start;
			""", as_dict=1)]
		else:
			reminder_minutes = [i.minute for i in frappe.db.sql("""
				SELECT notification_reminder_after_shift_end as minute FROM `tabShift Type`
				WHERE notification_reminder_after_shift_end>0
				GROUP BY notification_reminder_after_shift_end;
			""", as_dict=1)]
			supervisor_reminder_minutes = [i.minute for i in frappe.db.sql("""
				SELECT supervisor_reminder_start_ends as minute FROM `tabShift Type`
				WHERE supervisor_reminder_start_ends>0
				GROUP BY supervisor_reminder_start_ends;
			""", as_dict=1)]


		# get employees from shift assignment, check them in checkins and substract
		shift_assignments_employees_list = frappe.db.sql(f"""
			SELECT DISTINCT sa.employee, sa.shift_type, sa.start_datetime, sa.end_datetime,
			sa.shift as operations_shift, st.notification_reminder_after_shift_start,
			st.notification_reminder_after_shift_end, st.supervisor_reminder_shift_start,
			st.supervisor_reminder_start_ends, os.supervisor as shift_supervisor,
			osi.account_supervisor as site_supervisor

			FROM `tabShift Assignment` sa RIGHT JOIN `tabShift Type` st ON sa.shift_type=st.name
			RIGHT JOIN `tabOperations Shift` os ON sa.shift=os.name RIGHT JOIN `tabOperations Site` osi
			ON sa.site=osi.name

			WHERE {'sa.start_datetime' if log_type=='IN' else 'sa.end_datetime'}='{cur_date} {shift_start_time}'
			AND sa.status='Active' AND sa.docstatus=1
			GROUP BY sa.employee
		""", as_dict=1)
		if not shift_assignments_employees_list:
			return
		shift_assignments_employees = [i.employee for i in shift_assignments_employees_list]
		# make map of employee against shift type
		shift_assignments_employees_dict = {}
		for i in shift_assignments_employees_list:
			shift_assignments_employees_dict[i.employee] = i

		shift_assignments_employees_tuple = str(tuple(shift_assignments_employees)).replace(',)', ')')
		# fetch checkins
		checkins = [i.employee for i in frappe.db.sql(f"""
			SELECT employee FROM `tabEmployee Checkin`
			WHERE date='{cur_date}' AND employee IN {shift_assignments_employees_tuple}
			AND log_type='{log_type}'
			GROUP BY employee
		""", as_dict=1)]
		employees_yet_to_checkin = [i for i in shift_assignments_employees if not i in checkins]

		# check shift permissions, attendance request, leave application
		shift_permissions = [i.employee for i in frappe.db.sql(f"""
			SELECT employee FROM `tabShift Permission`
			WHERE date='{cur_date}' AND employee IN {shift_assignments_employees_tuple}
			AND log_type='{log_type}'
			GROUP BY employee
		""", as_dict=1)]
		employees_yet_to_checkin = [i for i in employees_yet_to_checkin if not i in shift_permissions]
		# attendance request
		attendance_request = [i.employee for i in frappe.db.sql(f"""
			SELECT employee FROM `tabAttendance Request`
			WHERE  docstatus=1
			AND '{cur_date}' BETWEEN from_date AND to_date
			AND employee IN {shift_assignments_employees_tuple}
			GROUP BY employee
		""", as_dict=1)]
		employees_yet_to_checkin = [i for i in employees_yet_to_checkin if not i in attendance_request]
		# leave application
		leave_application = [i.employee for i in frappe.db.sql(f"""
			SELECT employee FROM `tabLeave Application`
			WHERE status IN ('Open', 'Approved')
			AND '{cur_date}' BETWEEN from_date AND to_date
			AND employee IN {shift_assignments_employees_tuple}
		""", as_dict=1)]
		employees_yet_to_checkin = [i for i in employees_yet_to_checkin if not i in leave_application]

		# shift request
		shift_request = [i.employee for i in frappe.db.sql(f"""
			SELECT employee FROM `tabShift Request`
			WHERE  docstatus=1 AND '{cur_date}' BETWEEN from_date AND to_date
			AND employee IN {shift_assignments_employees_tuple}
		""", as_dict=1)]
		employees_yet_to_checkin = [i for i in employees_yet_to_checkin if not i in shift_request]

		# holiday list
		holiday_list = [i for i,j in get_holiday_today(cur_date).items()]
		holiday_list_employees = [i.name for i in frappe.db.get_list("Employee", filters={
			'name': ['IN', employees_yet_to_checkin],
			'status':'Active',
			'holiday_list': ['IN', holiday_list]
		})]
		employees_yet_to_checkin = [i for i in employees_yet_to_checkin if not i in holiday_list_employees]

		employee_details = frappe.db.get_list("Employee", filters={
			'name': ['IN', employees_yet_to_checkin]},
			fields=['name', 'employee_id', 'employee_name', 'user_id', 'prefered_contact_email',
			'prefered_email', 'reports_to']
		)

		if log_type=='IN':
			for i in employee_details:
				if shift_assignments_employees_dict.get(i.name):
					i = {**i, **shift_assignments_employees_dict.get(i.name), **{'log_type':'IN'}}
					del i['name']
					# check if is_after_grace_period
					if minute in reminder_minutes:i['is_after_grace_checkin'] = True
					else:i['is_after_grace_checkin'] = False
					# check if supervisor reminder
					if minute in supervisor_reminder_minutes:i['is_supervisor_checkin_reminder'] = True
					else:i['is_supervisor_checkin_reminder'] = False
					# check initial
					if (minute==i['start_datetime'].minute and hour==i['start_datetime'].hour):i['initial_checkin_reminder']=True
					else:i['initial_checkin_reminder']=False
					return_data.append(frappe._dict(i))
		else:
			for i in employee_details:
				if shift_assignments_employees_dict.get(i.name):
					i = {**i, **shift_assignments_employees_dict.get(i.name), **{'log_type':'OUT'}}
					del i['name']
					# check if is_after_grace_period
					if minute in reminder_minutes:i['is_after_grace_checkout'] = True
					else:i['is_after_grace_checkout'] = False
					# check if supervisor reminder
					if minute in supervisor_reminder_minutes:i['is_supervisor_checkout_reminder'] = True
					else:i['is_supervisor_checkout_reminder'] = False
					# check initial
					if (minute==i['end_datetime'].minute and hour==i['end_datetime'].hour):i['initial_checkout_reminder']=True
					else:i['initial_checkout_reminder']=False
					return_data.append(frappe._dict(i))

	return frappe._dict({
		'employees':return_data,
		# 'reminder_minutes':reminder_minutes,
		# 'supervisor_reminder_minutes': supervisor_reminder_minutes,
		'minute':minute, 'date':cur_date, 'total':len(return_data)
	})

def has_checkin_record(employee, log_type, date):
	if frappe.db.exists('Employee Checkin', {
		'employee':employee,
		'date': date,
		'log_type':log_type
		}):return True
	return False


def initiate_checkin_notification(res):
	"""
	params:
	recipients: Dictionary consist of user ID and Emplloyee ID eg: [{'user_id': 's.shaikh@armor-services.com', 'name': 'HR-EMP-00001'}]
	log_type: In or Out
	"""
	now_time = now()
	checkin_message = _(f"""
		<a class="btn btn-success" href="/app/face-recognition">Check In</a>&nbsp;
		<br>
		Submit a Shift Permission if you are planing to arrive late
		<a class="btn btn-primary" href="/app/shift-permission/new-shift-permission-1">Submit Shift Permission</a>&nbsp;
		<br>
		Submit an Attendance Request if there are issues in checkin or you forgot to checkin
		<a class="btn btn-secondary" href="/app/attendance-request/new-attendance-request-1">Submit Attendance Request</a>&nbsp;
		<br>
		Submit a Shift Request if you are trying to checkin from another site location
		<a class="btn btn-info" href="/app/shift-request/new-shift-request-1">Submit Shift Request</a>&nbsp;
		<h3>DON'T FORGET TO CHECKIN</h3>
	""")

	checkin_message_after_grace = _("""
		<a class="btn btn-success" href="/app/face-recognition">Check In</a>&nbsp;
		<br>
		Submit a Shift Permission if you are planing to arrive late
		<a class="btn btn-primary" href="/app/shift-permission/new-shift-permission-1">Submit Shift Permission</a>&nbsp;
		<br>
		Submit an Attendance Request if there are issues in checkin or you forgot to checkin
		<a class="btn btn-secondary" href="/app/attendance-request/new-attendance-request-1">Submit Attendance Request</a>&nbsp;
		<br>
		Submit a Shift Request if you are trying to checkin from another site location
		<a class="btn btn-info" href="/app/shift-request/new-shift-request-1">Submit Shift Request</a>&nbsp;
		<h3>IF YOU DO NOT CHECK-IN WITHIN THE NEXT 3 HOURS, YOU WOULD BE MARKED AS ABSENT</h3>
	""")


	checkout_message = _("""
		<a class="btn btn-danger" href="/app/face-recognition">Check Out</a>
		Submit a Shift Permission if you are planing to leave early or is there any issue in checkout or forget to checkout
		<a class="btn btn-primary" href="/app/shift-permission/new-shift-permission-1">Submit Shift Permission</a>&nbsp;
		""")

	user_id_list = []
	checkin_reminders = []
	checkout_reminders = []
	after_grace_checkin_reminder = []
	after_grace_checkout_reminder = []
	supervisor_checkin_reminder = []
	supervisor_checkout_reminder = []

	#eg: recipient: {'user_id': 's.shaikh@armor-services.com', 'name': 'HR-EMP-00001'}
	for recipient in res.employees:
		# split employees into lists
		if recipient.initial_checkin_reminder:
			checkin_reminders.append(recipient)
		elif recipient.is_after_grace_checkin:
			after_grace_checkin_reminder.append(recipient)
		elif recipient.is_supervisor_checkin_reminder:
			supervisor_checkin_reminder.append(recipient)
		elif recipient.initial_checkout_reminder:
			checkout_reminders.append(recipient)
		elif recipient.is_after_grace_checkout:
			after_grace_checkout_reminder.append(recipient)
		elif recipient.is_supervisor_checkout_reminder:
			supervisor_checkout_reminder.append(recipient)

	# process initial checkins
	if checkin_reminders:
		checkin_reminder_id_list = []
		notification_category = 'Attendance'
		notification_title = _("Checkin reminder")
		notification_subject = _("Checkin in the next 5 minutes!")
		for recipient in checkin_reminders:
			# if not has_checkin_record(recipient.employee, recipient.log_type, res.date):
			# Append the list of user ID to send notification through email.
			checkin_reminder_id_list.append(recipient.user_id)
			#arrive late button is true only if the employee has the user role "Head Office Employee".
			user_roles = frappe.get_roles(recipient.user_id)
			if "Head Office Employee" in user_roles:
				push_notification_rest_api_for_checkin(
					recipient.employee, notification_title, notification_subject,
					checkin=True, arriveLate=True, checkout=False)
			else:
				push_notification_rest_api_for_checkin(
					recipient.employee, notification_title, notification_subject,
					checkin=True,arriveLate=False,checkout=False)
		send_notification(
			notification_title, notification_subject, checkin_message,
			notification_category, checkin_reminder_id_list
		)

	# # process checkins after grace period
	if after_grace_checkin_reminder:
		checkin_reminder_id_list = []
		notification_category = 'Attendance'
		notification_title = _("Checkin reminder")
		notification_subject = _("Don't forget to Checkin!")
		for recipient in after_grace_checkin_reminder:
			# if not has_checkin_record(recipient.employee, recipient.log_type, res.date):
			# Append the list of user ID to send notification through email.
			checkin_reminder_id_list.append(recipient.user_id)
			#arrive late button is true only if the employee has the user role "Head Office Employee".
			user_roles = frappe.get_roles(recipient.user_id)
			if "Head Office Employee" in user_roles:
				push_notification_rest_api_for_checkin(
					recipient.employee, notification_title, notification_subject,
					checkin=True, arriveLate=True, checkout=False)
			else:
				push_notification_rest_api_for_checkin(
					recipient.employee, notification_title, notification_subject,
					checkin=True,arriveLate=False,checkout=False)
		send_notification(
			notification_title, notification_subject, checkin_message_after_grace,
			notification_category, checkin_reminder_id_list
		)


	# # process supervisor checkin reminder
	if supervisor_checkin_reminder:
		title = "Checkin Report"
		category = "Attendance"
		date = getdate()
		for recipient in supervisor_checkin_reminder:
			action_user, Role = get_action_user(recipient.employee,recipient.operations_shift)
			subject = _("{employee} has not checked in yet.".format(employee=recipient.employee_name))
			action_message = _("""
				Submit a Shift Permission for the employee to give an excuse and not need to penalize
				<a class="btn btn-primary" href="/app/shift-permission/new-shift-permission-1?employee={recipient.employee}&log_type=IN">Submit Shift Permission</a>&nbsp;
				<br/><br/>
				Issue penalty for the employee
				<a class='btn btn-primary btn-danger no-punch-in' id='{employee}_{date}_{shift}' href="/app/penalty-issuance/new-penalty-issuance-1">Issue Penalty</a>
			""").format(recipient=recipient, shift=recipient.operations_shift, date=cstr(now_time), employee=recipient.employee, time=str(recipient.start_datetime))
			if action_user is not None: #and not has_checkin_record(recipient.employee, recipient.log_type, res.date):
				send_notification(title, subject, action_message, category, [action_user])

			# notify_message = _("""Note that {employee} from Shift {shift} has Not Checked in yet.""").format(employee=recipient.employee_name, shift=recipient.operations_shift)
			# if Role:
			# 	notify_user = get_notification_user(recipient.employee,recipient.operations_shift, Role)
			# 	if notify_user is not None: #and not has_checkin_record(recipient.employee, recipient.log_type, res.date):
			# 		send_notification(title, subject, notify_message, category, notify_user)

	# # process initial checkout
	if checkout_reminders:
		checkout_reminder_id_list = []
		notification_category = 'Attendance'
		notification_title = _("Checkout reminder")
		notification_subject = _("Don't forget to Checkout!")
		for recipient in checkout_reminders:
			# if not has_checkin_record(recipient.employee, recipient.log_type, res.date):
			# Append the list of user ID to send notification through email.
			checkout_reminder_id_list.append(recipient.user_id)
			#arrive late button is true only if the employee has the user role "Head Office Employee".
			user_roles = frappe.get_roles(recipient.user_id)
			if "Head Office Employee" in user_roles:
				push_notification_rest_api_for_checkin(
					recipient.employee, notification_title, notification_subject,
					checkin=False, arriveLate=False, checkout=True)
			else:
				push_notification_rest_api_for_checkin(
					recipient.employee, notification_title, notification_subject,
					checkin=False,arriveLate=False,checkout=True)
		send_notification(
			notification_title, notification_subject, checkout_message,
			notification_category, checkout_reminder_id_list
		)


	# # process supervisor checkout reminder
	if supervisor_checkout_reminder:
		title = "Checkout Report"
		category = "Attendance"
		date = getdate()
		for recipient in supervisor_checkout_reminder:
			action_user, Role = get_action_user(recipient.employee,recipient.operations_shift)
			subject = _("{employee} has not checked out yet.".format(employee=recipient.employee_name))
			action_message = _("""
				Submit a Shift Permission for the employee to give an excuse and not need to penalize
				<a class="btn btn-primary" href="/app/shift-permission/new-shift-permission-1?employee={recipient.employee}&log_type=OUT">Submit Shift Permission</a>&nbsp;
				<br/><br/>
				Issue penalty for the employee
				<a class='btn btn-primary btn-danger no-punch-in' id='{employee}_{date}_{shift}' href="/app/penalty-issuance/new-penalty-issuance-1">Issue Penalty</a>

			""").format(recipient=recipient, shift=recipient.operations_shift, date=cstr(now_time), employee=recipient.employee, time=str(recipient.start_datetime))
			if action_user is not None:# and not has_checkin_record(recipient.employee, recipient.log_type, res.date):
				send_notification(title, subject, action_message, category, [action_user])

			# notify_message = _("""Note that {employee} from Shift {shift} has Not Checked out yet.""").format(employee=recipient.employee_name, shift=recipient.operations_shift)
			# if Role:
			# 	notify_user = get_notification_user(recipient.employee,recipient.operations_shift, Role)
			# 	if notify_user is not None:# and not has_checkin_record(recipient.employee, recipient.log_type, res.date):
			# 		send_notification(title, subject, notify_message, category, notify_user)


def run_checkin_reminder():
	# execute first checkin reminder

	try:
		res = fetch_employees_not_in_checkin()
		if res:
			initiate_checkin_notification(res)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), 'Checkin Notification')
  
  
