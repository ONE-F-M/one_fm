from datetime import timedelta
import frappe
from frappe import _
from frappe.utils import now_datetime, cstr, getdate, get_datetime, nowdate, cint
import schedule, time
from one_fm.operations.doctype.operations_site.operations_site import create_notification_log
from datetime import timedelta, datetime
from string import Template
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
			recipients = [recipient[0] for recipient in recipients]

			subject = _("Hourly Reminder: Please checkin")
			message = _('<a class="btn btn-warning" href="/desk#face-recognition">Hourly Check In</a>')
			send_notification(subject, message, recipients)


def final_reminder():
	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	shifts_list = get_active_shifts(now_time)
	for shift in shifts_list:
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
			recipients = [recipient[0] for recipient in recipients]
			subject = _("Final Reminder: Please checkin in the next five minutes.")
			message = _('<a class="btn btn-success" href="/desk#face-recognition">Check In</a>&nbsp;<a class="btn btn-primary btn-info" href="/desk#Form/Shift%20Permission/New%20Shift%20Permission%201">Planning to arrive late?</a>')
			send_notification(subject, message, recipients)

		if strfdelta(shift.end_time, '%H:%M:%S') == cstr((get_datetime(now_time)- timedelta(minutes=cint(shift.notification_reminder_after_shift_end))).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			
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
			recipients = [recipient[0] for recipient in recipients]

			subject = _("Final Reminder: Please checkout in the next five minutes.")
			message = _('<a class="btn btn-success" href="/desk#face-recognition">Check Out</a>')
			send_notification(subject, message, recipients)
		
def supervisor_reminder():
	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	shifts_list = get_active_shifts(now_time)
	for shift in shifts_list:
		if strfdelta(shift.start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.late_entry_grace_period))).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.employee_name, tSA.shift FROM `tabShift Assignment` tSA, `tabEmployee` emp
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
			supervisor = frappe.get_value("Operations Shift", recipients[0].shift, "supervisor")
			for_user = frappe.get_value("Employee", supervisor, "user_id")
			recipients = [recipient.employee_name for recipient in recipients]			
			subject = _("Checkin Report: List of employees who have not checked in yet.")
			names =  '\n'.join(['{}'.format(name) for name in recipients])
			message = _(names)
			send_notification(subject, message, [for_user])


def send_notification(subject, message, recipients):
	for user in recipients:
		notification = frappe.new_doc("Notification Log")
		notification.subject = subject
		notification.email_content = message
		notification.document_type = "Notification Log"
		notification.for_user = user
		notification.save()
		notification.document_name = notification.name
		notification.save()
		

def get_active_shifts(now_time):
	return frappe.db.sql("""
		SELECT 
			name, start_time, end_time, notification_reminder_after_shift_start, late_entry_grace_period
		FROM `tabShift Type`
		WHERE 
			CAST("{current_time}" as datetime) 
			BETWEEN
				CAST(start_time as datetime) 
			AND 
				IF(end_time < start_time, DATE_ADD(CAST(end_time as datetime), INTERVAL 1 DAY), CAST(end_time as datetime)) 
	""".format(current_time=now_time), as_dict=1)
