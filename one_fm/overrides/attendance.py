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
        self.create_additional_salary_for_overtime()
        
    def validate_duplicate_record(self):
        duplicate = get_duplicate_attendance_record(
			self.employee, self.attendance_date, self.shift, self.roster_type, self.name
		)
        
        if duplicate:
            frappe.throw(
				_("Attendance for employee {0} is already marked for the date {1}: {2} : {3}").format(
					frappe.bold(self.employee),
					frappe.bold(self.attendance_date),
					get_link_to_form("Attendance", duplicate[0].name),
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


    def create_additional_salary_for_overtime(self):
        """
        This function creates an additional salary document for a given by specifying the salary component for overtime set in the HR and Payroll Additional Settings,
        by obtaining the details from Attendance where the roster type is set to Over-Time.

        The over time rate is fetched from the project which is linked with the shift the employee was working in.
        The over time rate is calculated by multiplying the number of hours of the shift with the over time rate for the project.

        In case of no overtime rate is set for the project, overtime rates are fetched from HR and Payroll Additional Settings.
        Amount is calucated and additional salary is created as:
        1. If employee has an existing basic schedule on the same day - working day rate is applied
        2. Working on a holiday of type "weekly off: - day off rate is applied.
        3. Working on a holiday of type non "weekly off" - public/additional holiday.

        Args:
            doc: The attendance document

        """
        roster_type_basic = "Basic"
        roster_type_overtime = "Over-Time"

        days_of_week = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

        # Check if attendance is for roster type: Over-Time
        if self.roster_type == roster_type_overtime:

            payroll_date = cstr(getdate())

            # Fetch payroll details from HR and Payroll Additional Settings
            overtime_component = frappe.db.get_single_value("HR and Payroll Additional Settings", 'overtime_additional_salary_component')
            working_day_overtime_rate = frappe.db.get_single_value("HR and Payroll Additional Settings", 'working_day_overtime_rate')
            day_off_overtime_rate = frappe.db.get_single_value("HR and Payroll Additional Settings", 'day_off_overtime_rate')
            public_holiday_overtime_rate = frappe.db.get_single_value("HR and Payroll Additional Settings", 'public_holiday_overtime_rate')

            # Fetch project and duration of the shift employee worked in operations shift
            project, overtime_duration = frappe.db.get_value("Operations Shift", self.operations_shift, ["project", "duration"])

            # Fetch overtime details from project
            project_has_overtime_rate, project_overtime_rate = frappe.db.get_value("Project", {'name': project}, ["has_overtime_rate", "overtime_rate"])

            # If project has a specified overtime rate, calculate amount based on overtime rate and create additional salary
            if project_has_overtime_rate:

                if project_overtime_rate > 0:
                    amount = round(project_overtime_rate * overtime_duration, 3)
                    notes = "Calculated based on overtime rate set for the project: {project}".format(project=project)

                    self.create_additional_salary(amount, overtime_component, notes)

                else:
                    frappe.throw(_("Overtime rate must be greater than zero for project: {project}".format(project=project)))

            # If no overtime rate is specified, follow labor law => (Basic Hourly Wage * number of worked hours * 1.5)
            else:
                # Fetch assigned shift, basic salary  and holiday list for the given employee
                assigned_shift, basic_salary, holiday_list = frappe.db.get_value("Employee", {'employee': self.employee}, ["shift", "one_fm_basic_salary", "holiday_list"])

                if assigned_shift:
                    # Fetch duration of the shift employee is assigned to
                    assigned_shift_duration = frappe.db.get_value("Operations Shift", assigned_shift, ["duration"])

                    if basic_salary and basic_salary > 0:
                        # Compute hourly wage
                        daily_wage = round(basic_salary/30, 3)
                        hourly_wage = round(daily_wage/assigned_shift_duration, 3)

                        # Check if a basic schedule exists for the employee and the attendance date
                        if frappe.db.exists("Employee Schedule", {'employee': self.employee, 'date': self.attendance_date, 'employee_availability': "Working", 'roster_type': roster_type_basic}):

                            if working_day_overtime_rate > 0:

                                # Compute amount as per working day rate
                                amount = round(hourly_wage * overtime_duration * working_day_overtime_rate, 3)
                                notes = "Calculated based on working day rate => (Basic hourly wage) * (Duration of worked hours) * {working_day_overtime_rate}".format(working_day_overtime_rate=working_day_overtime_rate)

                                self.create_additional_salary(amount, overtime_component, notes)

                            else:
                                frappe.throw(_("No Wroking Day overtime rate set in HR and Payroll Additional Settings."))

                        # Check if attendance date falls in a holiday list
                        elif holiday_list:

                            # Pass last parameter as "False" to get weekly off days
                            holidays_weekly_off = get_holidays_for_employee(self.employee, self.attendance_date, self.attendance_date, False, False)

                            # Pass last paramter as "True" to get non weekly off days, ie, public/additional holidays
                            holidays_public_holiday = get_holidays_for_employee(self.employee, self.attendance_date, self.attendance_date, False, True)

                            # Check for weekly off days length and if description of day off is set as one of the weekdays. (By default, description is set to a weekday name)
                            if len(holidays_weekly_off) > 0 and holidays_weekly_off[0].description in days_of_week:

                                if day_off_overtime_rate > 0:

                                    # Compute amount as per day off rate
                                    amount = round(hourly_wage * overtime_duration * day_off_overtime_rate, 3)
                                    notes = "Calculated based on day off rate => (Basic hourly wage) * (Duration of worked hours) * {day_off_overtime_rate}".format(day_off_overtime_rate=day_off_overtime_rate)

                                    self.create_additional_salary(amount, overtime_component, notes)

                                else:
                                    frappe.throw(_("No Day Off overtime rate set in HR and Payroll Additional Settings."))

                            # Check for weekly off days set to "False", ie, Public/additional holidays in holiday list
                            elif len(holidays_public_holiday) > 0:

                                if public_holiday_overtime_rate > 0:

                                    # Compute amount as per public holiday rate
                                    amount = round(hourly_wage * overtime_duration * public_holiday_overtime_rate, 3)
                                    notes = "Calculated based on day off rate => (Basic hourly wage) * (Duration of worked hours) * {public_holiday_overtime_rate}".format(public_holiday_overtime_rate=public_holiday_overtime_rate)

                                    self.create_additional_salary(amount, overtime_component, notes)

                                else:
                                    frappe.throw(_("No Public Holiday overtime rate set in HR and Payroll Additional Settings."))
                        else:
                            frappe.throw(_("No basic Employee Schedule or Holiday List found for employee: {employee}".format(employee=self.employee)))

                    else:
                        frappe.throw(_("Basic Salary not set for employee: {employee} in the employee record.".format(employee=self.employee)))

                else:
                    frappe.throw(_("Shift not set for employee: {employee} in the employee record.".format(employee=self.employee)))

    def create_additional_salary(self, amount, component, notes):
        """
        This function creates a document in the Additonal Salary doctype.

        Args:
            employee: employee code (eg: HR-EMP-0001)
            amount: amount to be considered in the additional salary
            component: type of component
            payroll_date: date that falls in the range during which this additional salary must be considered for payroll
            notes: Any additional notes

        Raises:
            exception e: Any internal server error
        """

        try:
            if not frappe.db.exists("Additional Assignment", {
                    'ref_doctype':self.doctype,
                    'ref_docname':self.name
                }):
                additional_salary = frappe.new_doc("Additional Salary")
                additional_salary.employee = self.employee
                additional_salary.salary_component = component
                additional_salary.amount = amount
                additional_salary.payroll_date = self.attendance_date
                additional_salary.company = erpnext.get_default_company()
                additional_salary.overwrite_salary_structure_amount = 1
                additional_salary.notes = notes
                additional_salary.ref_doctype = self.doctype
                additional_salary.ref_docname = self.name
                additional_salary.insert()
                additional_salary.submit()

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), 'Additional Salary')
            frappe.throw(_(str(e)))

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
