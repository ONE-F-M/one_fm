import pandas as pd
import frappe, erpnext
from frappe import _
from frappe.utils import (
	now_datetime,nowtime, cstr, getdate, get_datetime, cint, add_to_date,
	datetime, today, add_days, now
)
from hrms.hr.doctype.attendance.attendance import *
from hrms.hr.utils import  validate_active_employee, get_holidays_for_employee
from one_fm.utils import get_holiday_today
from one_fm.operations.doctype.shift_permission.shift_permission import create_checkin as approve_shift_permission
from one_fm.operations.doctype.employee_checkin_issue.employee_checkin_issue import approve_open_employee_checkin_issue


def get_duplicate_attendance_record(employee, attendance_date, shift, roster_type, name=None):
    overlapping_attendance = frappe.db.get_list("Attendance", filters={
        'employee':employee,
        'attendance_date':attendance_date,
        'shift':shift,
        'roster_type': roster_type,
        'docstatus': 1
    }, fields="*")

    return overlapping_attendance


def get_overlapping_shift_attendance(employee, attendance_date, shift, roster_type, name=None):
	if not shift:
		return {}

	attendance = frappe.qb.DocType("Attendance")
	query = (
		frappe.qb.from_(attendance)
		.select(attendance.name, attendance.shift)
		.where(
			(attendance.employee == employee)
			& (attendance.docstatus < 2)
			& (attendance.attendance_date == attendance_date)
			& (attendance.shift != shift)
            & (attendance.roster_type == roster_type)
		)
	)

	if name:
		query = query.where(attendance.name != name)

	overlapping_attendance = query.run(as_dict=True)

	if overlapping_attendance and has_overlapping_timings(shift, overlapping_attendance[0].shift):
		return overlapping_attendance[0]
	return {}


class AttendanceOverride(Attendance):
    def validate(self):
        from erpnext.controllers.status_updater import validate_status

        validate_status(self.status, ["Present", "Absent", "On Leave", "Half Day", "Work From Home", "Day Off", "Holiday"])
        validate_active_employee(self.employee)
        self.validate_attendance_date()
        self.validate_duplicate_record()
        self.validate_overlapping_shift_attendance()
        self.validate_employee_status()
        self.check_leave_record()
        self.validate_working_hours()

    def validate_working_hours(self):
        if self.status not in ['Absent', 'Day Off', 'Holiday', 'On Leave']:
            if not self.working_hours:frappe.throw("Working hours is required.")
            if self.working_hours <= 0:frappe.throw("Working hours must be greater than 0 if staus is Presnet ot Work From Home.")

    def before_save(self):
        if not self.shift_assignment and self.status=='Present':
            shift_assignment = frappe.db.get_value("Shift Assignment", {
                'employee':self.employee,
                'start_date':self.attendance_date,
                'status':'Active',
                'roster_type':'Basic',
                'docstatus':1
            }, ['*'], as_dict=1)
            if shift_assignment:
                self.shift_assignment = shift_assignment.name
                self.shift = shift_assignment.shift_type
                self.operations_shift = shift_assignment.shift
                self.site = shift_assignment.site
        if self.attendance_request and not self.working_hours and not self.status in [
            'Holiday', 'Day Off', 'Absent'
            ]:
            self.working_hours = frappe.db.get_value("Shift Type", self.shift_type, 'duration')

    def on_submit(self):
        self.update_shift_details_in_attendance()

    def validate_duplicate_record(self):
        duplicate = get_duplicate_attendance_record(
			self.employee, self.attendance_date, self.shift, self.roster_type, self.name
		)
        for d in duplicate:
            if d.roster_type==self.roster_type:
                frappe.throw(
                    _("Attendance for employee {0} is already marked for the date {1}: {2} : {3}").format(
                        frappe.bold(self.employee),
                        frappe.bold(self.attendance_date),
                        get_link_to_form("Attendance", d.name),
                        self.roster_type
                    ),
                    title=_("Duplicate Attendance"),
                    exc=DuplicateAttendanceError,
                )

    def validate_overlapping_shift_attendance(self):
        attendance = get_overlapping_shift_attendance(
			self.employee, self.attendance_date, self.shift, self.roster_type, self.name
		)

        if attendance:
            frappe.throw(
				_("Attendance for employee {0} is already marked for an overlapping shift {1}: {2}").format(
					frappe.bold(self.employee),
					frappe.bold(attendance.shift),
					get_link_to_form("Attendance", attendance.name),
				),
				title=_("Overlapping Shift Attendance"),
				exc=OverlappingShiftAttendanceError,
			)

    def on_trash(self):
        if frappe.db.exists("Additional Salary", {
            'ref_doctype':self.doctype,
            'ref_docname':self.name
            }):
            frappe.get_doc("Additional Salary", {
                'ref_doctype':self.doctype,
                'ref_docname':self.name}).delete()

    def update_shift_details_in_attendance(doc):
        return



@frappe.whitelist()
def mark_single_attendance(emp, att_date, roster_type="Basic"):
    # check if attendance exists
    #  get holiday, employee schedule, shift assignment, employee checkins
    if not frappe.db.exists("Attendance", {
        'employee': emp,
        'attendance_date':att_date,
        'status': ['!=', 'Absent'],
        'roster_type': roster_type,
        'docstatus':1
        }):
        open_leaves = frappe.db.sql(f"""
            SELECT name, employee FROM `tabLeave Application`
            WHERE employee='{emp}' AND status='Open' AND '{att_date}' BETWEEN from_date AND to_date;
        """, as_dict=1)
        if not open_leaves: # continue if no open leaves
            employee = frappe.get_doc("Employee", emp)
            status = "Absent"
            comment = ""
            # check holiday
            holiday_today = get_holiday_today(att_date)
            employee_schedule = frappe.db.get_value("Employee Schedule", {'employee':emp, 'date':att_date}, ["*"], as_dict=1)
            if employee_schedule:
                if employee_schedule.employee_availability == 'Day Off':
                    status = "Day Off"
                    comment = f"Employee Schedule - {employee_schedule.name}"
                    create_single_attendance_record(
                        frappe._dict({
                        'employee':employee,
                        'attendance_date':att_date,
                        'status':status,
                        'comment':comment
                        })
                    )
                    return

            if holiday_today.get(employee.holiday_list):
                status = "Holiday"
                comment = "Holiday - " +str(holiday_today.get(employee.holiday_list))
                create_single_attendance_record(
                    frappe._dict({
                        'employee':employee,
                        'attendance_date':att_date,
                        'status':status,
                        'comment':comment
                    })
                )
                return
            elif employee_schedule:
                if employee_schedule.employee_availability == 'Working':
                    # continue to mark attendance if checkin exists
                    mark_for_shift_assignment(employee, att_date)

            # check for shift assignment
            else:
                mark_for_shift_assignment(employee, att_date)

def mark_for_shift_assignment(employee, att_date, roster_type='Basic'):
    shift_assignment = frappe.db.get_value("Shift Assignment", {
        'employee':employee.name,
        'start_date':att_date,
        'roster_type':roster_type,
        'docstatus':1
        }, ["*"], as_dict=1
    )
    if shift_assignment:
        # checkin if any open shift permission and approve
        shift_permissions = frappe.db.get_list("Shift Permission", filters={
            'employee':employee.name,
            'date':att_date,
            'docstatus':0,
            'workflow_state':'Pending'
        })
        for i in shift_permissions:
            approve_shift_permission(i.name)

        status = 'Absent'
        comment = 'No checkin records found'
        working_hours = 0
        checkin = ''
        checkout = ''

        in_checkins = frappe.db.get_list("Employee Checkin", filters={"shift_assignment": shift_assignment.name, 'log_type': 'IN'},
            fields="name, owner, creation, modified, modified_by, docstatus, idx, employee, employee_name, log_type, late_entry, early_exit, time, date, skip_auto_attendance, shift_actual_start, shift_actual_end, shift_assignment, operations_shift, shift_type, shift_permission, actual_time, MIN(time) as time",
            order_by="employee ASC", group_by="shift_assignment"
        )
        in_checkins = in_checkins[0] if in_checkins else frappe._dict({})
        out_checkins = frappe.db.get_list("Employee Checkin", filters={"shift_assignment": shift_assignment.name, 'log_type': 'OUT'},
            fields="name, owner, creation, modified, modified_by, docstatus, idx, employee, employee_name, log_type, late_entry, early_exit, time, date, skip_auto_attendance, shift_actual_start, shift_actual_end, shift_assignment, operations_shift, shift_type, shift_permission, actual_time, MAX(time) as time",
            order_by="employee ASC", group_by="shift_assignment"
        )
        out_checkins = out_checkins[0] if out_checkins else frappe._dict({})
        # start checkin
        if in_checkins:
            if ((in_checkins.time - shift_assignment.start_datetime).total_seconds() / (60*60)) > 4:
                status = 'Absent'
                comment = f" 4 hrs late, checkin in at {in_checkins.time}"
            elif in_checkins and not out_checkins:
                working_hours = ((shift_assignment.end_datetime - in_checkins.time).total_seconds() / (60*60))
                status = 'Present'
                comment = "Checkin but no checkout record found"
                checkin = in_checkins
            elif in_checkins and out_checkins:
                working_hours = ((out_checkins.time - in_checkins.time).total_seconds() / (60*60))
                status = 'Present'
                comment = ""
                checkin = in_checkins
                checkout = out_checkins

        create_single_attendance_record(frappe._dict({
            'status': status,
            'comment': comment,
            'attendance_date': att_date,
            'working_hours': working_hours,
            'checkin': checkin,
            'checkout': checkout,
            'shift_assignment':shift_assignment,
            'employee':employee,
            'roster_type': roster_type
            })
        )


        # working_hours = (out_time - in_time).total_seconds() / (60 * 60)


def create_single_attendance_record(record):
    if not frappe.db.exists("Attendance", {
        'employee':record.employee.name,
        'attendance_date':record.attendance_date,
        'roster_type':record.roster_type,
        'status': ["IN", ["Present", "On Leave", "Holiday", "Day Off"]]
        }):
        # clear absent
        frappe.db.sql(f"""
            DELETE FROM `tabAttendance` WHERE employee="{record.employee.name}" AND
            attendance_date="{record.attendance_date}" AND roster_type="{record.roster_type}"
            AND status="Absent"
        """)
        frappe.db.commit()
        doc = frappe._dict({})
        doc.doctype = "Attendance"
        doc.employee = record.employee.name
        doc.employee_name = record.employee.employee_name
        doc.status = record.status
        doc.attendance_date = record.attendance_date
        doc.company = record.employee.company
        doc.department = record.employee.department
        doc.working_hours = round(record.working_hours, 2) if record.working_hours else 0
        if record.shift_assignment:
            doc.shift_assignment = record.shift_assignment.name
            doc.shift = record.shift_assignment.shift_type
            doc.operations_shift = record.shift_assignment.shift
            doc.site = record.shift_assignment.site
        if record.checkin:
            if record.checkin.late_entry:doc.late_entry=1
        if record.checkout:
            if record.checkout.early_exit:doc.early_exit=1
        doc.roster_type = record.roster_type
        if record.comment:
            doc.comment = record.comment
        doc = frappe.get_doc(doc)
        if doc.working_hours < 4:
            doc.status = 'Absent'
            doc.comment = 'Late Checkin, 4hrs late.'
        if doc.status in ['Work From Home', 'Day Off', 'Holiday']:
            doc.flags.ignore_validate = True
            doc.save()
            doc.db_set('docstatus', 1)
        else:
            doc.submit()
        # updated checkins if exists
        if record.checkin:
            frappe.db.set_value("Employee Checkin", record.checkin.name, 'attendance', doc.name)
        if record.checkout:
            frappe.db.set_value("Employee Checkin", record.checkout.name, 'attendance', doc.name)
        frappe.db.commit()


@frappe.whitelist()
def mark_bulk_attendance(employee, from_date, to_date):
    employee_doc = frappe.get_doc("Employee", employee)
    date_range = pd.date_range(from_date, to_date)
    for date in date_range:
        mark_single_attendance(employee, date)
        mark_for_shift_assignment(employee_doc, date, roster_type='Over-Time')

    frappe.msgprint(f"Marked Attendance successfully for {employee} between {from_date} and {to_date}")


def remark_absent_for_employees(employees, date):
    # mark attendance
    for emp in employees:
        mark_single_attendance(emp, date)

def mark_overtime_attendance(from_date, to_date):
    shift_assignments = frappe.db.get_list("Shift Assignment", filters={
        'start_date':from_date,
        'end_date':to_date,
        'roster_type': 'Over-Time',
        'docstatus':1
    }, fields=["employee"])
    for employee in frappe.db.get_list("Employee", {
        'name': ["IN", [i.employee for i in shift_assignments]],
        'status':'Active'
        }):
        mark_for_shift_assignment(employee, from_date, roster_type='Over-Time')


def mark_day_attendance():
	from one_fm.operations.doctype.shift_permission.shift_permission import approve_open_shift_permission
	start_date, end_date = add_days(getdate(), -1), add_days(getdate(), -1)
	approve_open_shift_permission(str(start_date), str(end_date))
	approve_open_employee_checkin_issue(str(start_date), str(end_date))
	frappe.enqueue(mark_open_timesheet_and_create_attendance)
	frappe.enqueue(mark_daily_attendance, start_date=start_date, end_date=end_date, timeout=4000, queue='long')


def mark_night_attendance():
	from one_fm.operations.doctype.shift_permission.shift_permission import approve_open_shift_permission
	start_date = add_days(getdate(), -1)
	end_date =  getdate()
	approve_open_shift_permission(str(start_date), str(end_date))
	approve_open_employee_checkin_issue(str(start_date), str(end_date))
	frappe.enqueue(mark_open_timesheet_and_create_attendance)
	frappe.enqueue(mark_daily_attendance, start_date=start_date, end_date=end_date, timeout=4000, queue='long')

# mark daily attendance
def mark_daily_attendance(start_date, end_date):
	"""
		This method marks attendance for all employees
	"""
	try:
		errors = []
		absent_list = []
		owner = frappe.session.user
		creation = now()
		# get holiday for today
		holiday_today = get_holiday_today(start_date)
		# Get shift type and make hashmap
		shift_types = frappe.get_list("Shift Type", fields="*")
		shift_types_dict = {}
		for i in shift_types:
			shift_types_dict[i.name] = i

		# get Day off employee schedule
		employee_schedules = frappe.db.get_list("Employee Schedule", filters={'date':start_date, 'employee_availability':'Day Off'}, fields="*")
		employee_schedule_dict = {}
		for i in employee_schedules:
			employee_schedule_dict[i.employee] = i

		employees = frappe.get_list("Employee", filters={'status': 'Active', 'attendance_by_timesheet': ['!=', 1]}, fields="*")
		employees_data = {}
		for i in employees:
			employees_data[i.name] = i

		employees_dict = {}

		# get open leaves
		open_leaves = frappe.db.sql(f"""
			SELECT name, employee FROM `tabLeave Application`
			WHERE '{start_date}' BETWEEN from_date AND to_date AND status='Open';
		""", as_dict=1)
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
		# exempt leave applicants from attendance
		for i in open_leaves:
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
		in_checkins = frappe.get_list("Employee Checkin", filters={"shift_assignment": ["IN", shift_assignments_list], 'log_type': 'IN'},
			fields="name, owner, creation, modified, modified_by, docstatus, idx, employee, employee_name, log_type, late_entry, early_exit, time, date, skip_auto_attendance, shift_actual_start, shift_actual_end, shift_assignment, operations_shift, shift_type, shift_permission, actual_time, MIN(time) as time",
			order_by="employee ASC", group_by="shift_assignment")
		out_checkins = frappe.get_list("Employee Checkin", filters={"shift_assignment": ["IN", shift_assignments_list], 'log_type': 'OUT'},
			fields="name, owner, creation, modified, modified_by, docstatus, idx, employee, employee_name, log_type, late_entry, early_exit, time, date, skip_auto_attendance, shift_actual_start, shift_actual_end, shift_assignment, operations_shift, shift_type, shift_permission, actual_time, MAX(time) as time",
			order_by="employee DESC", group_by="shift_assignment")

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
				in_time = v.time

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
					if not i.employee in absent_list:absent_list.append(i.employee)
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
						'department': emp.department, 'late_entry':v.late_entry, 'early_exit':0, 'operations_role':shift_assignment.operations_role,
						'post_abbrv':shift_assignment.post_abbrv,
						'roster_type':shift_assignment.roster_type, 'docstatus':1, 'owner':owner, 'modified_by':owner, 'creation':creation, 'modified':creation, 'comment':"Checkin but no checkout record found"
					})
					# add employee to no checkout record found
					checkin_no_out.append({'employee':v.employee, 'in':v.name, 'shift_assignment':v.shift_assignment})
			except Exception as e:
				errors.append(str(frappe.get_traceback()))
		# add absent, day off and holiday in shift assignment
		for i in shift_assignments:
			try:
				if not employee_attendance.get(i.employee):
					# check for day off
					comment = ""
					if employee_schedule_dict.get(i.employee):
						availability = 'Day Off'
					elif holiday_today and holiday_today.get(employees_data[i.employee].holiday_list):
						availability = 'Holiday'
						comment = str(holiday_today.get(employees_data[i.employee].holiday_list))
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
						'roster_type':i.roster_type, 'docstatus':1, 'owner':owner, 'modified_by':owner, 'creation':creation, 'modified':creation,
						'comment':comment
					})
					if (availability == 'Absent') and (not i.employee in absent_list):absent_list.append(i.employee)
			except Exception as e:
				errors.append(str(frappe.get_traceback()))

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
				errors.append(str(frappe.get_traceback()))
    
	

		# Get attendance by timesheet employees
		timesheet_employees = frappe.get_list("Employee", filters={'status': 'Active', 'attendance_by_timesheet': 1}, fields="*")
		timesheet_employees_data = {}
		for i in timesheet_employees:
			timesheet_employees_data[i.name] = i

		# Get attendance by timesheet employees timesheet
		timesheet_list = frappe.get_list("Timesheet",
			filters={
				"start_date":start_date, "end_date": end_date, "docstatus": 1, "attendance_by_timesheet": 1,
				'workflow_state': 'Approved'
			},
			fields=['name', 'employee']
		)
		timesheet_dict = {}
		for i in timesheet_list:
			timesheet_dict[i.employee] = i

		for key_emp_id in timesheet_employees_data:
			try:
				if not timesheet_dict.get(key_emp_id):
					emp = timesheet_employees_data.get(key_emp_id)
					employee_attendance[key_emp_id] = frappe._dict({
						'name':f"HR-ATT-{start_date}-{key_emp_id}", 'employee':key_emp_id, 'employee_name':emp.employee_name,
						'working_hours':0, 'status':'Absent', 'shift':'', 'in_time':'00:00:00', 'out_time':'00:00:00',
						'shift_assignment':'', 'operations_shift':'', 'site':'', 'project':timesheet_employees_data[key_emp_id].project,
						'attendance_date': start_date, 'company':emp.company, 'department': emp.department, 'late_entry':0,
						'early_exit':0, 'operations_role':'', 'post_abbrv':'', 'roster_type':'Basic', 'docstatus':1, 'owner':owner,
						'modified_by':owner, 'creation':creation, 'modified':creation, 'comment':f"No Timesheet found"
					})
			except Exception as e:
				errors.append(str(frappe.get_traceback()))

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
						"{v.department}", {v.late_entry}, {v.early_exit}, "{v.operations_role}", "{v.post_abbrv}", "{v.roster_type or 'Basic'}", {v.docstatus}, "{v.owner}",
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
				errors.append(frappe.get_traceback())

		# check for error
		if len(errors):
			frappe.log_error(str(errors), "Mark Attendance")
		#
		# remark absent attendance and holiday list
		if (start_date==end_date):
			holiday_list_today = [k for k,v in get_holiday_today(start_date).items()]
			holidays = []
			for i in holiday_list_today:
				holidays += frappe.db.sql(f"""
					SELECT name FROM `tabEmployee`
					WHERE status='Active' AND holiday_list="{i}"
					AND name not in (
						SELECT employee FROM `tabShift Assignment`
						WHERE start_date='{start_date}')
				""", as_dict=1)
			if holidays:
				absent_list = [i.name for i in holidays]+absent_list

		# frappe.enqueue("one_fm.overrides.attendance.remark_absent_for_employees",
		# 	employees=absent_list, date=str(start_date), queue='long', timeout=6000)
		# frappe.enqueue("one_fm.overrides.attendance.mark_overtime_attendance",
		# 	from_date=start_date, to_date=end_date, queue='long', timeout=6000)

  
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), 'Mark Attendance')


def mark_open_timesheet_and_create_attendance():
    the_timesheet_list = frappe.db.get_list("Timesheet", filters={"workflow_state": "Open"}, pluck="name")
    for name in the_timesheet_list:
        frappe.db.set_value("Timesheet", name, "workflow_state", "Approved")
        frappe.db.set_value("Timesheet", name, "docstatus", 1)
        comment = frappe.get_doc({
            "doctype": "Comment",
            "content": _("Approved"),
            "owner": frappe.session.user,
            "comment_type": "Workflow",
            "comment_email": "Administrator",
            "reference_doctype": "Timesheet",
            "reference_name": name
        })
        comment.insert(ignore_permissions=True)
        doc = frappe.get_doc("Timesheet", name )
        doc.create_attendance()
