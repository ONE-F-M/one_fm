import itertools
from datetime import timedelta
from string import Template
from calendar import month
from datetime import timedelta

import frappe, erpnext
from frappe import _
from frappe.utils import now_datetime, cstr, getdate, get_datetime, cint, add_to_date, datetime, today
from one_fm.api.doc_events import get_employee_user_id
from erpnext.payroll.doctype.payroll_entry.payroll_entry import get_end_date
from one_fm.api.doc_methods.payroll_entry import create_payroll_entry

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
				AND tSA.start_date="{date}" 
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
		if strfdelta(shift.start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.notification_reminder_after_shift_start))).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.user_id FROM `tabShift Assignment` tSA, `tabEmployee` emp
				WHERE
			  		tSA.employee=emp.name 
				AND tSA.start_date="{date}"
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
		
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.user_id FROM `tabShift Assignment` tSA, `tabEmployee` emp  
				WHERE
			  		tSA.employee = emp.name 
				AND tSA.start_date="{date}" 
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
	
				subject = _("Final Reminder: Please checkout in the next five minutes.")
				message = _("""<a class="btn btn-danger" href="/desk#face-recognition">Check Out</a>""")
				send_notification(subject, message, recipients)

def insert_Contact():
	Us = frappe.db.get_list('Employee', ["user_id","cell_number"])
	for i in Us:
		if frappe.db.exists("User", i.user_id):			
			uid = i.user_id
			mob = i.cell_number
			if len(str(mob))==8:
				new_Mob= int(str("965") + str(mob))
				frappe.db.set_value('User', {"email":uid}, 'mobile_no', new_Mob)
				print(new_Mob)
			elif len(str(mob))==10:
				new_Mob= int(str("91") + str(mob))
				frappe.db.set_value('User', {"email":uid}, 'mobile_no', new_Mob)
				print(new_Mob)
			else:
				print("Not valid")

		
def supervisor_reminder():
	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	today_datetime = today()	
	shifts_list = get_active_shifts(now_time)

	for shift in shifts_list:
		t = shift.supervisor_reminder_shift_start
		b = strfdelta(shift.start_time, '%H:%M:%S')
		
		#Send notification to supervisor of those who haven't checked in
		if strfdelta(shift.start_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.supervisor_reminder_shift_start))).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			print(date)
			checkin_time = today_datetime + " " + strfdelta(shift.start_time, '%H:%M:%S')
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.name, emp.employee_id, emp.employee_name, emp.reports_to, tSA.shift FROM `tabShift Assignment` tSA, `tabEmployee` emp
				WHERE
			  		tSA.employee=emp.name 
				AND tSA.start_date="{date}"
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

			if len(recipients) > 0:
				for recipient in recipients:
					op_shift =  frappe.get_doc("Operations Shift", recipient.shift)
					for_user = get_notification_user(op_shift) if get_notification_user(op_shift) else get_employee_user_id(recipient.reports_to)	
					if for_user is not None:
						subject = _("Checkin Report: {employee} has not checked in yet.".format(employee=recipient.employee_name))
						message = _("""
						<a class="btn btn-success checkin" id='{employee}_{time}'>Approve</a>
						<br><br><div class='btn btn-primary btn-danger no-punch-in' id='{employee}_{date}_{shift}'>Issue Penalty</div>
						""").format(shift=recipient.shift, date=cstr(now_time), employee=recipient.name, time=checkin_time)
						send_notification(subject, message, [for_user])

		#Send notification to supervisor of those who haven't checked out
		if strfdelta(shift.end_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.supervisor_reminder_start_ends))).time()):
		 	date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
		 	checkin_time = today_datetime + " " + strfdelta(shift.end_time, '%H:%M:%S')
		 	recipients = frappe.db.sql("""
		 		SELECT DISTINCT emp.employee_name, emp.reports_to, tSA.shift FROM `tabShift Assignment` tSA, `tabEmployee` emp
		 		WHERE
		 	  		tSA.employee=emp.name 
		 		AND tSA.start_date="{date}"
		 		AND tSA.shift_type="{shift_type}" 
		 		AND tSA.docstatus=1
				AND tSA.employee 
		 		NOT IN(SELECT employee FROM `tabEmployee Checkin` empChkin 
		 			WHERE
		 				empChkin.log_type="OUT"
		 				AND empChkin.skip_auto_attendance=0
		 				AND date(empChkin.time)="{date}"
		 				AND empChkin.shift_type="{shift_type}")
		 	""".format(date=cstr(date), shift_type=shift.name), as_dict=1)

		 	if len(recipients) > 0:
		 		for recipient in recipients:
		 			op_shift =  frappe.get_doc("Operations Shift", recipient.shift)
		 			for_user = get_notification_user(op_shift) if get_notification_user(op_shift) else get_employee_user_id(recipient.reports_to)	
		 			if for_user is not None:
						 subject = _("Checkin Report: {employee} has not checked in yet.".format(employee=recipient.employee_name))
						 message = _("""
						 <a class="btn btn-success checkin" id='{employee}_{time}'>Approve</a>
						 <br><br><div class='btn btn-primary btn-danger no-punch-in' id='{employee}_{date}_{shift}'>Issue Penalty</div>
						 """).format(shift=recipient.shift, date=cstr(now_time), employee=recipient.name, time=checkout_time)
						 send_notification(subject, message, [for_user])

					
def send_notification(subject, message, recipients):
	for user in recipients:
		notification = frappe.new_doc("Notification Log")
		notification.subject = subject
		notification.email_content = message
		notification.document_type = "Notification Log"
		notification.for_user = user
		notification.document_name = " "
		notification.save()
		notification.document_name = notification.name
		notification.save()
		frappe.db.commit()	

def get_active_shifts(now_time):
	return frappe.db.sql("""
		SELECT 
			name, start_time, end_time, 
			notification_reminder_after_shift_start, late_entry_grace_period, 
			notification_reminder_after_shift_end, allow_check_out_after_shift_end_time,
			supervisor_reminder_shift_start, supervisor_reminder_start_ends
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
			if supervisor != operations_shift.owner:
				return supervisor
		
		operations_site = frappe.get_doc("Operations Site", operations_shift.site)
		if operations_site.account_supervisor:
			account_supervisor = get_employee_user_id(operations_site.account_supervisor)
			if account_supervisor != operations_shift.owner:
				return account_supervisor

		if operations_site.project:
			project = frappe.get_doc("Project", operations_site.project)
			if project.account_manager:
				account_manager = get_employee_user_id(project.account_manager)
				if account_manager != operations_shift.owner:
					return account_manager

def automatic_checkout():
	now_time = now_datetime().strftime("%Y-%m-%d %H:%M")
	shifts_list = get_active_shifts(now_time)
	for shift in shifts_list:
		# shift_end is equal to now time - notification reminder in mins
		#print(shift.name, strfdelta(shift.end_time, '%H:%M:%S') , cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.allow_check_out_after_shift_end_time))).time()))
		if strfdelta(shift.end_time, '%H:%M:%S') == cstr((get_datetime(now_time) - timedelta(minutes=cint(shift.allow_check_out_after_shift_end_time))).time()):
			date = getdate() if shift.start_time < shift.end_time else (getdate() - timedelta(days=1))
			# print(shift.name, now_time, shift.end_time)
		
			recipients = frappe.db.sql("""
				SELECT DISTINCT emp.name FROM `tabShift Assignment` tSA, `tabEmployee` emp  
				WHERE
					tSA.employee = emp.name 
				AND tSA.start_date="{date}" 
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
	end_previous_shifts()
	roster = frappe.get_all("Employee Schedule", {"date": date, "employee_availability": "Working" }, ["*"])
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
	shift_assignment.submit()


def update_shift_type():
	today_datetime = now_datetime()	
	now_time = today_datetime.strftime("%H:%M")
	shift_types = frappe.get_all("Shift Type", {"end_time": now_time},["name", "allow_check_out_after_shift_end_time"])
	for shift_type in shift_types:
		last_sync_of_checkin = add_to_date(today_datetime, minutes=cint(shift_type.allow_check_out_after_shift_end_time)+15, as_datetime=True)
		doc = frappe.get_doc("Shift Type", shift_type.name)
		doc.last_sync_of_checkin = last_sync_of_checkin
		doc.submit()


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
		site, project, shift, post_type, post_abbrv = frappe.get_value("Shift Assignment", {"employee": doc.employee, "start_date": doc.attendance_date}, ["site", "project", "shift", "post_type", "post_abbrv"])
		frappe.db.sql("""update `tabAttendance`
			set project = %s, site = %s, operations_shift = %s, post_type = %s, post_abbrv = %s 
			where name = %s """, (project, site, shift, post_type, post_abbrv, doc.name))

def generate_payroll():
	start_date = add_to_date(getdate(), months=-1)
	end_date = get_end_date(start_date, 'monthly')['end_date']
	
	# Hardcoded dates for testing, remove below 2 lines for live
	#start_date = "2021-02-24"
	#end_date = "2021-03-23"

	try:
			create_payroll_entry(start_date, end_date)
	except Exception:
			print(frappe.get_traceback())
			frappe.log_error(frappe.get_traceback())

"""
	departments = frappe.get_all("Department", {"company": erpnext.get_default_company()})
	for department in departments:
		try:
			# If condition for testing. 
			if department.name != "IT - ONEFM":
				create_payroll_entry(department.name, start_date, end_date)
		except Exception:
			print(frappe.get_traceback())
			frappe.log_error(frappe.get_traceback())
"""


def generate_penalties():
	print("HEllo")
	start_date = add_to_date(getdate(), days=-30)
	end_date = get_end_date(start_date, 'monthly')['end_date']
	print (str(start_date) + str(end_date))

	filters = {
		'penalty_issuance_time': ['between', (start_date, end_date)],
		'workflow_state': 'Penalty Accepted'
	}
	logs = frappe.db.get_list('Penalty', filters=filters, fields="*", order_by="recipient_employee,penalty_issuance_time")
	print(logs)
	for key, group in itertools.groupby(logs, key=lambda x: (x['recipient_employee'])):
		employee_penalties = list(group)
		calculate_penalty_amount(key, start_date, end_date, employee_penalties)



def calculate_penalty_amount(employee, start_date, end_date, logs):
	filters = {
		'docstatus': 1,
		'employee': employee
	}
	salary_structure = frappe.get_value("Salary Structure Assignment", filters, "salary_structure", order_by="from_date desc")
	basic_salary = frappe.db.sql("""
		SELECT amount FROM `tabSalary Detail`
		WHERE parenttype="Salary Structure" 
		AND parent=%s 
		AND salary_component="Basic"
	""",(salary_structure), as_dict=1)
	print(basic_salary)
	
	#Single day salary of employee = Basic Salary(WP salary) divided by 26 days
	single_day_salary = basic_salary[0].amount / 26 

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
	# print(damages_amount)

	days_deduction = frappe.db.sql("""
		SELECT sum(pd.deduction) as days_deduction, pd.name 
		FROM `tabPenalty Issuance Details` as pd
		WHERE
			pd.parenttype="Penalty"
		AND pd.parent in ({refs})
	""".format(refs=references), as_dict=1)

	# Days deduction
	print("Deduction:" + str(days_deduction))
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