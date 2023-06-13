# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import nowdate, add_to_date, cstr, add_days, today
from one_fm.utils import production_domain

class AttendanceCheck(Document):
	def on_submit(self):
		self.validate_justification_and_attendance_status()
		self.mark_attendance()

	def mark_attendance(self):
		if self.workflow_state == 'Approved':
			comment = ""
			logs = []
			if frappe.db.exists('Attendance',
				{'attendance_date': self.date, 'employee': self.employee, 'docstatus': ['<', 2],
				'roster_type':self.roster_type
				}):
				att = frappe.get_doc("Attendance", {
					'attendance_date': self.date, 'employee': self.employee, 
					'docstatus': ['<', 2],
					'roster_type':self.roster_type
				})
				logs = frappe.get_all("Employee Checkin", filters={"attendance":att.name})
				comment = att.comment
				frappe.db.sql(f"""DELETE FROM `tabAttendance` WHERE name="{att.name}" """)

			att = frappe.new_doc("Attendance")
			att.employee = self.employee
			att.employee_name = self.employee_name
			att.attendance_date = self.date
			att.status = self.attendance_status
			att.roster_type = self.roster_type
			att.reference_doctype = "Attendance Check"
			att.reference_docname = self.name
			att.comment = f"Created from Attendance Check\n{self.justification}\n{self.comment or ''}\n{comment or ''}"
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
			if att.shift_assignment and att.status=='Present':
				att.working_hours = frappe.db.get_value("Operations Shift", 
					frappe.db.get_value("Shift Assignment", att.shift_assignment, 'shift'), 'duration')
			if not att.working_hours:
				att.working_hours = 8 if self.attendance_status == 'Present' else 0
			att.insert(ignore_permissions=True)
			att.submit()
			for i in logs:
				frappe.db.set_value("Employee Checkin", i.name, "attendance", att.name)


	def validate_justification_and_attendance_status(self):
		if self.workflow_state in ['Approved', 'Rejected']:
			message = 'Justification' if not self.justification else False
			if not self.attendance_status:
				message = message + ' and Attendance Status' if message else 'Attendance Status'
			if message:
				frappe.throw(_('To Approve or Reject the Record set {0}'.format(message)))

def create_attendance_check(attendance_date=None):
	if production_domain():
		attendance_checkin_found = []
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
		checkin_basic_filter = missing_basic+absent_attendance_basic_list
		if len(checkin_basic_filter)==1:
			checkin_basic_filter_tuple = (checkin_basic_filter[0])
		elif len(checkin_basic_filter)>1:
			checkin_basic_filter_tuple = tuple(checkin_basic_filter)
		else:
			checkin_basic_filter_tuple = ()

		checkin_ot_filter = missing_ot+absent_attendance_ot_list
		if len(checkin_ot_filter)==1:
			checkin_ot_filter_tuple = (checkin_ot_filter[0])
		elif len(checkin_ot_filter)>1:
			checkin_ot_filter_tuple = tuple(checkin_ot_filter)
		else:
			checkin_ot_filter_tuple = ()

		in_checkins_basic = frappe.db.sql(f""" 
			SELECT name, owner, creation, modified, modified_by, docstatus, idx, employee, 
			employee_name, log_type, late_entry, early_exit, time, date, skip_auto_attendance, 
			shift_actual_start, shift_actual_end, shift_assignment, operations_shift, shift_type, 
			shift_permission, actual_time, MIN(time) as time FROM `tabEmployee Checkin` 
			WHERE 
			roster_type='Basic' AND log_type='IN' AND employee IN {checkin_basic_filter_tuple} AND
			shift_actual_start BETWEEN '{attendance_date} 00:00:00' AND '{attendance_date} 23:59:59' 
			GROUP BY employee
			ORDER BY employee
		""", as_dict=1)
		
		out_checkins_basic = frappe.db.sql(f""" 
			SELECT name, owner, creation, modified, modified_by, docstatus, idx, employee, 
			employee_name, log_type, late_entry, early_exit, time, date, skip_auto_attendance, 
			shift_actual_start, shift_actual_end, shift_assignment, operations_shift, shift_type, 
			shift_permission, actual_time, MAX(time) as time FROM `tabEmployee Checkin` 
			WHERE 
			roster_type='Basic' AND log_type='OUT' AND employee IN {checkin_basic_filter_tuple} AND
			shift_actual_start BETWEEN '{attendance_date} 00:00:00' AND '{attendance_date} 23:59:59' 
			GROUP BY employee
			ORDER BY employee
		""", as_dict=1)
		
		in_checkins_ot = frappe.db.sql(f""" 
			SELECT name, owner, creation, modified, modified_by, docstatus, idx, employee, 
            employee_name, log_type, late_entry, early_exit, time, date, skip_auto_attendance, 
            shift_actual_start, shift_actual_end, shift_assignment, operations_shift, shift_type,
            roster_type, operations_site, project, company, operations_role, post_abbrv,
            shift_permission, actual_time, MIN(time) as time  FROM `tabEmployee Checkin` 
			WHERE 
			roster_type='Over-Time' AND log_type='IN' AND employee IN {checkin_ot_filter_tuple} AND
			shift_actual_start BETWEEN '{attendance_date} 00:00:00' AND '{attendance_date} 23:59:59' 
			GROUP BY employee
			ORDER BY employee
		""", as_dict=1)
		
		out_checkins_ot = frappe.db.sql(f""" 
			SELECT name, owner, creation, modified, modified_by, docstatus, idx, employee, 
            employee_name, log_type, late_entry, early_exit, time, date, skip_auto_attendance, 
            shift_actual_start, shift_actual_end, shift_assignment, operations_shift, shift_type,
            roster_type, operations_site, project, company, operations_role, post_abbrv,
            shift_permission, actual_time, MIN(time) as time  FROM `tabEmployee Checkin` 
			WHERE 
			roster_type='Over-Time' AND log_type='OUT' AND employee IN {checkin_ot_filter_tuple} AND
			shift_actual_start BETWEEN '{attendance_date} 00:00:00' AND '{attendance_date} 23:59:59' 
			GROUP BY employee
			ORDER BY employee
		""", as_dict=1)

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
				# check if late hours
				if (checkin_basic.time - checkin_basic.shift_actual_start).total_seconds() / (60*60) > 4:
					at_check.comment = f"4 hrs late, checkin in at {checkin_basic.time}"
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
					# if at_check.has_checkin_record and not str(at_check.comment).startswith('4'):
					# 	attendance_checkin_found.append(at_check)
					# else:
					at_check_doc = frappe.get_doc(at_check).insert(ignore_permissions=1)
					attendance_check_list.append(at_check_doc.name)
				except Exception as e:
					print(e)

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
				# check if late hours
				if (checkin_ot.time - checkin_ot.shift_actual_start).total_seconds() / (60*60) > 4:
					at_check.comment = f"4 hrs late, checkin in at {checkin_ot.time}"
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
					# if at_check.has_checkin_record and not str(at_check.comment).startswith('4'):
					# 	attendance_checkin_found.append(at_check)
					# else:
					at_check_doc = frappe.get_doc(at_check).insert(ignore_permissions=1)
					attendance_check_list.append(at_check_doc.name)
				except Exception as e:
					print(e)

		# remark missing
		frappe.enqueue(mark_missing_attendance, attendance_checkin_found=attendance_checkin_found, queue='long', timeout=5000)

		# update employee checkin
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
		if not doc.justification:
			doc.justification = "Approved by Administrator"
		if not doc.attendance_status:
			doc.attendance_status = "Absent"
		doc.workflow_state = "Approved"
		try:
			doc.submit()
		except Exception as e:
			if str(e)=="To date can not greater than employee's relieving date":
				doc.db_set("Comment", f"Employee exited company on {frappe.db.get_value('Employee', doc.employee, 'relieving_date')}\n{doc.comment or ''}")


def mark_missing_attendance(attendance_checkin_found):
	for i in attendance_checkin_found:
		try:
			checkin_record = ""
			checkout_record = ""
			shift_assignment = ""
			att = ""
			working_hours = 0
			in_time = ''
			out_time = ''
			comment = ''
			day_off_ot = 0
			
			if i.attendance:
				att = frappe.get_doc("Attendance", i.attendance)
			if i.shift_assignment:
				shift_assignment = frappe.get_doc("Shift Assignment", i.shift_assignment)
				day_off_ot = frappe.get_value("Employee Schedule", {
					'employee':i.employee,
					'date':i.date,
					'roster_type':i.roster_type
				}, 'day_off_ot')
			if i.checkin_record:
				checkin_record = frappe.get_doc("Employee Checkin", i.checkin_record)
			if i.checkout_record:
				checkout_record = frappe.get_doc("Employee Checkin", i.checkout_record)
			
			# calculate working hours
			if checkin_record and not checkout_record and shift_assignment:
				working_hours = (shift_assignment.end_datetime - checkin_record.time).total_seconds() / (60 * 60)
				in_time = checkin_record.time
				out_time = shift_assignment.end_datetime
				comment = "No checkout record found"
			elif checkin_record and checkout_record and shift_assignment:
				working_hours = (checkout_record.time - checkin_record.time).total_seconds() / (60 * 60)
				in_time = checkin_record.time
				out_time = checkout_record.time
			if att:
				# set values based on existing attendance
				if att.status=='Absent':
					att.db_set({
						'working_hours':working_hours,
						'in_time':in_time,
						'out_time':out_time,
						'comment':comment,
						'day_off_ot':day_off_ot,
						'status':'Present'
					})
			else:
				att = frappe.new_doc("Attendance")
				att.employee = i.employee
				att.employee_name = i.employee_name
				att.attendance_date = i.date
				att.status = 'Present'
				att.roster_type = i.roster_type
				att.shift_assignment = i.shift_assignment
				att.in_time = in_time
				att.out_time = out_time
				att.working_hours = working_hours
				att.comment = comment
				att.day_off_ot = day_off_ot
				att.insert(ignore_permissions=True)
				att.submit()
			frappe.db.set_value("Employee Checkin", i.checkin_record, "attendance", att.name)
			if checkout_record:
				frappe.db.set_value("Employee Checkin", i.checkout_record, "attendance", attendance.name)
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), 'Attendance Remark')