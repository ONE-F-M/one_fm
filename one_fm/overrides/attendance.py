import pandas as pd
import frappe
from frappe.utils import getdate, add_days
from hrms.hr.doctype.attendance.attendance import Attendance
from hrms.hr.utils import  validate_active_employee
from one_fm.api.tasks import get_holiday_today
from one_fm.operations.doctype.shift_permission.shift_permission import create_checkin as approve_shift_permission


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
        if not self.shift_assignment and self.status not in ['Absent', 'Day Off', 'Holiday', 'On Leave']:
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



@frappe.whitelist()
def mark_single_attendance(emp, att_date):
    # check if attendance exists
    #  get holiday, employee schedule, shift assignment, employee checkins
    if not frappe.db.exists("Attendance", {
        'employee': emp,
        'attendance_date':att_date,
        'status': ['!=', 'Absent'],
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

def mark_for_shift_assignment(employee, att_date):
    shift_assignment = frappe.db.get_value("Shift Assignment", {
        'employee':employee.name,
        'start_date':att_date,
        'roster_type':'Basic',
        'status':'Active',
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
            'employee':employee
            })
        )
        

        # working_hours = (out_time - in_time).total_seconds() / (60 * 60)


def create_single_attendance_record(record):
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
    doc.roster_type = 'Basic'
    if record.comment:
        doc.comment = record.comment
    
    if frappe.db.exists("Attendance", {
        'employee':doc.employee,
        'attendance_date':doc.attendance_date,
        }):
        frappe.db.sql(f"""
            DELETE FROM `tabAttendance` WHERE employee='{doc.employee}'
            AND attendance_date='{doc.attendance_date}'
        """)
    
    doc = frappe.get_doc(doc)
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
    date_range = pd.date_range(from_date, to_date)
    for i in date_range:
        mark_single_attendance(employee, i)

    frappe.msgprint(f"Marked Attendance successfully for {employee} between {from_date} and {to_date}")
