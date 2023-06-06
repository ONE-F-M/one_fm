# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import nowdate, add_to_date, cstr, add_days
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError, close_all_assignments

class AttendanceCheck(Document):
	def after_insert(self):
		self.assign_to_supervisor()

	def on_submit(self):
		self.validate_justification_and_attendance_status()
		close_all_assignments(self.doctype, self.name)
		self.mark_attendance()

	def mark_attendance(self):
		if self.workflow_state == 'Approved':
			attendance_exists = frappe.db.exists('Attendance',
				{'attendance_date': self.date, 'employee': self.employee, 'docstatus': ['<', 2]})
			if attendance_exists:
				att = frappe.get_doc("Attendance", attendance_exists)
				if att.status != self.attendance_status:
					att.db_set("status", self.attendance_status)
			else:
				att = frappe.new_doc("Attendance")
				att.employee = self.employee
				att.employee_name = self.employee_name
				att.attendance_date = self.date
				att.status = self.attendance_status
				att.working_hours = 8 if self.attendance_status == 'Present' else 0
				att.insert(ignore_permissions=True)
				att.submit()

	def validate_justification_and_attendance_status(self):
		if self.workflow_state in ['Approved', 'Rejected']:
			message = 'Justification' if not self.justification else False
			if not self.attendance_status:
				message = message + ' and Attendance Status' if message else 'Attendance Status'
			if message:
				frappe.throw(_('To Approve or Reject the Record set {0}'.format(message)))

	def assign_to_supervisor(self):
		try:
			users = []
			if self.reports_to:
				users.append(self.reports_to_user)
			if self.shift_supervisor_user:
				users.append(self.shift_supervisor_user)
			if self.site_supervisor_user:
				users.append(self.site_supervisor_user)
			description = f"""
				<p>Here is to inform you that the following {self.doctype}({self.name}) requires your attention/action.
				<br>
				The details of the request are as follows:<br>
				</p>
				<table border="1" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
					<thead>
						<tr>
							<th style="padding: 10px; text-align: left; background-color: #f2f2f2;">Label</th>
							<th style="padding: 10px; text-align: left; background-color: #f2f2f2;">Value</th>
						</tr>
					</thead>
					<tbody>
						<tr>
							<td style="padding: 10px;">Employee</td>
							<td style="padding: 10px;">{self.employee} - {self.employee_name}</td>
						</tr>
						<tr>
							<td style="padding: 10px;">Date</td>
							<td style="padding: 10px;">{self.date}</td>
						</tr>
						<tr>
							<td style="padding: 10px;">Department</td>
							<td style="padding: 10px;">{self.department}</td>
						</tr>
					</tbody>
				</table>
			"""
			add_assignment({
				'doctype': self.doctype,
				'name': self.name,
				'assign_to': users,
				'description': description,
			})
		except DuplicateToDoError:
			frappe.message_log.pop()
			pass

@frappe.whitelist()
def create_attendance_check(date = None):
    # Date is in "YYYY-MM-DD" format
	date = add_to_date(nowdate(), days=-1) if not date else add_to_date(date)
	data = fetch_data(date)

	for employee in data:
		doc = frappe.new_doc("Attendance Check")
		doc.employee = employee
		doc.date = date
		supervisor = get_supervisor(employee)
		if supervisor:
			if supervisor['shift_supervisor']:
				doc.shift_supervisor = supervisor['shift_supervisor']
			if supervisor['site_supervisor']:
				doc.site_supervisor = supervisor['site_supervisor']

		if data[employee]['shift_assignment'] == 0 and not has_day_off(employee, date):
			doc.has_shift_assignment = 1
			doc.shift_assignment = frappe.get_doc("Shift Assignment", {'employee': employee, 'start_date':date})

		if data[employee]['checkin'] == 0:
			doc.has_checkin_record = 1
			emp_checkin = frappe.db.sql("""SELECT name, log_type FROM `tabEmployee Checkin` empChkin
							WHERE
							date(empChkin.time)='{date}'
							AND employee = '{employee}'""".format(date=cstr(date), employee=employee), as_dict=1)
			for checkin in emp_checkin:
				if checkin.log_type == "IN":
					doc.checkin_record = frappe.get_doc("Employee Checkin", checkin.name)
				if checkin.log_type == "OUT":
					doc.checkout_record = frappe.get_doc("Employee Checkin", checkin.name)
		if data[employee]['attendance'] == 0 and not has_day_off(employee, date):
			doc.has_the_attendance_for_the_marked = 1
			doc.attendance =  frappe.get_value("Attendance", {'employee': employee, 'attendance_date':date}, ['name'])

		if frappe.db.exists("Shift Permission", {'employee': employee, 'date':date}):
			doc.has_shift_pemission = 1
			doc.shift_permission = frappe.get_value("Shift Permission", {'employee': employee, 'date':date}, ['name'])

		if frappe.db.exists("Attendance Request", {'employee': employee, 'date':date}):
			doc.has_attendance_request = 1
			doc.attendance_request = frappe.get_value("Attendance Request", {'employee': employee, 'date':date}, ['name'])

		doc.insert()
	frappe.db.commit()

def fetch_data(date):
	active_employee = frappe.get_list("Employee", {"status":"Active"},['name'])

	active_employee = [emp.name for emp in active_employee]
	no_shift_assignment = fetch_no_shift_assignment(date, active_employee)
	no_checkin = fetch_no_checkin_record(date, active_employee)
	no_attendance = fetch_no_attendance(date, active_employee)

	data = {}
	processed_values = set()

	for value in no_shift_assignment + no_checkin + no_attendance:  # Merge all lists and create a set of unique values
		if value not in processed_values:
			data[value] = {
				'shift_assignment': int(value in no_shift_assignment),
				'checkin': int(value in no_checkin),
				'attendance': int(value in no_attendance)
			}
			processed_values.add(value)

	return data

def get_supervisor(employee):
	shifts = frappe.get_list("Employee", {'name':employee}, ['shift', 'default_shift'])

	shift = shifts[0].shift if shifts[0].shift != "" else shifts[0].default_shift if shifts[0].default_shift!="" else ""
	if shift != "":
		shift_doc = frappe.get_list("Operations Shift", {"name":shift}, ['site','supervisor'])
		shift_supervisor = shift_doc[0].supervisor
		site_supervisor = frappe.get_value("Operations Site", {"name":shift_doc[0].site}, ['account_supervisor'])
		return {'shift_supervisor':shift_supervisor, 'site_supervisor':site_supervisor}
	else:
		return

def fetch_no_shift_assignment(date, employees):
	shift_assignment = get_assigned_shift(date)
	day_off = get_days_off(date)
	sa = shift_assignment + day_off

	no_sa = [e for e in employees if e not in sa]
	return no_sa

def get_assigned_shift(date):
	shift_assignment = frappe.get_list("Shift Assignment", {'start_date':date}, ['employee'])
	shift_assignment = [emp.employee for emp in shift_assignment]
	return shift_assignment

def get_days_off(date):
	day_off_emp_se = frappe.get_list("Employee Schedule", {'date':date, 'employee_availability':'Day Off'}, ['employee'])
	day_off_emp_se = [emp.employee for emp in day_off_emp_se]
	day_off_emp_nse = frappe.db.sql("""SELECT name as employee, holiday_list from `tabEmployee` E
				WHERE E.shift_working = 0 AND E.status='Active' AND E.attendance_by_timesheet != 1
				AND EXISTS(SELECT * from `tabHoliday` h
					WHERE
						h.parent = E.holiday_list
					AND h.holiday_date = '{date}')
					""".format(date=date), as_dict=1)
	day_off_emp_nse = [emp.employee for emp in day_off_emp_nse]
	day_off = day_off_emp_se + day_off_emp_nse
	return day_off

def has_day_off(employee, date):
	day_off_employees = get_days_off(date)
	if employee in day_off_employees:
		return True
	else:
		return False

def fetch_no_checkin_record(date, employees):
	shift_assignment = get_assigned_shift(date)
	checkin_employee = get_checkin(date)

	no_checkin = [e for e in employees if e not in shift_assignment and e not in checkin_employee]
	return no_checkin

def get_checkin(date):
	checkin = frappe.db.sql("""SELECT DISTINCT employee FROM `tabEmployee Checkin` empChkin
							WHERE
							date(empChkin.time)='{date}'""".format(date=cstr(date)), as_dict=1)
	checkin = [emp.employee for emp in checkin]
	return checkin

def fetch_no_attendance(date, employees):
	shift_assignment =  get_assigned_shift(date)
	attendance = frappe.db.sql("""SELECT employee FROM `tabAttendance`
							WHERE attendance_date='{date}'
							AND employee in {employees}""".format(date=cstr(date), employees=tuple(employees)), as_dict=1)
	attendance = [emp.employee for emp in attendance]

	no_attendance =  [e for e in employees if e not in shift_assignment and e not in attendance]
	return no_attendance

def assign_doc(doc):
	supervisor = doc.reports_to if doc.reports_to else doc.shift_supervisor if doc.shift_supervisor else doc.site_supervisor
	supervisor_user_id = frappe.db.get_value("Employee", {"name": supervisor}, ["user_id"], as_dict=1)
	if supervisor_user_id:
		doc.assign_to = supervisor_user_id.user_id
	doc.submit()
	frappe.db.commit()

def approve_attendance_check():
	date_before_24_hours = add_days(nowdate(), -1)
	attendance_check_list = frappe.get_list("Attendance Check", {"workflow_state": "Pending Approval", "date": ['<=', date_before_24_hours]}, ['name'])
	if len(attendance_check_list) <= 10:
		auto_approve_attendance_check(attendance_check_list)
	else:
		frappe.enqueue(method=auto_approve_attendance_check, attendance_check_list=attendance_check_list, queue='long', timeout=1200, job_name='Approve Attendance Check')

def auto_approve_attendance_check(attendance_check_list):
	for attendance_check in attendance_check_list:
		try:
			doc = frappe.get_doc("Attendance Check", attendance_check.name)
			doc.workflow_state = "Approved"
			doc.attendance_status = "Present"
			doc.justification = "No valid reason"
			doc.flags.ignore_validate = True
			doc.submit()
			doc.add_comment(comment_type="Info", text="Auto Approved on {0}".format(nowdate()))
		except:
			frappe.log_error("Error while auto approve attendance check {0}".format(attendance_check.name))
			continue
	frappe.db.commit()
