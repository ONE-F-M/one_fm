from datetime import timedelta
import frappe
from frappe import _
from frappe.utils import now_datetime, cstr, getdate, get_datetime, nowdate, cint, add_to_date
import schedule, time
from one_fm.operations.doctype.operations_site.operations_site import create_notification_log
from datetime import timedelta, datetime
from string import Template
from one_fm.api.doc_events import get_employee_user_id
import itertools

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

	#Send notifications to employees assigned to a shift for hourly checkin
	for shift in shifts_list:
		if strfdelta(shift.start_time, '%H:%M:%S') != cstr(get_datetime(now_time).time()) and strfdelta(shift.end_time, '%H:%M:%S') != cstr(get_datetime(now_time).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.user_id FROM `tabShift Assignment` tSA, `tabEmployee` emp  
				WHERE
			  		tSA.employee = emp.name 
				AND tSA.date="{date}" 
				AND tSA.shift_type="{shift_type}" 
				AND tSA.docstatus=1
			""".format(date=cstr(date), shift_type=shift.name), as_list=1)
			recipients = [recipient[0] for recipient in recipients if recipient[0]]
			print(recipients)
			subject = _("Hourly Reminder: Please checkin")
			message = _('<a class="btn btn-warning" href="/desk#face-recognition">Hourly Check In</a>')
			send_notification(subject, message, recipients)

def final_reminder():
	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	shifts_list = get_active_shifts(now_time)

	#Send final reminder to checkin or checkout to employees who have not even after shift has ended
	for shift in shifts_list:
		# shift_start is equal to now time - notification reminder in mins
		# print(shift.name, now_datetime(), now_time, shift.start_time)
		if strfdelta(shift.start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.notification_reminder_after_shift_start))).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.user_id FROM `tabShift Assignment` tSA, `tabEmployee` emp
				WHERE
			  		tSA.employee=emp.name 
				AND tSA.date="{date}"
				AND tSA.shift_type="{shift_type}" 
				AND tSA.docstatus=1
				AND tSA.employee 
				NOT IN(SELECT employee FROM `tabEmployee Checkin` empChkin 
				WHERE
					empChkin.log_type="IN"
				AND empChkin.skip_auto_attendance=0
				AND date(empChkin.time)="{date}"
				AND empChkin.shift_type="{shift_type}")
			""".format(date=cstr(date), shift_type=shift.name), as_list=1)
			print(recipients)

			if len(recipients) > 0:
				recipients = [recipient[0] for recipient in recipients if recipient[0]]
				subject = _("Final Reminder: Please checkin in the next five minutes.")
				message = _("""
					<a class="btn btn-success" href="/desk#face-recognition">Check In</a>&nbsp;
					<a class="btn btn-primary" href="/desk#Form/Shift%20Permission/New%20Shift%20Permission%201">Planning to arrive late?</a>&nbsp;
					""")
				send_notification(subject, message, recipients)

		# shift_end is equal to now time - notification reminder in mins
		if strfdelta(shift.end_time, '%H:%M:%S') == cstr((get_datetime(now_time)- timedelta(minutes=cint(shift.notification_reminder_after_shift_end))).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			print(shift.name, now_time, shift.end_time)
		
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.user_id FROM `tabShift Assignment` tSA, `tabEmployee` emp  
				WHERE
			  		tSA.employee = emp.name 
				AND tSA.date="{date}" 
				AND tSA.shift_type="{shift_type}" 
				AND tSA.docstatus=1
				AND tSA.employee 
				NOT IN(SELECT employee FROM `tabEmployee Checkin` empChkin 
				WHERE
					empChkin.log_type="OUT"
				AND empChkin.skip_auto_attendance=0
				AND date(empChkin.time)="{date}"
				AND empChkin.shift_type="{shift_type}")
			""".format(date=cstr(date), shift_type=shift.name), as_list=1)
			print(recipients)

			if len(recipients) > 0:	
				recipients = [recipient[0] for recipient in recipients if recipient[0]]
	
				subject = _("Final Reminder: Please checkout in the next five minutes.")
				message = _("""<a class="btn btn-danger" href="/desk#face-recognition">Check Out</a>""")
				send_notification(subject, message, recipients)
		
def supervisor_reminder():
	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	shifts_list = get_active_shifts(now_time)
	print("SUPERVISOR REMINDER", now_time, now_datetime())
	for shift in shifts_list:
		#Send notification to supervisor of those who haven't checked in
		if strfdelta(shift.start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.late_entry_grace_period))).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.name, emp.employee_id, emp.employee_name, emp.reports_to, tSA.shift FROM `tabShift Assignment` tSA, `tabEmployee` emp
				WHERE
			  		tSA.employee=emp.name 
				AND tSA.date="{date}"
				AND tSA.shift_type="{shift_type}" 
				AND tSA.docstatus=1
				AND tSA.employee 
				NOT IN(SELECT employee FROM `tabEmployee Checkin` empChkin 
					WHERE
						empChkin.log_type="IN"
						AND empChkin.skip_auto_attendance=0
						AND date(empChkin.time)="{date}"
						AND empChkin.shift_type="{shift_type}")
			""".format(date=cstr(date), shift_type=shift.name), as_dict=1)
			print("SUPERVISOR REMINDER", recipients)

			if len(recipients) > 0:
				for recipient in recipients:
					op_shift =  frappe.get_doc("Operations Shift", recipient.shift)
					for_user = get_notification_user(op_shift) if get_notification_user(op_shift) else get_employee_user_id(recipient.reports_to)	
					if for_user is not None:
						subject = _("Checkin Report: {employee} has not checked in yet.".format(employee=recipient.employee_name))
						message = _("{name} has not checked in yet. <br><br><div class='btn btn-primary btn-danger no-punch-in' id='{employee}_{date}_{shift}'>Issue Penalty</div>".format(name=recipient.employee_name, shift=recipient.shift, date=cstr(now_time), employee=recipient.name))
						send_notification(subject, message, [for_user])

		#Send notification to supervisor of those who haven't checked out
		# if strfdelta(shift.end_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.allow_check_out_after_shift_end_time))).time()):
		# 	date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			
		# 	recipients = frappe.db.sql("""
		# 		SELECT DISTINCT emp.employee_name, emp.reports_to, tSA.shift FROM `tabShift Assignment` tSA, `tabEmployee` emp
		# 		WHERE
		# 	  		tSA.employee=emp.name 
		# 		AND tSA.date="{date}"
		# 		AND tSA.shift_type="{shift_type}" 
		# 		AND tSA.docstatus=1
		# 		AND tSA.employee 
		# 		NOT IN(SELECT employee FROM `tabEmployee Checkin` empChkin 
		# 			WHERE
		# 				empChkin.log_type="OUT"
		# 				AND empChkin.skip_auto_attendance=0
		# 				AND date(empChkin.time)="{date}"
		# 				AND empChkin.shift_type="{shift_type}")
		# 	""".format(date=cstr(date), shift_type=shift.name), as_dict=1)

		# 	if len(recipients) > 0:
		# 		for recipient in recipients:
		# 			op_shift =  frappe.get_doc("Operations Shift", recipient.shift)
		# 			for_user = get_notification_user(op_shift) if get_notification_user(op_shift) else get_employee_user_id(recipient.reports_to)	
		# 			if for_user is not None:
		# 				subject = _("Checkin Report: {employee} has not checked out yet.".format(employee=recipient.employee_name))
		# 				message = _("{employee} has not checked out yet.".format(employee=recipient.employee_name))
		# 				send_notification(subject, message, [for_user])

def send_notification(subject, message, recipients):
	print("181", recipients)
	for user in recipients:
		notification = frappe.new_doc("Notification Log")
		notification.subject = subject
		notification.email_content = message
		notification.document_type = "Notification Log"
		notification.for_user = user
		notification.save()
		print("188" ,notification.as_dict())
		notification.document_name = notification.name
		notification.save()
		# print(notification.as_dict())
		frappe.db.commit()	

def get_active_shifts(now_time):
	return frappe.db.sql("""
		SELECT 
			name, start_time, end_time, 
			notification_reminder_after_shift_start, late_entry_grace_period, 
			notification_reminder_after_shift_end, allow_check_out_after_shift_end_time
		FROM `tabShift Type`
		WHERE 
			CAST("{current_time}" as date) 
			BETWEEN
				CAST(start_time as date) 
			AND 
				IF(end_time < start_time, DATE_ADD(CAST(end_time as date), INTERVAL 1 DAY), CAST(end_time as date)) 
	""".format(current_time=now_time), as_dict=1)

def get_notification_user(operations_shift):
		"""
				Shift > Site > Project > Reports to
		"""
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

def automatic_checkout():
	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	shifts_list = get_active_shifts(now_time)
	for shift in shifts_list:
		# shift_end is equal to now time - notification reminder in mins
		print(shift.name, strfdelta(shift.end_time, '%H:%M:%S') , cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.allow_check_out_after_shift_end_time))).time()))
		if strfdelta(shift.end_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.allow_check_out_after_shift_end_time))).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			# print(shift.name, now_time, shift.end_time)
		
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.name FROM `tabShift Assignment` tSA, `tabEmployee` emp  
				WHERE
					tSA.employee = emp.name 
				AND tSA.date="{date}" 
				AND tSA.shift_type="{shift_type}" 
				AND tSA.docstatus=1
				AND tSA.employee 
				NOT IN(SELECT employee FROM `tabEmployee Checkin` empChkin 
				WHERE
					empChkin.log_type="OUT"
				AND empChkin.skip_auto_attendance=0
				AND date(empChkin.time)="{date}"
				AND empChkin.shift_type="{shift_type}")
			""".format(date=cstr(date), shift_type=shift.name), as_list=1)
			if len(recipients) > 0:	
				recipients = [recipient[0] for recipient in recipients if recipient[0]]
				# print(recipients)
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
	penalty_issuance.penalty_location = penalty
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


def automatic_shift_assignment():
	date = cstr(getdate())
	roster = frappe.get_all("Employee Schedule", {"date": date, "employee_availability": "Working", "project": "Mighty Zinger"}, ["*"])
	for schedule in roster:
		create_shift_assignment(schedule, date)

def create_shift_assignment(schedule, date):
	shift_assignment = frappe.new_doc("Shift Assignment")
	shift_assignment.date = date
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
	shift_assignment.submit()



def update_shift_type():
	today_datetime = now_datetime()	
	now_time = today_datetime.strftime("%H:%M")
	shift_types = frappe.get_all("Shift Type", {"end_time": now_time},["name", "allow_check_out_after_shift_end_time"])
	for shift_type in shift_types:
		last_sync_of_checkin = add_to_date(today_datetime, minutes=cint(shift_type.allow_check_out_after_shift_end_time)+15, as_datetime=True)
		frappe.set_value("Shift Type", shift_type.name, "last_sync_of_checkin", last_sync_of_checkin)


def process_attendance():
	now_time = now_datetime().strftime("%H:%M")
	shift_types = frappe.get_all("Shift Type", {"last_sync_of_checkin": now_time})
	for shift_type in shift_types:
		frappe.enqueue(mark_auto_attendance, shift_type, worker='long')

def mark_auto_attendance(shift_type):
	doc = frappe.get_doc("Shift Type", shift_type.name)
	doc.process_auto_attendance()	


def update_shift_details_in_attendance(doc, method):
	if frappe.db.exists("Shift Assignment", {"employee": doc.employee, "date": doc.attendance_date}):
		site, project, shift, post_type, post_abbrv = frappe.get_value("Shift Assignment", {"employee": doc.employee, "date": doc.attendance_date}, ["site", "project", "shift", "post_type", "post_abbrv"])
		frappe.db.sql("""update `tabAttendance`
			set project = %s, site = %s, operations_shift = %s, post_type = %s, post_abbrv = %s 
			where name = %s """, (project, site, shift, post_type, post_abbrv, doc.name))


def create_attendance():
	emps = ["HR-EMP-00030", "HR-EMP-00035"]
	x = range(1, 30)
	for emp in emps:
		for n in x:
			if n not in [4,11,18,25]:
				date = getdate("2020-09-"+cstr(n))
				doc = frappe.new_doc("Attendance")
				doc.employee= emp
				doc.attendance_date = cstr(date)
				doc.working_hours = 11.2
				doc.status = "Post Off"
				doc.status = "Present"
				doc.post_abbrv = "GSG"
				doc.post_type = "Gate Security Guard"
				doc.site = "Cpven Ahmadi"
				doc.operations_shift = "Cpven Ahmadi-Day|6:00:00-18:00:00|12.0 hours"
				doc.project = "CPVEN"
				doc.insert()
				doc.submit()
	frappe.db.commit()

def timesheet_automation():
	start_date = '2020-09-01' # Replace date with dynamic date value
	end_date = '2020-09-30'  # Replace date with dynamic date value
	filters = {
		'attendance_date': ['between', (start_date, end_date)],
		'project': 'CPVEN', # Replace hardcoded value with project name
		'status': 'Present'
	}

	logs = frappe.db.get_list('Attendance', fields="employee,working_hours,attendance_date,operations_shift,project,post_type", filters=filters, order_by="employee,attendance_date")
	for key, group in itertools.groupby(logs, key=lambda x: (x['employee'])):
		attendances = list(group)
		timesheet = frappe.new_doc("Timesheet")
		timesheet.employee = key
			
		for attendance in attendances:
			date = cstr(attendance.attendance_date)
			#Get start time from first employee checkin of that day of log type IN
			start = frappe.get_list("Employee Checkin", {"employee": key, "time": ['between', (date, date)], "log_type": "IN"}, "time", order_by="time asc")[0].time
			#Get end time from last employee checkin of that day of log type OUT
			end = frappe.get_list("Employee Checkin", {"employee": key, "time": ['between', (date, date)], "log_type": "OUT"}, "time", order_by="time desc")[0].time

			# Added hardcoded for testing
			#start = date + ' 08:00:00'
			#end = date + ' 17:00:00'

			timesheet.append("time_logs", {
				"activity_type": attendance.post_type,
				"from_time": start,
				"to_time": end,
				"project": attendance.project,
				"hours": attendance.working_hours
			})
		timesheet.save()
	frappe.db.commit()	