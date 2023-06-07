import pandas as pd
import frappe, erpnext
from frappe import _
from frappe.utils import getdate, add_days
from hrms.hr.doctype.attendance.attendance import *
from hrms.hr.utils import  validate_active_employee, get_holidays_for_employee
from one_fm.utils import get_holiday_today
from one_fm.operations.doctype.shift_permission.shift_permission import create_checkin as approve_shift_permission


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
        # condition = ''
        # if frappe.db.exists("Employee Schedule",
        #     {"employee": doc.employee, "date": doc.attendance_date, "roster_type": "Over-Time", "day_off_ot": True}):
        #     condition += ' day_off_ot="1"'
        # shift_assignment = frappe.get_list("Shift Assignment",{"employee": doc.employee, "start_date": doc.attendance_date},["name", "site", "project", "shift", "shift_type", "operations_role", "start_datetime","end_datetime", "roster_type"])
        # if shift_assignment and len(shift_assignment) > 0 :
        #     shift_data = shift_assignment[0]
        #     condition += """ shift_assignment="{shift_assignment[0].name}" """.format(shift_assignment=shift_assignment)

        #     for key in shift_assignment[0]:
        #         if shift_data[key] and key not in ["name","start_datetime","end_datetime", "shift", "shift_type"]:
        #             condition += """, {key}="{value}" """.format(key= key,value=shift_data[key])
        #         if key == "shift" and shift_data["shift"]:
        #             condition += """, operations_shift="{shift}" """.format(shift=shift_data["shift"])
        #         if key == "shift_type" and shift_data["shift_type"]:
        #             condition += """, shift='{shift_type}' """.format(shift_type=shift_data["shift_type"])

        #     if doc.attendance_request or frappe.db.exists("Shift Permission", {"employee": doc.employee, "date":doc.attendance_date,"workflow_state":"Approved"}):
        #         condition += """, in_time='{start_datetime}', out_time='{end_datetime}' """.format(start_datetime=cstr(shift_data["start_datetime"]), end_datetime=cstr(shift_data["end_datetime"]))
        # if condition:
        #     query = """UPDATE `tabAttendance` SET {condition} WHERE name= "{name}" """.format(condition=condition, name = doc.name)
        #     return frappe.db.sql(query)
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
