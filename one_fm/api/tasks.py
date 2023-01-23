import itertools
from datetime import timedelta
from string import Template
from calendar import month, monthrange
from datetime import datetime, timedelta
from frappe import enqueue
import frappe, erpnext
from frappe import _
from frappe.utils import now_datetime,nowtime, cstr, getdate, get_datetime, cint, add_to_date, datetime, today, add_days, now
from one_fm.api.doc_events import get_employee_user_id
from hrms.payroll.doctype.payroll_entry.payroll_entry import get_end_date
from one_fm.api.doc_methods.payroll_entry import auto_create_payroll_entry
from one_fm.utils import mark_attendance
from one_fm.api.mobile.roster import get_current_shift
from one_fm.processor import sendemail
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
			message = _('<a class="btn btn-warning" href="/app/face-recognition">Hourly Check In</a>')
			send_notification(title, subject, message, category, recipients)

def checkin_checkout_initial_reminder():
	"""
	This function sends a push notification to users to remind them to checkin/checkout at the start/end time of their shift.
	"""
	try:
		if not frappe.db.get_single_value('HR and Payroll Additional Settings', 'remind_employee_checkin_checkout'):
			return

		# Get current date and time
		now_time = now_datetime().strftime("%Y-%m-%d %H:%M")

		# Get list of active shifts
		shifts_list = get_active_shifts(now_time)

		frappe.enqueue(schedule_initial_reminder, shifts_list=shifts_list, now_time=now_time, is_async=True, queue='long')

	except Exception as error:
		frappe.log_error(str(error), 'Checkin/checkout initial reminder failed')

def schedule_initial_reminder(shifts_list, now_time):
	notification_title = _("Checkout reminder")
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
		if not frappe.db.get_single_value('HR and Payroll Additional Settings', 'remind_employee_checkin_checkout'):
			return

		now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
		shifts_list = get_active_shifts(now_time)

		#Send final reminder to checkin or checkout to employees who have not even after shift has ended
		frappe.enqueue(schedule_final_notification, shifts_list=shifts_list, now_time=now_time, is_async=True, queue='long')
	except Exception as error:
		frappe.log_error(str(error), 'Checkin/checkout final reminder failed')

def schedule_final_notification(shifts_list, now_time):
	notification_title = _("Final Reminder")
	notification_subject_in =  _("Please checkin in the next five minutes.")
	notification_subject_out =  _("Please checkin in the next five minutes.")

	
	for shift in shifts_list:
		date = getdate()
		if shift.start_time < shift.end_time and nowtime() < cstr(shift.start_time):
			date = getdate() - timedelta(days=1)
		# shift_start is equal to now time - notification reminder in mins
		# Employee won't receive checkin notification when accepted Arrive Late shift permission is present
		if (strfdelta(shift.start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.notification_reminder_after_shift_start))).time())) or (shift.has_split_shift == 1 and strfdelta(shift.second_shift_start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.notification_reminder_after_shift_start))).time())):
			recipients = checkin_checkout_query(date=cstr(date), shift_type=shift.name, log_type="IN")

			if len(recipients) > 0:
				notify_checkin_checkout_final_reminder(recipients=recipients,log_type="IN", notification_title= notification_title, notification_subject=notification_subject_in)

		# shift_end is equal to now time - notification reminder in mins
		# Employee won't receive checkout notification when accepted Leave Early shift permission is present
		if (strfdelta(shift.end_time, '%H:%M:%S') == cstr((get_datetime(now_time)- timedelta(minutes=cint(shift.notification_reminder_after_shift_end))).time())) or (shift.has_split_shift == 1 and strfdelta(shift.first_shift_end_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.notification_reminder_after_shift_end))).time())):
			recipients = checkin_checkout_query(date=cstr(date), shift_type=shift.name, log_type="OUT")

			if len(recipients) > 0:
				notify_checkin_checkout_final_reminder(recipients=recipients,log_type="IN", notification_title= notification_title, notification_subject=notification_subject_out)

#This function is the combination of two types of notification, email/log notifcation and push notification
@frappe.whitelist()
def notify_checkin_checkout_final_reminder(recipients, log_type, notification_title, notification_subject):
	"""
	params:
	recipients: Dictionary consist of user ID and Emplloyee ID eg: [{'user_id': 's.shaikh@armor-services.com', 'name': 'HR-EMP-00001'}]
	log_type: In or Out
	"""
	#defining the subject and message
	notification_category = "Attendance"

	checkin_message = _("""
					<a class="btn btn-success" href="/app/face-recognition">Check In</a>&nbsp;
					Submit a Shift Permission if you are plannig to arrive late or is there any issue in checkin or forget to checkin
					<a class="btn btn-primary" href="/app/shift-permission/new-shift-permission-1">Submit Shift Permission</a>&nbsp;
					""")

	checkout_message = _("""
		<a class="btn btn-danger" href="/app/face-recognition">Check Out</a>
		Submit a Shift Permission if you are plannig to leave early or is there any issue in checkout or forget to checkout
		<a class="btn btn-primary" href="/app/shift-permission/new-shift-permission-1">Submit Shift Permission</a>&nbsp;
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
	if not frappe.db.get_single_value('HR and Payroll Additional Settings', 'remind_supervisor_checkin_checkout'):
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
	# penalty_issuance.employee_name = self.lead_name
	penalty_issuance.flags.ignore_permissions = True
	penalty_issuance.insert()
	penalty_issuance.submit()
	frappe.msgprint(_('A penalty has been issued against {0}'.format(employee_name)))

def fetch_non_shift(date, s_type):
	if s_type == "AM":
		roster = frappe.db.sql("""SELECT @roster_type := 'Basic' as roster_type, @start_datetime := "{date} 08:00:00" as start_datetime, @end_datetime := "{date} 17:00:00" as end_datetime,  
				name as employee, employee_name, department, holiday_list, default_shift as shift_type, checkin_location, shift, site from `tabEmployee` E
				WHERE E.shift_working = 0
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
				AND E.default_shift IN(
					SELECT name from `tabShift Type` st
					WHERE st.start_time < '01:00:00' OR st.start_time >= '13:00:00'
					)
				AND NOT EXISTS(SELECT * from `tabHoliday` h
					WHERE
						h.parent = E.holiday_list
					AND h.holiday_date = '{date}')
		""".format(date=cstr(date)), as_dict=1)

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
		shift_type = frappe.get_list("Shift Type", {"start_time": [">=", "00:00"], "start_time": ["<", "12:00"]},['name'], pluck='name')
	else:
		shift_type = frappe.get_list("Shift Type", {"start_time": [">=", "12:00"]},['name'], pluck='name')
	return shift_type

def create_shift_assignment(roster, date, time):
	owner = frappe.session.user
	creation = now()
	shift_type = get_shift_type(time)
	shift_types = frappe.db.get_list("Shift Type", filters={'name':['IN', shift_type]},
		fields=['name', 'shift_type', 'start_time', 'end_time'])
	shift_types_dict = {}
	for i in shift_types:
		i.start_datetime = f"{date} {i.start_time}"
		if i.end_time.total_seconds() < i.start_time.total_seconds():
			i.end_datetime = f"{add_days(date, 1)} {i.end_time}"
		else:
			i.end_datetime = f"{date} {i.end_time}"
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
		'to_date': ['>=', date]
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
	
	if roster:
		query = """
			INSERT INTO `tabShift Assignment` (`name`, `company`, `docstatus`, `employee`, `employee_name`, `shift_type`, `site`, `project`, `status`,
			`shift_classification`, `site_location`, `start_date`, `start_datetime`, `end_datetime`, `department`, 
			`shift`, `operations_role`, `post_abbrv`, `roster_type`, `owner`, `modified_by`, `creation`, `modified`,
			`shift_request`, `check_in_site`, `check_out_site`)
			VALUES 
		"""
		# check if all roster has been done
		has_rostered = False
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
				has_rostered = True
		
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
		if not has_rostered:
			frappe.db.sql(query, values=[], as_dict=1)
			frappe.db.commit()

	if time == 'AM':
		mark_day_attendance()


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

def update_shift_details_in_attendance(doc, method):
	condition = ''
	if frappe.db.exists("Employee Schedule",
		{"employee": doc.employee, "date": doc.attendance_date, "roster_type": "Over-Time", "day_off_ot": True}):
		condition += ' day_off_ot="1"'
	shift_assignment = frappe.get_list("Shift Assignment",{"employee": doc.employee, "start_date": doc.attendance_date},["name", "site", "project", "shift", "shift_type", "operations_role", "start_datetime","end_datetime", "roster_type"])
	if shift_assignment and len(shift_assignment) > 0 :
		shift_data = shift_assignment[0]
		condition += """ shift_assignment="{shift_assignment[0].name}" """.format(shift_assignment=shift_assignment)
		
		for key in shift_assignment[0]:
			if shift_data[key] and key not in ["name","start_datetime","end_datetime", "shift", "shift_type"]: 
				condition += """, {key}="{value}" """.format(key= key,value=shift_data[key])
			if key == "shift" and shift_data["shift"]:
				condition += """, operations_shift="{shift}" """.format(shift=shift_data["shift"])
			if key == "shift_type" and shift_data["shift_type"]:
				condition += """, shift='{shift_type}' """.format(shift_type=shift_data["shift_type"])

		if doc.attendance_request or frappe.db.exists("Shift Permission", {"employee": doc.employee, "date":doc.attendance_date,"workflow_state":"Approved"}):
			condition += """, in_time='{start_datetime}', out_time='{end_datetime}' """.format(start_datetime=cstr(shift_data["start_datetime"]), end_datetime=cstr(shift_data["end_datetime"]))
	if condition:
		query = """UPDATE `tabAttendance` SET {condition} WHERE name= "{name}" """.format(condition=condition, name = doc.name)
		return frappe.db.sql(query)
	return

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



def mark_day_attendance():
	start_date, end_date = add_days(getdate(), -1), add_days(getdate(), -1)
	frappe.enqueue(mark_daily_attendance, start_date=start_date, end_date=end_date, timeout=4000, queue='long')

def mark_night_attendance():
	start_date = add_days(getdate(), -1)
	end_date =  getdate()
	frappe.enqueue(mark_daily_attendance, start_date=start_date, end_date=end_date, timeout=4000, queue='long')



# mark daily attendance
def mark_daily_attendance(start_date, end_date):
	"""
		This method marks attendance for all employees
	"""
	try:
		errors = []
		owner = frappe.session.user
		creation = now()
		# get holiday for today
		holiday_today = get_holiday_today(start_date)
		# Get shift type and make hashmap
		shift_types = frappe.get_list("Shift Type", fields="*")
		shift_types_dict = {}
		for i in shift_types:
			shift_types_dict[i.name] = i
		
		# get employee schedule
		employee_schedules = frappe.db.get_list("Employee Schedule", filters={'date':start_date, 'employee_availability':'Day Off'}, fields="*")
		employee_schedule_dict = {}
		for i in employee_schedules:
			employee_schedule_dict[i.employee] = i
		
		employees = frappe.get_list("Employee", fields="*")
		employees_data = {}
		for i in employees:
			employees_data[i.name] = i

		employees_dict = {}


		# get attendance for the day
		attendance_list = frappe.get_list("Attendance", filters={"attendance_date":start_date, 'status': ['NOT IN', ['On Leave', 'Work From Home', 'Day Off', 'Holiday', 'Present']]})
		attendance_dict = {}
		for i in attendance_list:
			attendance_dict[i.employee] = i
		# present attendance
		present_attendance_list = frappe.get_list("Attendance", filters={"attendance_date":start_date, 'status': ['IN', ['On Leave', 'Work From Home', 'Day Off', 'Holiday', 'Present']]})
		present_attendance_dict = {}
		for i in present_attendance_list:
			present_attendance_dict[i.employee] = i

		# Get shift assignment and make hashmap
		shift_assignments = frappe.db.sql(f"""
			SELECT * FROM `tabShift Assignment` WHERE start_date="{start_date}" AND end_date="{end_date}" AND roster_type='Basic' 
			AND docstatus=1 AND status='Active'
		""", as_dict=1)
		shift_assignments_dict = {}
		shift_assignments_list = [i.name for i in shift_assignments]

		for row in shift_assignments:
			shift_assignments_dict[row.name] = row
			if row.employee in employees:
				if employees_dict.get(row.employee):
					employees_dict[row.employee]['shift_assignments'].append(row)
				else:
					employees_dict[row.employee] = {'shift_assignments':[row]}

		shift_assignments_tuple = str(tuple(shift_assignments_list)) #[:-2]+')'

		# Get checkins and make hashmap
		in_checkins = frappe.get_list("Employee Checkin", filters={"shift_assignment": ["IN", shift_assignments_list], 'log_type': 'IN'}, fields="*",
			order_by="creation ASC", group_by="shift_assignment")
		out_checkins = frappe.get_list("Employee Checkin", filters={"shift_assignment": ["IN", shift_assignments_list], 'log_type': 'OUT'}, fields="*",
			order_by="creation DESC", group_by="shift_assignment")

		in_checkins_dict = {}
		for i in in_checkins:
			in_checkins_dict[i.shift_assignment] = i

		out_checkins_dict = {}
		for i in out_checkins:
			out_checkins_dict[i.shift_assignment] = i
		

		# create attendance object
		employee_checkin = []
		employee_attendance = {}
		checkin_no_out = []
		for k, v in in_checkins_dict.items():
			try:
				emp = employees_data.get(v.employee)
				if attendance_dict.get(v.employee):
					name = attendance_dict.get(v.employee).name
				else:
					name = f"HR-ATT-{start_date}-{v.employee}"
				shift_type = shift_types_dict.get(v.shift_type)
				shift_assignment = shift_assignments_dict.get(v.shift_assignment)
				in_time = v.actual_time

				# check if late entry > 4hrs
				if ((in_time - shift_assignment.start_datetime).total_seconds() / (60*60)) > 4:
					working_hours = 0
					employee_attendance[i.employee] = frappe._dict({
						'name':f"HR-ATT-{start_date}-{i.employee}", 'employee':i.employee, 'employee_name':emp.employee_name, 'working_hours':0, 'status':'Absent',
						'shift':i.shift_type, 'in_time':'00:00:00', 'out_time':'00:00:00', 'shift_assignment':v.shift_assignment, 'operations_shift':v.operations_shift,
						'site':i.site, 'project':i.project, 'attendance_date': start_date, 'company':emp.company,
						'department': emp.department, 'late_entry':0, 'early_exit':0, 'operations_role':i.operations_role, 'post_abbrv':i.post_abbrv,
						'roster_type':i.roster_type, 'docstatus':1, 'owner':owner, 'modified_by':owner, 'creation':creation, 'modified':creation, "comment":f"Checked in 4hrs late at {in_time}"
					})
				# check if checkout exists
				elif out_checkins_dict.get(k):
					check_out = out_checkins_dict.get(k)
					out_time = check_out.time
					working_hours = (out_time - in_time).total_seconds() / (60 * 60)
					employee_checkin.append({name:{'in':v.name, 'out':check_out.name}}) # add checkin for update
					employee_attendance[v.employee] = frappe._dict({
						'name':name, 'employee':v.employee, 'employee_name':emp.employee_name, 'working_hours':working_hours, 'status':'Present',
						'shift':v.shift_type, 'in_time':in_time, 'out_time':out_time, 'shift_assignment':v.shift_assignment, 'operations_shift':v.operations_shift,
						'site':shift_assignment.site, 'project':shift_assignment.project, 'attendance_date': start_date, 'company':shift_assignment.company,
						'department': emp.department, 'late_entry':v.late_entry, 'early_exit':check_out.early_exit, 'operations_role':shift_assignment.operations_role,
						'post_abbrv':shift_assignment.post_abbrv,
						'roster_type':shift_assignment.roster_type, 'docstatus':1, 'owner':owner, 'modified_by':owner, 'creation':creation, 'modified':creation, 'comment':""
					})
				else: # no checkout record found
					working_hours = (shift_assignment.end_datetime - in_time).total_seconds() / (60 * 60)
					employee_checkin.append({name:{'in':v.name, 'out':v.name}}) # add checkin for update
					employee_attendance[v.employee] = frappe._dict({
						'name':name, 'employee':v.employee, 'employee_name':emp.employee_name, 'working_hours':working_hours, 'status':'Present',
						'shift':v.shift_type, 'in_time':in_time, 'out_time':shift_assignment.end_datetime, 'shift_assignment':v.shift_assignment, 'operations_shift':v.operations_shift,
						'site':shift_assignment.site, 'project':shift_assignment.project, 'attendance_date': start_date, 'company':shift_assignment.company,
						'department': emp.department, 'late_entry':v.late_entry, 'early_exit':check_out.early_exit, 'operations_role':shift_assignment.operations_role,
						'post_abbrv':shift_assignment.post_abbrv,
						'roster_type':shift_assignment.roster_type, 'docstatus':1, 'owner':owner, 'modified_by':owner, 'creation':creation, 'modified':creation, 'comment':"Checkin but no checkout record found"
					})
					# add employee to no checkout record found
					checkin_no_out.append({'employee':v.employee, 'in':v.name, 'shift_assignment':v.shift_assignment})
			except Exception as e:
				errors.append(str(e))
		# add absent, day off and holiday in shift assignment
		for i in shift_assignments:
			try:
				if not employee_attendance.get(i.employee):
					# check for day off
					if employee_schedule_dict.get(i.employee):
						availability = 'Day Off'
					elif holiday_today and holiday_today.get(employees_data[i.employee].holiday_list):
						availability = 'Holiday'
					else:
						availability = 'Absent'

					emp = employees_data.get(i.employee)
					if not emp:
						emp = frappe._dict({'department': '', 'employee_name': ''})
					employee_attendance[i.employee] = frappe._dict({
						'name':f"HR-ATT-{start_date}-{i.employee}", 'employee':i.employee, 'employee_name':emp.employee_name, 'working_hours':0, 'status':availability,
						'shift':i.shift_type, 'in_time':'00:00:00', 'out_time':'00:00:00', 'shift_assignment':i.name, 'operations_shift':i.shift,
						'site':i.site, 'project':i.project, 'attendance_date': start_date, 'company':i.company,
						'department': emp.department, 'late_entry':0, 'early_exit':0, 'operations_role':i.operations_role, 'post_abbrv':i.post_abbrv,
						'roster_type':i.roster_type, 'docstatus':1, 'owner':owner, 'modified_by':owner, 'creation':creation, 'modified':creation, 'comment':""
					})
			except Exception as e:
				errors.append(str(e))

		# mark day off if non above is met
		for i in employee_schedules:
			try:
				if not employee_attendance.get(i.employee):
					emp = employees_data.get(i.employee)
					employee_attendance[i.employee] = frappe._dict({
						'name':f"HR-ATT-{start_date}-{i.employee}", 'employee':i.employee, 'employee_name':emp.employee_name, 'working_hours':0, 'status':'Day Off',
						'shift':i.shift_type, 'in_time':'00:00:00', 'out_time':'00:00:00', 'shift_assignment':'', 'operations_shift':i.shift,
						'site':i.site, 'project':i.project, 'attendance_date': start_date, 'company':emp.company,
						'department': emp.department, 'late_entry':0, 'early_exit':0, 'operations_role':i.operations_role, 'post_abbrv':i.post_abbrv,
						'roster_type':i.roster_type, 'docstatus':1, 'owner':owner, 'modified_by':owner, 'creation':creation, 'modified':creation, 'comment':f"Employee Schedule - {i.name}"
					})
			except Exception as e:
				errors.append(str(e))
				
		
		# create attendance with sql injection
		if employee_attendance:
			query = """
				INSERT INTO `tabAttendance` (`name`, `employee`, `employee_name`, `working_hours`, `status`, `shift`, `in_time`, `out_time`,
				`shift_assignment`, `operations_shift`, `site`, `project`, `attendance_date`, `company`, 
				`department`, `late_entry`, `early_exit`, `operations_role`, `post_abbrv`, `roster_type`, `docstatus`, `modified_by`, `owner`,
				`creation`, `modified`, `comment`)
				VALUES 

			"""

			for k, v in employee_attendance.items():
				if not present_attendance_dict.get(v.employee):
					query+= f"""
					(
						"{v.name}", "{v.employee}", "{v.employee_name}", {v.working_hours}, "{v.status}", '{v.shift}', '{v.in_time}',
						'{v.out_time}', "{v.shift_assignment}", "{v.operations_shift}", "{v.site}", "{v.project}", "{v.attendance_date}", "{v.company}", 
						"{v.department}", {v.late_entry}, {v.early_exit}, "{v.operations_role}", "{v.post_abbrv}", "{v.roster_type}", {v.docstatus}, "{v.owner}",
						"{v.owner}", "{v.creation}", "{v.modified}", "{v.comment}"
					),"""
			
			query = query[:-1]
			query += f"""
					ON DUPLICATE KEY UPDATE
					employee = VALUES(employee),
					employee_name = VALUES(employee_name),
					working_hours = VALUES(working_hours),
					status = VALUES(status),
					shift = VALUES(shift),
					in_time = VALUES(in_time),
					out_time = VALUES(out_time),
					shift_assignment = VALUES(shift_assignment),
					operations_shift = VALUES(operations_shift),
					site = VALUES(site),
					project = VALUES(project),
					attendance_date = VALUES(attendance_date),
					company = VALUES(company),
					department = VALUES(department),
					late_entry = VALUES(late_entry),
					early_exit = VALUES(early_exit),
					operations_role = VALUES(operations_role),
					roster_type = VALUES(roster_type),
					docstatus = VALUES(docstatus),
					modified_by = VALUES(modified_by),
					modified = VALUES(modified)
				"""
			try:
				frappe.db.sql(query, values=[], as_dict=1)
				frappe.db.commit()
				# update checkin links
				if employee_checkin:
					query = """
						INSERT INTO `tabEmployee Checkin`
						(`name`, `attendance`)
						VALUES 
						
					"""
					for i in employee_checkin:
						k = list(i.keys())[0]
						v = i[k]
						query += f"""
							("{v['in']}", "{k}"),
							("{v['out']}", "{k}"),"""

					query = query[:-1]
					query += f"""
						ON DUPLICATE KEY UPDATE
						attendance = VALUES(attendance)
					"""
					frappe.db.sql(query, values=[], as_dict=1)
					frappe.db.commit()
			except Exception as e:
				errors.append(str(e))

		# check for error
		if len(errors):
			frappe.log_error(str(errors), "Mark Attendance")
		if len(checkin_no_out):
			# report no checkout
			frappe.get_doc({
				"doctype": "Issue",
				"naming_series": "ISS-.YYYY.-",
				"communication_medium": "Email",
				"status": "Open",
				"agreement_status": "First Response Due",
				"opening_date": "2023-01-23",
				"company": "One Facilities Management",
				"via_customer_portal": 0,
				"description": f"<div class=\"ql-editor read-mode\"><p>{str(checkin_no_out)}</p></div>",
				"subject": f"Attendance Issue (in no out) - {str(start_date)}",
				"priority": "Medium",
				"department": "IT - ONEFM",
				"issue_type": "Idea/Feedback",
				"raised_by": "e.anthony@one-fm.com"
			})
			frappe.log_error(str(errors), "Mark Attendance")
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), 'Mark Attendance')


def get_holiday_today(curr_date):
	start_date = getdate(curr_date).replace(day=1, month=1)
	end_date = getdate(start_date).replace(day=31, month=12)

	holidays = frappe.db.sql(f"""
		SELECT h.parent as holiday, h.holiday_date, h.description FROM `tabHoliday` h
		JOIN `tabHoliday List` hl ON hl.name=h.parent 
		WHERE from_date='{start_date}' AND to_date='{end_date}' AND h.holiday_date= '{curr_date}' """, as_dict=1)

	holiday_dict = {}
	for i in holidays:
		if(holiday_dict.get(i.holiday)):
			holiday_dict[i.holiday] = {**holiday_dict[i.holiday], **{i.holiday_date:i.description}}
		else:
			holiday_dict[i.holiday] = {i.holiday_date:i.description}
	
	return holiday_dict