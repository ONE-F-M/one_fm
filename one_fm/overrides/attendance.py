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
from frappe.model import table_fields

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

        validate_status(self.status, ["Present", "Absent", "On Leave", "Half Day", "Work From Home", "Day Off", "Holiday", "On Hold"])
        validate_active_employee(self.employee)
        self.validate_attendance_date()
        self.validate_duplicate_record()
        self.validate_overlapping_shift_attendance()
        self.validate_employee_status()
        self.check_leave_record()
        self.validate_working_hours()

    def validate_working_hours(self):
        if self.status not in ['Absent', 'Day Off', 'Holiday', 'On Leave', 'On Hold']:
            if not self.working_hours:frappe.throw("Working hours is required.")
            if self.working_hours <= 0:frappe.throw("Working hours must be greater than 0 if staus is Presnet ot Work From Home.")

    def after_insert(self):
        self.set_day_off_ot()

    def set_day_off_ot(self):
        if self.shift_assignment:
            day_off_ot = frappe.db.get_value("Employee Schedule", {
                'employee':self.employee,
                'date':self.attendance_date,
                'roster_type':self.roster_type
            }, 'day_off_ot')
            if day_off_ot:
                self.db_set("day_off_ot", day_off_ot)

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

    def validate_update_after_submit(self):
        db_values = frappe.get_doc(self.doctype, self.name).as_dict()

        for key in self.as_dict():
            df = self.meta.get_field(key)
            db_value = db_values.get(key)
            if key in ["status","working_hours"] and "Payroll Operator" in frappe.get_roles():
                df.allow_on_submit = 1

            if df and not df.allow_on_submit and (self.get(key) or db_value):
                if df.fieldtype in table_fields:
                    # just check if the table size has changed
                    # individual fields will be checked in the loop for children
                    self_value = len(self.get(key))
                    db_value = len(db_value)

                else:
                    self_value = self.get_value(key)
                # Postgres stores values as `datetime.time`, MariaDB as `timedelta`
                if isinstance(self_value, datetime.timedelta) and isinstance(db_value, datetime.time):
                    db_value = datetime.timedelta(
                        hours=db_value.hour,
                        minutes=db_value.minute,
                        seconds=db_value.second,
                        microseconds=db_value.microsecond,
                    )
                if self_value != db_value:
                    frappe.throw(
                        _("{0} Not allowed to change {1} after submission from {2} to {3}").format(
                            f"Row #{self.idx}:" if self.get("parent") else "",
                            frappe.bold(_(df.label)),
                            frappe.bold(db_value),
                            frappe.bold(self_value),
                        ),
                        frappe.UpdateAfterSubmitError,
                        title=_("Cannot Update After Submit"),
                    )

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
        if shift_permissions:
            for i in shift_permissions:
                idoc = frappe.get_doc("Shift Permission", i.name)
                approve_shift_permission(idoc)

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

def mark_daily_attendance(start_date, end_date):
    # try:
    creation = now()
    print(start_date, end_date)
    owner = frappe.session.user
    naming_series = 'HR-ATT-.YYYY.-'
    new_attendances = []
    basic_unavailable = []
    basic_available = []
    checkin_attendance_link = {}
    query = """
        INSERT INTO `tabAttendance` (`name`, `naming_series`,`employee`, `employee_name`, `working_hours`, `status`, `shift`, `in_time`, `out_time`,
        `shift_assignment`, `operations_shift`, `site`, `project`, `attendance_date`, `company`,
        `department`, `late_entry`, `early_exit`, `operations_role`, `post_abbrv`, `roster_type`, `docstatus`, `modified_by`, `owner`,
        `creation`, `modified`, `comment`)
        VALUES

    """
    query_body = """"""
    employees = frappe.get_all("Employee", fields="*")
    employees_dict = {}
    for i in employees:
        employees_dict[i.employee] = i
    operations_shift = frappe.get_all("Operations Shift", fields="*")
    operations_shift_dict = {}
    for i in operations_shift:operations_shift_dict[i.name]=i
    
    basic_attendances = frappe.db.get_all("Attendance", filters={
        'attendance_date':['BETWEEN', [start_date, end_date]],
        'roster_type':'Basic'
    }, fields="*")
    basic_attendance_employees = [i.employee for i in basic_attendances]
    ## TREAT BASIC
    basic_employee_schedules = frappe.get_all("Employee Schedule", filters={
        'date':["BETWEEN", [start_date, end_date]],
        'roster_type':'Basic'
    }, fields="*")
    print(basic_attendance_employees)
    basic_employee_schedules = [i for i in basic_employee_schedules if not i.employee in basic_attendance_employees]
    
    # Mark Holiday Attendance
    holiday_employee = frappe.db.sql(f"""SELECT e.*, h.description from `tabEmployee` e ,`tabHoliday List` hl 
                            INNER JOIN `tabHoliday` h ON h.parent = hl.name
                            WHERE e.holiday_list = hl.name 
                            AND h.holiday_date BETWEEN '{start_date}' AND '{end_date}'
                            AND h.weekly_off=0""", as_dict=1)
    holiday_attendance_employee = [i for i in holiday_employee if not i.employee in basic_attendance_employees]

    # Mark Holiday Attendance
    day_off_employee = frappe.db.sql(f"""SELECT e.*, h.description from `tabEmployee` e ,`tabHoliday List` hl 
                            INNER JOIN `tabHoliday` h ON h.parent = hl.name
                            WHERE e.holiday_list = hl.name 
                            AND h.holiday_date BETWEEN '{start_date}' AND '{end_date}'
                            AND h.weekly_off=1""", as_dict=1)
    day_off_attendance_employee = [i for i in day_off_employee if not i.employee in basic_attendance_employees]

    on_hold_employees = frappe.db.sql(f""" SELECT es.* from `tabEmployee Schedule` es
                            INNER JOIN `tabOperations Role` o ON es.operations_role = o.name
                            WHERE es.date BETWEEN '{start_date}' AND '{end_date}'
                            AND o.attendance_by_client = 1
                            """, as_dict=1)
    on_hold_employees = [i for i in on_hold_employees if not i.employee in basic_attendance_employees]

    basic_shift_assignments = frappe.get_all("Shift Assignment", filters={
        'start_date':start_date, 
        'end_date': end_date,
        'roster_type':'Basic', 'docstatus':1
    }, fields="*")
    basic_shift_assignments = [i for i in basic_shift_assignments if not i.employee in basic_attendance_employees]
    
    basic_in_checkins = frappe.db.sql(f""" 
        SELECT name, owner, creation, modified, modified_by, docstatus, idx, employee, 
        employee_name, log_type, late_entry, early_exit, time, date, skip_auto_attendance, 
        shift_actual_start, shift_actual_end, shift_assignment, operations_shift, shift_type,
        roster_type, operations_site, project, company, operations_role, post_abbrv,
        shift_permission, actual_time, MIN(time) as time  FROM `tabEmployee Checkin` 
        WHERE 
        roster_type='Basic' AND log_type='IN' AND
        shift_actual_start BETWEEN '{start_date} 00:00:00' AND '{start_date} 23:59:59' 
        AND shift_actual_end BETWEEN '{end_date} 00:00:00' AND '{end_date} 23:59:59' 
        GROUP BY employee
        ORDER BY employee
    """, as_dict=1)
    basic_in_checkins = [i for i in basic_in_checkins if not i.employee in basic_attendance_employees]
    
    basic_out_checkins = frappe.db.sql(f""" 
        SELECT name, owner, creation, modified, modified_by, docstatus, idx, employee, 
        employee_name, log_type, late_entry, early_exit, time, date, skip_auto_attendance, 
        shift_actual_start, shift_actual_end, shift_assignment, operations_shift, shift_type, 
        roster_type, operations_site, project, company, operations_role, post_abbrv,
        shift_permission, actual_time, MAX(time) as time  FROM `tabEmployee Checkin` 
        WHERE 
        roster_type='Basic' AND log_type='OUT' AND
        shift_actual_start BETWEEN '{start_date} 00:00:00' AND '{start_date} 23:59:59' 
        AND shift_actual_end BETWEEN '{end_date} 00:00:00' AND '{end_date} 23:59:59' 
        GROUP BY employee
        ORDER BY employee
    """, as_dict=1)
    basic_out_checkins = [i for i in basic_out_checkins if not i.employee in basic_attendance_employees]
    
    # create On Hold Attendance 
    if on_hold_employees:
        for i in on_hold_employees:
            name = f"HR-ATT_{start_date}_{i.employee}_Basic"
            emp = employees_dict.get(i.employee)
            query_body+= f"""
                (
                    "{name}", "{naming_series}","{i.employee}", "{i.employee_name}", 0, "On Hold", '{i.shift_type}', NULL,
                    NULL, "{i.name}", "{i.shift}", "{i.site}", "{i.project}", "{start_date}", "{emp.company}",
                    "{emp.department}", 0, 0, "{i.operations_role}", "{i.post_abbrv}", "{i.roster_type}", {1}, "{owner}",
                    "{owner}", "{creation}", "{creation}", "Attendance By Client"
                ),"""
            basic_attendance_employees.append(i.employee)

    if holiday_attendance_employee:
        print(len(holiday_attendance_employee))
        for i in holiday_attendance_employee:
            name = f"HR-ATT_{start_date}_{i.name}_Basic"
            emp = employees_dict.get(i.name)
            query_body+= f"""
                (
                    "{name}", "{naming_series}","{i.name}", "{i.employee_name}", 0, "Holiday", '', NULL,
                    NULL, "", "", "", "", "{start_date}", "{emp.company}",
                    "{i.department}", 0, 0, "", "", "Basic", {1}, "{owner}",
                    "{owner}", "{creation}", "{creation}", "{i.description}"
                ),"""
            basic_attendance_employees.append(i.employee)

    # create BASIC DAY OFF
    for i in basic_employee_schedules:
        if i.employee_availability == "Day Off" and getdate(start_date) == getdate(i.date):
            emp = employees_dict.get(i.employee)
            query_body+= f"""
            (
                "HR-ATT_{start_date}_{i.employee}_Basic", "{naming_series}" , "{i.employee}", "{emp.employee_name}", 0, "Day Off", '', NULL,
                NULL, "", "", "", "", "{start_date}", "{emp.company}",
                "{emp.department}", 0, 0, "", "", "Basic", 1, "{owner}",
                "{owner}", "{creation}", "{creation}", "Employee Schedule - {i.name}"
            ),"""
            basic_attendance_employees.append(i.employee)
    
    # Day Off from Holiday list.
    day_off_attendance_employee = [i for i in day_off_employee if not i.employee in basic_attendance_employees]
    if day_off_attendance_employee:
        for i in day_off_attendance_employee:
            name = f"HR-ATT_{start_date}_{i.name}_Basic"
            emp = employees_dict.get(i.name)
            query_body+= f"""
                (
                    "{name}", "{naming_series}","{i.name}", "{i.employee_name}", 0, "Day Off", '', NULL,
                    NULL, "", "", "", "", "{start_date}", "{emp.company}",
                    "{i.department}", 0, 0, "", "", "Basic", {1}, "{owner}",
                    "{owner}", "{creation}", "{creation}", "{i.description}"
                ),"""
            basic_attendance_employees.append(i.employee)

    # update employees schedule and assignment list
    basic_employee_schedules = [i for i in basic_employee_schedules if not i.employee in basic_attendance_employees or i.employee_availability=='Working']
    basic_shift_assignments = [i for i in basic_shift_assignments if not i.employee in basic_attendance_employees]
    basic_in_checkins = [i for i in basic_in_checkins if not i.employee in basic_attendance_employees]
    basic_out_checkins = [i for i in basic_out_checkins if not i.employee in basic_attendance_employees]
    # mark checkins
    
    basic_in_checkins_dict = {}
    basic_out_checkins_dict = {}
    for i in basic_in_checkins:basic_in_checkins_dict[i.employee]=i
    for i in basic_out_checkins:basic_out_checkins_dict[i.employee]=i
    for i in basic_in_checkins:
        emp = employees_dict.get(i.employee)
        name = f"HR-ATT-{start_date}_{i.employee}_{i.roster_type}"
        checkin_attendance_link[name] = [i.name]
        late_entry = late_entry = i.late_entry
        early_exit = 0
        out_time = i.shift_actual_end
        comment = ""
        if ((i.time - i.shift_actual_start).total_seconds() / (60*60)) > 4:
            working_hours = 0
            status = 'Absent'
            comment = f"4 hours late, checked in at {i.time}"
            out_time = i.shift_actual_end
            if basic_out_checkins_dict.get(i.employee):
                out = basic_out_checkins_dict.get(i.employee)
                out_time = out.time
                checkin_attendance_link[name].append(out.name)
        elif basic_out_checkins_dict.get(i.employee):
            out = basic_out_checkins_dict.get(i.employee)
            working_hours = (out.time - i.time).total_seconds() / (60 * 60)
            status = 'Present'
            out_time = out.time
            early_exit = i.early_exit
            checkin_attendance_link[name].append(out.name)
        else:
            working_hours = (i.shift_actual_end - i.time).total_seconds() / (60 * 60)
            status = 'Present'
            comment = 'No checkout record found.'
            
        if not emp:
            emp = frappe._dict({})
        query_body+= f"""
        (
            "{name}", "{naming_series}", "{i.employee}", "{emp.employee_name or ''}", {working_hours}, "{status}", '{i.shift_type}', '{i.time}',
            '{out_time}', "{i.shift_assignment}", "{i.operations_shift}", "{i.operations_site}", "{i.project}", "{start_date}", "{i.company}",
            "{emp.department}", {late_entry}, {early_exit}, "{i.operations_role}", "{i.post_abbrv}", "{i.roster_type}", {1}, "{owner}",
            "{owner}", "{creation}", "{creation}", "{comment}"
        ),"""
        basic_attendance_employees.append(i.employee)
        new_attendances.append(name)
    # update schedules
    basic_employee_schedules = [i for i in basic_employee_schedules if not i.employee in basic_attendance_employees]
    basic_shift_assignments = [i for i in basic_shift_assignments if not i.employee in basic_attendance_employees]
    
    for i in basic_shift_assignments:
        emp = employees_dict.get(i.employee)
        name = f"HR-ATT_{start_date}_{i.employee}_Basic"
        query_body+= f"""
        (
            "{name}", "{naming_series}", "{i.employee}", "{i.employee_name}", 0, "Absent", '{i.shift_type}', NULL,
            NULL, "{i.name}", "{i.shift}", "{i.site}", "{i.project}", "{start_date}", "{i.company}",
            "{emp.department}", 0, 0, "{i.operations_role}", "{i.post_abbrv}", "{i.roster_type}", {1}, "{owner}",
            "{owner}", "{creation}", "{creation}", "No attendance record found"
        ),"""
        new_attendances.append(name)


    ### DO SAME FOR OVERTIME
    ot_attendances = frappe.db.get_all("Attendance", filters={
        'attendance_date':['BETWEEN', [start_date, end_date]],
        'roster_type':'Over-Time'
    }, fields="*")
    ot_attendance_employees = [i.employee for i in ot_attendances]

    ot_employee_schedules = frappe.get_all("Employee Schedule", filters={
        'date':["BETWEEN", [start_date, end_date]],
        'roster_type':'Over-Time', 'employee_availability':'Working'
    }, fields="*")
    ot_employee_schedules = [i for i in ot_employee_schedules if not i.employee in ot_attendance_employees]
    
    ot_shift_assignments = frappe.get_all("Shift Assignment", filters={
        'start_date':["BETWEEN", [start_date, end_date]],
        'roster_type':'Over-Time', 'docstatus':1
    }, fields="*")
    ot_shift_assignments = [i for i in ot_shift_assignments if not i.employee in ot_attendance_employees]
    
    ot_in_checkins = frappe.db.sql(f""" 
        SELECT name, owner, creation, modified, modified_by, docstatus, idx, employee, 
        employee_name, log_type, late_entry, early_exit, time, date, skip_auto_attendance, 
        shift_actual_start, shift_actual_end, shift_assignment, operations_shift, shift_type,
        roster_type, operations_site, project, company, operations_role, post_abbrv,
        shift_permission, actual_time, MIN(time) as time  FROM `tabEmployee Checkin` 
        WHERE 
        roster_type='Over-Time' AND log_type='IN' AND
        shift_actual_start BETWEEN '{start_date} 00:00:00' AND '{start_date} 23:59:59' 
        AND shift_actual_end BETWEEN '{end_date} 00:00:00' AND '{end_date} 23:59:59' 
        GROUP BY employee
        ORDER BY employee
    """, as_dict=1)
    ot_in_checkins = [i for i in ot_in_checkins if not i.employee in ot_attendance_employees]
    
    ot_out_checkins = frappe.db.sql(f""" 
        SELECT name, owner, creation, modified, modified_by, docstatus, idx, employee, 
        employee_name, log_type, late_entry, early_exit, time, date, skip_auto_attendance, 
        shift_actual_start, shift_actual_end, shift_assignment, operations_shift, shift_type,
        roster_type, operations_site, project, company, operations_role, post_abbrv,
        shift_permission, actual_time, MAX(time) as time  FROM `tabEmployee Checkin` 
        WHERE 
        roster_type='Over-Time' AND log_type='OUT' AND
        shift_actual_start BETWEEN '{start_date} 00:00:00' AND '{start_date} 23:59:59' 
        AND shift_actual_end BETWEEN '{end_date} 00:00:00' AND '{end_date} 23:59:59' 
        GROUP BY employee
        ORDER BY employee
    """, as_dict=1)
    ot_out_checkins = [i for i in ot_out_checkins if not i.employee in ot_attendance_employees]
    
    # mark checkins
    
    ot_in_checkins_dict = {}
    ot_out_checkins_dict = {}
    for i in ot_in_checkins:ot_in_checkins_dict[i.employee]=i
    for i in ot_out_checkins:ot_out_checkins_dict[i.employee]=i
    for i in ot_in_checkins:
        emp = employees_dict.get(i.employee)
        name = f"HR-ATT-{start_date}_{i.employee}_{i.roster_type}"
        checkin_attendance_link[name] = [i.name]
        late_entry = i.late_entry
        early_exit = 0
        out_time = i.shift_actual_end
        comment = ""
        if ((i.time - i.shift_actual_start).total_seconds() / (60*60)) > 4:
            working_hours = 0
            status = 'Absent'
            comment = f"4 hours late, checked in at {i.time}"
            late_entry = i.late_entry
            out_time = i.shift_actual_end
            if basic_out_checkins_dict.get(i.employee):
                out = basic_out_checkins_dict.get(i.employee)
                out_time = out.time
                checkin_attendance_link[name].append(out.name)
        elif basic_out_checkins_dict.get(i.employee):
            out = basic_out_checkins_dict.get(i.employee)
            working_hours = (out.time - i.time).total_seconds() / (60 * 60)
            status = 'Present'
            out_time = out.time
            early_exit = i.early_exit
            checkin_attendance_link[name].append(out.name)
        else:
            working_hours = (i.shift_actual_end - i.time).total_seconds() / (60 * 60)
            status = 'Present'
            comment = 'No checkout record found.'
        query_body+= f"""
        (
            "{name}", "{naming_series}", "{i.employee}", "{emp.employee_name}", {working_hours}, "{status}", '{i.shift_type}', '{i.time}',
            '{out_time}', "{i.shift_assignment}", "{i.operations_shift}", "{i.operations_site}", "{i.project}", "{start_date}", "{i.company}",
            "{emp.department}", {late_entry}, {early_exit}, "{i.operations_role}", "{i.post_abbrv}", "{i.roster_type}", {1}, "{owner}",
            "{owner}", "{creation}", "{creation}", "{comment}"
        ),"""
        ot_attendance_employees.append(i.employee)
        new_attendances.append(name)
    # update schedules
    ot_employee_schedules = [i for i in ot_employee_schedules if not i.employee in ot_attendance_employees]
    ot_shift_assignments = [i for i in ot_shift_assignments if not i.employee in ot_attendance_employees]
    
    for i in ot_shift_assignments:
        emp = employees_dict.get(i.employee)
        name = f"HR-ATT_{start_date}_{i.employee}_Basic"
        query_body+= f"""
        (
            "{name}", "{naming_series}", "{i.employee}", "{i.employee_name}", 0, "Absent", '{i.shift_type}', NULL,
            NULL, "{i.name}", "{i.shift}", "{i.site}", "{i.project}", "{start_date}", "{i.company}",
            "{emp.department}", 0, 0, "{i.operations_role}", "{i.post_abbrv}", "{i.roster_type}", {1}, "{owner}",
            "{owner}", "{creation}", "{creation}", "No attendance record found"
        ),"""
        new_attendances.append(name)

    # UPDATE QUERY
    if query_body:
        query += query_body[:-1]
        query += f"""
            ON DUPLICATE KEY UPDATE
            naming_series = VALUES(naming_series),
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
        frappe.db.sql(query, values=[], as_dict=1)
        frappe.db.commit()

        # update employee checkin
        frappe.enqueue(update_employee_checkin_with_attendance, attendance_dict=checkin_attendance_link, queue='long', timeout=6000)
        # update day_off_ot
        frappe.enqueue(update_day_off_ot, attendances=new_attendances, queue='long', timeout=6000)
        # remark missing
        frappe.enqueue(remark_attendance, start_date=start_date, end_date=end_date, queue='long', timeout=6000)
    # except Exception as e:
    #     frappe.log_error(frappe.get_traceback(), "Attendance Marking")    

def remark_attendance(start_date, end_date):
    try:
        shift_assignments = frappe.db.get_list("Shift Assignment", filters={
            'start_date':start_date, 'end_date':end_date},
            fields='name, employee'
        )
        attendances = frappe.db.get_list("Attendance", filters={
            'attendance_date':start_date, 'shift_assignment':['IN', [i.name for i in shift_assignments]],
            'docstatus':1},
            fields='name, employee'
        )
        missing_attendances = [i.employee for i in shift_assignments if not i.employee in [x.employee for x in attendances]] 
        for employee in missing_attendances:
            mark_bulk_attendance(employee, start_date, start_date)
    except:
        frappe.log_error(frappe.get_traceback(), 'Remark Attendance')


def update_employee_checkin_with_attendance(attendance_dict):
    for k, v in attendance_dict.items():
        for i in v:
            frappe.db.set_value("Employee Checkin", i, 'attendance', k)

def update_day_off_ot(attendances):
    for i in attendances:
        att = frappe.get_doc("Attendance", i)
        if att.shift_assignment:
            try:
                day_off_ot = frappe.db.get_value("Employee Schedule", {
                    'employee':att.employee,
                    'date':att.attendance_date,
                    'roster_type':att.roster_type
                }, 'day_off_ot')
                if day_off_ot:
                    att.db_set("day_off_ot", day_off_ot)
            except:
                frappe.log_error(frappe.get_traceback(), "Attendance Marking OT")   

def mark_open_timesheet_and_create_attendance():
    the_timesheet_list = frappe.db.get_list("Timesheet", filters={"workflow_state": "Open", "total_hours":[">",0]}, pluck="name")
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
