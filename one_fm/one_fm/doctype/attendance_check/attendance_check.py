# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import nowdate, add_to_date, cstr, add_days, today

class AttendanceCheck(Document):
	def on_submit(self):
		self.validate_justification_and_attendance_status()
		self.mark_attendance()

	def mark_attendance(self):
		if self.workflow_state == 'Approved':
			if frappe.db.exists('Attendance',
				{'attendance_date': self.date, 'employee': self.employee, 'docstatus': ['<', 2],
				'roster_type':self.roster_type
				}):
				att = frappe.get_doc("Attendance", {
					'attendance_date': self.date, 'employee': self.employee, 
					'docstatus': ['<', 2],
					'roster_type':self.roster_type
				})
				if att.status != self.attendance_status:
					if self.shift_assignment and not att.shift_assignment:
						att.db_set("shift_assignment", self.shift_assignment)
					else:
						if att.shift_assignment:
							shift_assignment = frappe.get_doc("Shift Assignment", att.shift_assignment)
							att.db_set('shift_assignment', att.shift_assignment.name)
					att.reload()
					att.db_set("comment", f"Created from Attendance Check, \n{att.comment or ''}")
					att.db_set("status", self.attendance_status)
					att.db_set('reference_doctype', "Attendance Check")
					att.db_set('reference_docname', self.name)
					if not att.shift_assignment:
						if frappe.db.exists("Shift Assignment", {
								'employee':self.employee, 'start_date':self.date, 'roster_type':self.roster_type
							}):
							shift_assignment = frappe.get_doc("Shift Assignment", {
								'employee':self.employee, 'start_date':self.date, 'roster_type':self.roster_type
							})
							att.shift_Assignment = shift_assignment.name
						elif frappe.db.exists("Employee Schedule", {
								'employee':self.employee, 'date':self.date, 'roster_type':self.roster_type
							}):
							employee_schedule = frappe.get_doc("Employee Schedule", {
								'employee':self.employee, 'date':self.date, 'roster_type':self.roster_type
							})
							shift_assignment = frappe.get_doc({
								'doctype':"Shift Assignment",
								'employee':employee_schedule.employee,
								'shift_type':employee_schedule.shift_type,
								'start_date':employee_schedule.date,
								'status':'Active',
								'operations_role':employee_schedule.operations_role,
								'shift':employee_schedule.shift,
								'day_off_ot':employee_schedule.day_off_ot
							}).insert(ignore_permissions=1)
							shift_assignment.submit()
							self.db_set("shift_assignment", shift_assignment.name)
							self.db_set("has_shift_assignment", 1)
						att.db_set("shift_Assignment", shift_assignment.name)
						att.db_set('operations_role', shift_assignment.operations_role)
						att.db_set('operations_site', shift_assignment.site)
						att.db_set('operations_shift', shift_assignment.shif)
						att.db_set('project', shift_assignment.project)
			else:
				att = frappe.new_doc("Attendance")
				att.employee = self.employee
				att.employee_name = self.employee_name
				att.attendance_date = self.date
				att.status = self.attendance_status
				att.working_hours = 8 if self.attendance_status == 'Present' else 0
				att.roster_type = self.roster_type
				att.reference_doctype = "Attendance Check"
				att.reference_docname = self.name
				att.comment = "Created from Attendance Check"
				if self.shift_assignment:
					att.shift_assignment = self.shift_assignment
				if not att.shift_assignment:
					if frappe.db.exists("Shift Assignment", {
							'employee':self.employee, 'start_date':self.date, 'roster_type':self.roster_type
						}):
						shift_assignment = frappe.get_doc("Shift Assignment", {
							'employee':self.employee, 'start_date':self.date, 'roster_type':self.roster_type
						})
						att.shift_Assignment = shift_assignment.name
					elif frappe.db.exists("Employee Schedule", {
							'employee':self.employee, 'date':self.date, 'roster_type':self.roster_type
						}):
						employee_schedule = frappe.get_doc("Employee Schedule", {
							'employee':self.employee, 'date':self.date, 'roster_type':self.roster_type
						})
						shift_assignment = frappe.get_doc({
							'doctype':"Shift Assignment",
							'employee':employee_schedule.employee,
							'shift_type':employee_schedule.shift_type,
							'start_date':employee_schedule.date,
							'status':'Active'
						}).insert(ignore_permissions=1)
						shift_assignment.submit()
						att.shift_Assignment = shift_assignment.name	
				att.insert(ignore_permissions=True)
				att.submit()

	def validate_justification_and_attendance_status(self):
		if self.workflow_state in ['Approved', 'Rejected']:
			message = 'Justification' if not self.justification else False
			if not self.attendance_status:
				message = message + ' and Attendance Status' if message else 'Attendance Status'
			if message:
				frappe.throw(_('To Approve or Reject the Record set {0}'.format(message)))

def create_attendance_check(attendance_date=None):
	if not attendance_date:
		attendance_date = add_days(today(), -1)
	all_attendance = frappe.get_all("Attendance", filters={
		'attendance_date':attendance_date}, fields="*")
	all_attendance_employee = [i.employee for i in all_attendance]
	
	employee_schedules = frappe.db.get_list("Employee Schedule", filters={'date':attendance_date, 'employee_availability':'Working'}, fields="*")
	employee_schedules_basic = [i for i in employee_schedules if i.roster_type=='Basic']
	employee_schedules_ot = [i for i in employee_schedules if i.roster_type=='Over-Time']
	shift_assignments = frappe.db.get_list("Shift Assignment", filters={'start_date':attendance_date}, fields="*")
	shift_assignment_basic = [i for i in shift_assignments if i.roster_type=='Basic']
	shift_assignment_ot = [i for i in shift_assignments if i.roster_type=='Over-Time']
	shift_permissions = frappe.db.get_list("Shift Permission", filters={'date':attendance_date}, fields="*")
	timesheets = frappe.db.get_all("Timesheet", filters={'start_date':attendance_date}, fields="*")
	attendance_requests = frappe.db.sql(f"""
        SELECT * FROM `tabAttendance Request`
        WHERE '{attendance_date}' BETWEEN from_date AND to_date
        AND docstatus=1
    """, as_dict=1)

	attendance_basic = [i for i in all_attendance if i.roster_type=='Basic']
	attendance_ot = [i for i in all_attendance if i.roster_type=='Over-Time']
	attendance_basic_employees = [i.employee for i in attendance_basic]
	attendance_ot_employees = [i.employee for i in attendance_ot]

	#absent
	absent_attendance_basic = [i for i in attendance_basic if i.status=='Absent']
	absent_attendance_basic_list = [i.employee for i in absent_attendance_basic]
	absent_attendance_ot = [i for i in attendance_ot if i.status=='Absent']
	absent_attendance_ot_list = [i.employee for i in absent_attendance_ot]
	# missing attendance
	missing_basic = []
	for i in employee_schedules_basic: #employee schedule
		if not i.employee in attendance_basic_employees:
			missing_basic.append(i.employee)
	for i in shift_assignment_basic: #shift assignment
		if not i.employee in attendance_basic_employees:
			missing_basic.append(i.employee)

	missing_ot = []
	for i in employee_schedules_ot: #employee schedule
		if not i.employee in attendance_ot_employees:
			missing_ot.append(i.employee)
	for i in shift_assignment_ot: #shift assignment
		if not i.employee in attendance_ot_employees:
			missing_ot.append(i.employee)

	### Checkins
	in_checkins_basic = frappe.get_all("Employee Checkin", filters={
		'log_type': 'IN', 'shift_actual_start':['BETWEEN', [f"{attendance_date} 00:00:00.000000", f"{attendance_date} 23:59:59.999999"]],
		'roster_type':'Basic', 'employee':["IN", missing_basic+absent_attendance_basic_list]},
		fields="*", order_by="employee ASC", group_by="employee")
	
	out_checkins_basic = frappe.get_all("Employee Checkin", filters={
		'log_type': 'OUT', 
		'shift_actual_start':['BETWEEN', [f"{attendance_date} 00:00:00.000000", f"{attendance_date} 23:59:59.999999"]],
		'roster_type':'Basic', 'employee':["IN", missing_basic+absent_attendance_basic_list]},
		fields="*", order_by="employee DESC", group_by="employee")
	
	in_checkins_ot = frappe.get_all("Employee Checkin", filters={
		'log_type': 'IN', 'shift_actual_start':['BETWEEN', [f"{attendance_date} 00:00:00.000000", f"{attendance_date} 23:59:59.999999"]],
		'roster_type':'Over-Time', 'employee':["IN", missing_ot+absent_attendance_ot_list]},
		fields="*", order_by="employee ASC", group_by="employee")
	
	out_checkins_ot = frappe.get_all("Employee Checkin", filters={
		'log_type': 'OUT', 
		'shift_actual_start':['BETWEEN', [f"{attendance_date} 00:00:00.000000", f"{attendance_date} 23:59:59.999999"]],
		'roster_type':'Over-Time', 'employee':["IN", missing_ot+absent_attendance_ot_list]},
		fields="*", order_by="employee DESC", group_by="employee")

	### Create maps
	#  Schedules
	employee_schedules_ot_dict = {}
	for i in employee_schedules_ot:
		employee_schedules_ot_dict[i.employee] = i
	employee_schedules_basic_dict = {}
	for i in employee_schedules_basic:
		employee_schedules_basic_dict[i.employee] = i
	# Shift Assignment
	shift_assignment_ot_dict = {}
	for i in shift_assignment_ot:
		shift_assignment_ot_dict[i.employee] = i
	shift_assignment_basic_dict = {}
	for i in shift_assignment_basic:
		shift_assignment_basic_dict[i.employee] = i
	# Shift Permissions
	shift_permission_basic_dict = {}
	shift_permission_ot_dict = {}
	for i in shift_permissions:
		if i.roster_type=='Basic':
			shift_permission_basic_dict[i.employee] = i
		if i.roster_type=='Over-Time':
			shift_permission_ot_dict[i.employee] = i
	# Timesheet
	timesheets_dict = {}
	for i in timesheets:
		timesheets_dict[i.employee] = i
	
	# Attendance Request
	attendance_requests_dict = {}
	for i in attendance_requests:
		attendance_requests_dict[i.employee] = i
	
	# Attendance
	absent_attendance_basic_dict = {}
	for i in absent_attendance_basic:absent_attendance_basic_dict[i.employee] = i
	absent_attendance_ot_dict = {}
	for i in absent_attendance_ot:absent_attendance_ot_dict[i.employee] = i

	# Checkins
	in_checkins_basic_dict = {}
	for i in in_checkins_basic:in_checkins_basic_dict[i.employee] = i
	out_checkins_basic_dict = {}
	for i in out_checkins_basic:out_checkins_basic_dict[i.employee] = i
	in_checkins_ot_dict = {}
	for i in in_checkins_ot:in_checkins_ot_dict[i.employee] = i
	out_checkins_ot_dict = {}
	for i in out_checkins_ot:out_checkins_ot_dict[i.employee] = i

	# Get Supervisors
	operations_shifts = frappe.get_all("Operations Shift", fields=["name", "supervisor", "supervisor_name"])
	operations_sites = frappe.get_all("Operations Site", fields=["name", "account_supervisor", "account_supervisor_name"])
	operations_shifts_dict = {}
	for i in operations_shifts: operations_shifts_dict[i.name] = i
	operations_sites_dict = {}
	for i in operations_sites: operations_sites_dict[i.name] = i
	
	# Employees
	employees_dict = {}
	for i in frappe.get_all("Employee", filters={"name":["IN", missing_ot+missing_basic+absent_attendance_basic_list+absent_attendance_ot_list]}, fields="*"):
		employees_dict[i.name] = i
	
	
	### Create records
	# disable workflow
	workflow = frappe.get_doc("Workflow", "Attendance Check")
	workflow. is_active = 0
	workflow.save()
	# Absent record Basic
	attendance_check_list = []
	#basic create
	print(len(missing_basic+absent_attendance_basic_list), len(missing_ot+absent_attendance_ot_list))
	for i in missing_basic+absent_attendance_basic_list:
		employee = employees_dict.get(i)
		at_check = frappe._dict({
			"doctype":"Attendance Check",
			"employee": i,
			"employee_name":employee.employee_name,
			"department":employee.department,
			"date":str(attendance_date),
		})
		if absent_attendance_basic_dict.get(i):
			attendance = absent_attendance_basic_dict.get(i)
			at_check.attendance_marked = 1
			at_check.attendance = attendance.name
			at_check.marked_attendance_status = attendance.status
			at_check.roster_type = attendance.roster_type
			at_check.comment = attendance.comment
		if in_checkins_basic_dict.get(i):
			checkin_basic = in_checkins_basic_dict.get(i)
			at_check.has_checkin_record = 1
			at_check.checkin_record = checkin_basic.name
			at_check.roster_type = checkin_basic.roster_type
		if out_checkins_basic_dict.get(i):
			checkout_basic = out_checkins_basic_dict.get(i)
			at_check.has_checkout_record = 1
			at_check.checkout_record = checkout_basic.name
			at_check.roster_type = checkout_basic.roster_type
		if shift_assignment_basic_dict.get(i):
			shift_assignment = shift_assignment_basic_dict.get(i)
			at_check.has_shift_assignment = 1
			at_check.shift_assignment = shift_assignment.name
			at_check.start_time = shift_assignment.start_datetime
			at_check.end_time = shift_assignment.end_datetime
			at_check.roster_type = shift_assignment.roster_type
			shift_supervisor = operations_shifts_dict.get(shift_assignment.shift)
			if shift_supervisor:
				at_check.shift_supervisor = shift_supervisor.supervisor
				at_check.shift_supervisor_name = shift_supervisor.supervisor_name
		if shift_permission_basic_dict.get(i):
			shift_permission = shift_permission_basic_dict.get(i)
			at_check.has_shift_permission
			at_check.shift_permission = shift_permission.name
			at_check.roster_type = shift_permission.roster_type
		if attendance_requests_dict.get(i):
			attendance_request = attendance_requests_dict.get(i)
			at_check.has_attendance_request = 1
			at_check.attendance_request = attendance_request.name

		# add supervisor
		if not at_check.shift_supervisor:
			if employee.shift:
				shift_supervisor = operations_shifts_dict.get(employee.shift)
				at_check.shift_supervisor = shift_supervisor.supervisor
				at_check.shift_supervisor_name = shift_supervisor.supervisor_name
		if not at_check.site_supervisor:
			if employee.site:
				site_supervisor = operations_sites_dict.get(employee.site)
				at_check.site_supervisor = site_supervisor.account_supervisor
				at_check.site_supervisor_name = site_supervisor.account_supervisor_name
		
		if not frappe.db.exists("Attendance Check", {"employee":i, 'date':attendance_date, 'roster_type':at_check.roster_type}):
			try:
				at_check_doc = frappe.get_doc(at_check).insert(ignore_permissions=1)
				attendance_check_list.append(at_check_doc.name)
			except:
				pass

	# OT Create
	for i in missing_ot+absent_attendance_ot_list:
		employee = employees_dict.get(i)
		at_check = frappe._dict({
			"doctype":"Attendance Check",
			"employee": i,
			"employee_name":employee.employee_name,
			"department":employee.department,
			"date":str(attendance_date),
		})
		if absent_attendance_ot_dict.get(i):
			attendance = absent_attendance_ot_dict.get(i)
			at_check.attendance_marked = 1
			at_check.attendance = attendance.name
			at_check.marked_attendance_status = attendance.status
			at_check.roster_type = attendance.roster_type
			at_check.comment = attendance.comment
		if in_checkins_ot_dict.get(i):
			checkin_ot = in_checkins_ot_dict.get(i)
			at_check.has_checkin_record = 1
			at_check.checkin_record = checkin_ot.name
			at_check.roster_type = checkin_ot.roster_type
		if out_checkins_ot_dict.get(i):
			checkout_ot = out_checkins_ot_dict.get(i)
			at_check.has_checkout_record = 1
			at_check.checkout_record = checkout_ot.name
			at_check.roster_type = checkout_ot.roster_type
		if shift_assignment_ot_dict.get(i):
			shift_assignment = shift_assignment_ot_dict.get(i)
			at_check.has_shift_assignment = 1
			at_check.shift_assignment = shift_assignment.name
			at_check.start_time = shift_assignment.start_datetime
			at_check.end_time = shift_assignment.end_datetime
			at_check.roster_type = shift_assignment.roster_type
			shift_supervisor = operations_shifts_dict.get(shift_assignment.shift)
			if shift_supervisor:
				at_check.shift_supervisor = shift_supervisor.supervisor
				at_check.shift_supervisor_name = shift_supervisor.supervisor_name
		if shift_permission_ot_dict.get(i):
			shift_permission = shift_permission_ot_dict.get(i)
			at_check.has_shift_permission
			at_check.shift_permission = shift_permission.name
			at_check.roster_type = shift_permission.roster_type
		
				# add supervisor
		if not at_check.shift_supervisor:
			if employee.shift:
				shift_supervisor = operations_shifts_dict.get(employee.shift)
				at_check.shift_supervisor = shift_supervisor.supervisor
				at_check.shift_supervisor_name = shift_supervisor.supervisor_name
		if not at_check.site_supervisor:
			if employee.site:
				site_supervisor = operations_sites_dict.get(employee.site)
				at_check.site_supervisor = site_supervisor.account_supervisor
				at_check.site_supervisor_name = site_supervisor.account_supervisor_name

		if not frappe.db.exists("Attendance Check", {"employee":i, 'date':attendance_date, 'roster_type':at_check.roster_type}):
			try:
				at_check_doc = frappe.get_doc(at_check).insert(ignore_permissions=1)
				attendance_check_list.append(at_check_doc.name)
			except:
				pass

	if len(attendance_check_list)==1:
		attendance_check_tuple = (attendance_check_list[0])
	elif len(attendance_check_list)>1:
		attendance_check_tuple = tuple(attendance_check_list)
	if attendance_check_list:
		frappe.db.sql(f"""
			UPDATE `tabAttendance Check` SET workflow_state="Pending Approval"
			WHERE name in {attendance_check_tuple}     
		""")
	# Enable workflow
	workflow = frappe.get_doc("Workflow", "Attendance Check")
	workflow. is_active = 1
	workflow.save()
	frappe.db.commit()


def approve_attendance_check():
	attendance_checks = frappe.get_all("Attendance Check", filters={
		"date":["<", today()], "workflow_state":"Pending Approval"}
	)
	for i in attendance_checks:
		doc = frappe.get_doc("Attendance Check", i.name)
		doc.justification = "Approved by Administrator"
		doc.attendance_status = "Present"
		doc.workflow_state = "Approved"
		try:
			doc.submit()
		except Exception as e:
			if str(e)=="To date can not greater than employee's relieving date":
				doc.db_set("Comment", f"Employee exited company on {frappe.db.get_value('Employee', doc.employee, 'relieving_date')}\n{doc.comment or ''}")

