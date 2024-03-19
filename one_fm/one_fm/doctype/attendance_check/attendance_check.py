# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt
from datetime import datetime, timedelta
from itertools import chain

from frappe.model.document import Document
import frappe,json
from frappe import _
from frappe.desk.form.assign_to import add as add_assignment
from frappe.utils import nowdate, add_to_date, cstr, add_days, today, format_date, now, get_url_to_form
from one_fm.utils import (
    production_domain,
    fetch_attendance_manager_user,
    get_approver
)

class AttendanceCheck(Document):
    def before_insert(self):
        self.validate_duplicate()
        # Get shift assignment for the date and roster type
        shift_assignment = self.get_shift_assignment()
        # Set shift assignment to the attendance check
        if shift_assignment:
            self.shift_assignment = shift_assignment.name
            self.start_time = shift_assignment.start_datetime
            self.end_time = shift_assignment.end_datetime
            # Get checkin records for the
            checkins = self.get_checkins_details()
            # Set check in recods to attendance check
            if checkins and len(checkins)>0:
                self.checkin_record=checkins[0].in_name if checkins[0].in_name else ""
                self.checkout_record=checkins[0].out_name if checkins[0].out_name else ""

        attendance_request = self.get_attendance_request()
        if attendance_request and len(attendance_request)>0:
            self.attendance_request=attendance_request[0].name

        # Get shift permission
        shift_permission = self.get_shift_permission()
        # Set shift permission details
        if shift_permission:
            self.shift_permission = shift_permission.name
            self.has_shift_permissions = 1

        # Set approver
        self.set_attedance_check_approver()

    def validate_duplicate(self):
        attendance_exist = frappe.db.get_value(
            self.doctype,
            {
                'employee':self.employee,
                'date':self.date,
                'roster_type':self.roster_type
            },
            ["name", "workflow_state"],
            as_dict=1
        )
        if attendance_exist:
            msg = f"""Attendance Check already exist for {self.employee} on {self.date} with name {attendance_exist.name}"""
            frappe.throw(msg)

    def get_shift_assignment(self):
        return frappe.db.get_value(
            "Shift Assignment",
            {
                "employee":self.employee,
                "start_date":self.date,
                "roster_type":self.roster_type,
                "status":"Active",
                "docstatus":1
            },
            ["name", "start_date", "start_datetime", "end_datetime"],
            as_dict=1
        )

    def get_checkins_details(self):
        return frappe.db.sql(f"""
            SELECT
                MIN(CASE WHEN ec.log_type = 'IN' THEN ec.name END) AS in_name,
                MAX(CASE WHEN ec.log_type = 'OUT' THEN ec.name END) AS out_name
            FROM
                `tabEmployee Checkin` ec
            WHERE
                ec.shift_assignment="{self.shift_assignment}"
            GROUP BY
                ec.shift_assignment;
        """, as_dict=1)

    def get_attendance_request(self):
        return frappe.db.sql(f"""
            select
                name
            from
                `tabAttendance Request`
            where
                '{self.date}'
                between
                from_date
                and
                to_date
                and
                docstatus=1
        """, as_dict=1)

    def get_shift_permission(self):
        return frappe.db.get_value(
            "Shift Permission",
            {
                "employee":self.employee,
                "date":self.date,
                "roster_type":self.roster_type,
                "docstatus":["!=", 0]
            },
            ["name"],
            as_dict=1
        )

    def set_attedance_check_approver(self):
        employee = frappe.db.get_value(
            "Employee",
            {"name": self.employee},
            ["reports_to", "shift", "site"],
            as_dict=1
        )
        if employee.reports_to:
            self.reports_to = employee.reports_to
        if employee.shift:
            shift_supervisor = frappe.db.get_value('Operations Shift', employee.shift, 'supervisor')
            self.shift_supervisor = shift_supervisor
        if employee.site:
            site_supervisor = frappe.db.get_value('Operations Site', employee.site, 'account_supervisor')
            self.site_supervisor = site_supervisor

    def validate(self):
        self.validate_justification()

    def validate_justification(self):
        # The method is used to validate the justification and its dependend fields
        if self.attendance_status == 'Present':
            if not self.justification:
                frappe.throw("Please select Justification")

            if self.justification == "Other":
                if not self.other_reason:
                    frappe.throw("Please write the other Reason")
            else:
                self.other_reason = ""

            if self.justification == "Mobile isn't supporting the app":
                if not self.mobile_brand:
                    frappe.throw("Please select mobile brand")
                if not self.mobile_model:
                    frappe.throw("Please Select Mobile Model")
            else:
                self.mobile_brand = ""
                self.mobile_model = ""

            if self.justification in ["Invalid media content","Out-of-site location", "User not assigned to shift"]:
                if not self.screenshot:
                    frappe.throw("Please Attach ScreenShot")
            else:
                self.screenshot = ""
        else:
            self.justification = ""

        if self.justification == "Approved by Administrator" and not check_attendance_manager(email=frappe.session.user):
            frappe.throw("Only the Attendance manager can select 'Approved by Administrator' ")


    def validate_unscheduled_check(self):
        #If Check is unscheduled,confirmed user roles before submitting
        if self.is_unscheduled:
            if check_attendance_manager(frappe.session.user):
                return
            elif "Shift Supervisor" in frappe.get_roles(frappe.session.user) or "Site Supervisor" in frappe.get_roles(frappe.session.user):
                shift_assignments = frappe.db.get_list("Shift Assignment", filters={'docstatus':1,'start_date':self.date,'employee':self.employee}, fields="*")
                if not shift_assignments:
                    frappe.throw(f"No Shift Assignments found for {self.employee_name} on {self.date} Please create one")
            else:
                frappe.throw("Only Shift/Site Supervisors and Attendance Managers have permission to submit unscheduled Attendance Checks")

    def on_submit(self):
        shift_working = frappe.db.get_value("Employee", self.employee, "shift_working")
        if self.attendance_status == "Present" and shift_working:
            self.validate_unscheduled_check()
        if self.attendance_status == "On Leave":
            self.check_on_leave_record()
        if self.attendance_status == "Day Off" and shift_working:
            validate_day_off(self,convert=0)
        self.validate_justification_and_attendance_status()
        self.mark_attendance()

    def mark_attendance(self):
        if self.workflow_state == 'Approved':
            attendance = self.get_existing_attendance()
            if attendance and len(attendance)>0:
                self.update_existing_attendance_record(attendance)
            else:
                self.create_new_attendance_record()

    def get_existing_attendance(self):
        return frappe.db.get_value(
            "Attendance",
            {
                "attendance_date": self.date,
                "employee": self.employee,
                "docstatus": ["<", 2],
                "roster_type":self.roster_type
            },
            ["status", "name"],
            as_dict=1
        )

    def update_existing_attendance_record(self, attendance):
        if attendance.status == "Absent" and self.attendance_status in ["Present", "Day Off", "On Leave"]:
            working_hours = self.get_shift_working_hours(self.shift_assignment)
            frappe.db.sql(f"""
                update
                    `tabAttendance`
                set
                    status = '{self.attendance_status}',
                    reference_doctype='{self.doctype}',
                    reference_docname='{self.name}',
                    modified='{str(now())}',
                    working_hours={working_hours},
                    modified_by='{frappe.session.user}',
                    comment="Created from Attendance Check"
                where
                    name = '{attendance.name}'
            """)
            frappe.db.commit()

    def create_new_attendance_record(self):
        attendance = frappe.new_doc("Attendance")
        attendance.employee = self.employee
        attendance.employee_name = self.employee_name
        attendance.attendance_date = self.date
        attendance.status = self.attendance_status
        attendance.roster_type = self.roster_type
        attendance.reference_doctype = self.doctype
        attendance.reference_docname = self.name
        attendance.comment = "Created from Attendance Check"

        if not frappe.db.get_value("Employee", self.employee, "attendance_by_timesheet"):
            # Set shift assignmet to attendance recod
            if self.shift_assignment:
                attendance.shift_assignment = self.shift_assignment
            else:
                shift_assignment = frappe.db.exists("Shift Assignment", {
                        'employee':self.employee, 'start_date':self.date, 'roster_type':self.roster_type
                    })
                if shift_assignment:
                    attendance.shift_assignment = shift_assignment

            if attendance.shift_assignment and attendance.status=='Present':
                attendance.working_hours = self.get_shift_working_hours(attendance.shift_assignment)
        if not attendance.working_hours and attendance.status != 'Day Off':
            attendance.working_hours = 8 if self.attendance_status == 'Present' else 0
        attendance.insert(ignore_permissions=True)
        attendance.submit()

    def get_shift_working_hours(self, shift_assignment=False):
        working_hours=0
        if shift_assignment:
            shift = frappe.db.get_value("Shift Assignment", shift_assignment, 'shift')
            if shift:
                working_hours = frappe.db.get_value("Operations Shift", shift, 'duration')
        else:
            working_hours = 8 if self.attendance_status == 'Present' else 0
        return working_hours

    def validate_justification_and_attendance_status(self):
        if not self.attendance_status:
            frappe.throw(_('To Approve the record set Attendance Status'))

    def check_on_leave_record(self):
        submited_leave_record = frappe.db.sql(f"""SELECT leave_type
            FROM `tabLeave Application`
            WHERE employee = '{self.employee}'
                AND '{self.date}' >= from_date AND '{self.date}' <= to_date
                AND workflow_state = 'Approved'
                AND docstatus = 1
        """,as_dict=True)

        if  submited_leave_record:
            return
        else:
            draft_leave_records = frappe.db.sql(f"""select employee_name,leave_approver_name,name
                FROM `tabLeave Application`
                WHERE employee = '{self.employee}'
                    AND '{self.date}' >= from_date AND '{self.date}' <= to_date
                    AND docstatus = 0
            """,as_dict=True)
            if draft_leave_records:
                doc_url = get_url_to_form('Leave Application',draft_leave_records[0].get('name'))
                error_template = frappe.render_template('one_fm/templates/emails/attendance_check_alert.html',context={'doctype':'Leave Application','current_user':frappe.session.user,'date':self.date,'approver':draft_leave_records[0].get('leave_approver_name'),'page_link':doc_url,'employee_name':self.employee_name})
                frappe.throw(error_template)
            else:
                frappe.throw(f"""
                <p>Please note that a Leave Application has not been created for <b>{self.employee_name}</b>.</p>
                <hr>
                To create a leave application <a class="btn btn-primary btn-sm" href="{frappe.utils.get_url('/app/leave-application/new-leave-application-1')}?doc_id={self.name}&doctype={self.doctype}" target="_blank" onclick=" ">Click Here</a>
                 """)

def create_attendance_check(attendance_date=None):
    if production_domain():
        if not attendance_date:
            attendance_date = add_days(today(), -1)

        # Create attendance check for absentees for the date
        absentees = get_absentees_on_date(attendance_date)
        insert_attendance_check_records(absentees, attendance_date)

        # Create attendance check for employee who is shift working but no attendance marked on the date
        attendance_not_marked_shift_employees = get_attendance_not_marked_shift_employees(attendance_date)
        if attendance_not_marked_shift_employees:
            insert_attendance_check_records(attendance_not_marked_shift_employees, attendance_date, True)

def get_absentees_on_date(attendance_date):
    return frappe.get_all("Attendance",
        filters={
            'docstatus': 1,
            'status': 'Absent',
            'attendance_date': attendance_date
        },
        fields=[
            "employee",
            "roster_type",
            "name as attendance",
            "comment as attendance_comment",
            "shift_assignment",
            "status as attendance_status"
        ]
    )

def get_attendance_not_marked_shift_employees(attendance_date):
    # Fetch the list of employees, attendance marked for the date and basic roster
    attendance_list = frappe.db.get_list("Attendance",
        filters={
            "attendance_date": attendance_date,
            "roster_type": "Basic",
            "status": ["not in", ["Absent"]],
            "docstatus": 1
        },
        fields=["employee"]
    )
    employees = [attendance.employee for attendance in attendance_list]

    # Fetch all the employees who is shift working but no attendance marked
    return frappe.db.get_list("Employee",
        filters={
            "shift_working":1,
            "status":"Active",
            "name": ["not in", employees],
            "date_of_joining": ["<=", attendance_date]
        },
        fields=["name as employee"]
    )

def insert_attendance_check_records(details, attendance_date, is_unscheduled=False):
    for count, data in enumerate(details):
        try:
            attendance_by_timesheet = False
            if not is_unscheduled:
                attendance_by_timesheet = frappe.db.get_value("Employee", data["employee"], "attendance_by_timesheet")
            filters = {
                "doctype": "Attendance Check",
                "employee": data["employee"],
                "date": attendance_date,
                "attendance": data["attendance"] if "attendance" in data else "",
                "roster_type": data["roster_type"] if "roster_type" in data else "Basic",
                'is_unscheduled': is_unscheduled,
                "attendance_by_timesheet": attendance_by_timesheet,
                "marked_attendance_status": data["attendance_status"] if "attendance_status" in data else "",
                "shift_assignment": data["shift_assignment"] if "shift_assignment" in data else "",
                "attendance_marked": 1 if "attendance" in data else 0,
                "comment": data["attendance_comment"] if "attendance_comment" in data else ""
            }
            doc = frappe.get_doc(filters).insert(ignore_permissions=1)
        except Exception as e:
            if not "Attendance Check already exist for" in str(e):
                frappe.log_error(message=frappe.get_traceback(), title="Attendance Check Creation")
        if count%10==0:
            frappe.db.commit()
    frappe.db.commit()

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
                frappe.db.set_value("Employee Checkin", i.checkout_record, "attendance", att.name)
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), 'Attendance Remark')

@frappe.whitelist()
def check_attendance_manager(email: str) -> bool:
    return frappe.db.get_value("Employee", {"user_id": email}) == frappe.db.get_single_value("ONEFM General Setting", "attendance_manager")


@frappe.whitelist()
def validate_day_off(form,convert=1):
    # Validates the existence of a shift request when the attendance status of the attendance
    doc = json.loads(form) if convert else form
    if doc.get('attendance_status') == "Day Off":
        #check if shift request for that day exists
        query = f"Select name from `tabShift Request` where docstatus = 1 and assign_day_off = 1 and  employee = '{doc.get('employee')}' and from_date <= '{doc.get('date')}'  and to_date >='{doc.get('date')}'"
        submited_result_set = frappe.db.sql(query,as_dict=1)
        if submited_result_set:
            return
        else:
            draft_query =  f"Select name,approver from `tabShift Request` where docstatus = 0 and assign_day_off = 1 and  employee = '{doc.get('employee')}' and from_date <= '{doc.get('date')}'  and to_date >='{doc.get('date')}'"
            drafts_result_set = frappe.db.sql(draft_query,as_dict=1)
            if drafts_result_set:


                doc_url = get_url_to_form('Shift Request',drafts_result_set[0].get('name'))
                approver_full_name = frappe.db.get_value("User",drafts_result_set[0].get('approver'),'full_name')
                error_template = frappe.render_template('one_fm/templates/emails/attendance_check_alert.html',context={'doctype':'Shift Request','current_user':frappe.session.user,'date':doc.date,'approver':approver_full_name,'page_link':doc_url,'employee_name':doc.employee_name})
                frappe.throw(error_template)
            else:
                #cancelled or shift request not created at all
                frappe.throw(f"""
                <p>Please note that a shift request has not been created for <b>{doc.employee_name}</b> on <b>{doc.date}</b>..</p>
                <hr>
                 To create a Shift Request <a class="btn btn-primary btn-sm" href="{frappe.utils.get_url('/app/shift-request/new-shift-request-1')}?doc_id={doc.name}&doctype={doc.doctype}" target="_blank" onclick=" ">Click Here</a>
                 """)

def attendance_check_pending_approval_check():
    pending_approval_attendance_checks = get_pending_approval_attendance_check(48)
    if pending_approval_attendance_checks and len(pending_approval_attendance_checks)>0:
        # Issue Penalty to the assigned approver
        issue_penalty_to_the_assigned_approver(pending_approval_attendance_checks)
        # Assign the attendance checks to attendance manager for approval
        assign_attendance_manager(pending_approval_attendance_checks)

def get_pending_approval_attendance_check(hours):
    # Method to get list of attendance check, which is in panding approval state after a given hours
    date_time = datetime.strptime(now(), '%Y-%m-%d %H:%M:%S.%f') - timedelta(hours=hours)
    return frappe.db.sql("""
        select
            name, _assign as assign_to
        from
            `tabAttendance Check`
        where
            creation <= %s
            and
            docstatus = 0
            and
            TIME(creation) <= %s
    """, (date_time, date_time.time()), as_dict=1)

def issue_penalty_to_the_assigned_approver(pending_approval_attendance_checks):
    approvers = {}
    for pending_approval_attendance_check in pending_approval_attendance_checks:
        pending_approval_attendance_check = frappe.parse_json(pending_approval_attendance_check)
        if "assign_to" in pending_approval_attendance_check:
            assign_to = frappe.parse_json(pending_approval_attendance_check.assign_to)
            if assign_to and len(assign_to) > 0:
                if assign_to[0] in approvers:
                    approvers[assign_to[0]] += ", "+pending_approval_attendance_check.name
                else:
                    approvers[assign_to[0]] = pending_approval_attendance_check.name

    penalty_type = frappe.db.get_single_value("ONEFM General Setting", "att_check_approver_penalty_type")
    for approver in approvers:
        note = "There are attendance check not approved "+approvers[approver]
        approver_employee = frappe.db.get_values(
            "Employee",
            {"user_id": approver},
            ['name', 'employee_name', 'designation'],
            as_dict=True
        )
        if approver_employee and len(approver_employee)>0:
            penalty = frappe.get_doc({
                "doctype": "Penalty",
                "penalty_issuance_time": now(),
                "recipient_employee": approver_employee[0].name,
                "recipient_name": approver_employee[0].employee_name,
                "recipient_designation": approver_employee[0].designation,
                "recipient_user": approver,
            })
            penalty_details = penalty.append("penalty_details")
            penalty_details.penalty_type = penalty_type
            penalty_details.exact_notes = note
            penalty.save(ignore_permissions=True)

def assign_attendance_manager(pending_approval_attendance_checks):
    attendance_manager_user = fetch_attendance_manager_user()
    if attendance_manager_user:
        for pending_approval_attendance_check in pending_approval_attendance_checks:
            add_assignment({
                'doctype': "Attendance Check",
                'name': pending_approval_attendance_check.name,
                'assign_to': [attendance_manager_user],
            })
        frappe.db.commit()

def check_for_missed(date,schedules,shift_assignments,attendance_requests,all_attendance,checks_to_create):
    all_leaves = frappe.db.sql(f"""SELECT name,employee
        FROM `tabLeave Application`
            Where '{date}' >= from_date AND '{date}' <= to_date
            AND workflow_state = 'Approved'
            AND docstatus = 1
    """,as_dict=True)
    all_shifts_query = f"""Select employee from `tabShift Request` where docstatus = 1 and
    from_date <= '{date}'  and to_date >='{date}'"""
    all_leave_employees = [i.employee for i in all_leaves]
    all_shifts = frappe.db.sql(all_shifts_query,as_dict = 1)
    shift_request_employees = [i.employee for i in all_shifts]
    schedule_employees = [i.employee for i in schedules]
    shift_assignments_employees = [i.employee for i in shift_assignments]
    attendance_requests_employees = [i.employee for i in attendance_requests]
    all_attendance_employees = [i.employee for i in all_attendance]
    merged = shift_request_employees+schedule_employees+shift_assignments_employees+\
            all_attendance_employees+attendance_requests_employees+checks_to_create+all_leave_employees
    merged_set  = set(merged) #Remove Duplicates
    merged_tuple = tuple(merged_set)
    if len(merged_tuple) == 1:
        single_employee = merged_tuple[0]
        employees_with_no_docs_query = f""" SELECT name from `tabEmployee` where status = 'Active' AND date_of_joining <= '{date}' AND shift_working = 1 and name = {single_employee}
                                        """

    #Employees with no shift,schedule,leaves etc
    else:
         employees_with_no_docs_query = f""" SELECT name from `tabEmployee` where status = 'Active' AND date_of_joining <= '{date}' and shift_working = 1 and name not in {merged_tuple}
                                            """
    result_set = frappe.db.sql(employees_with_no_docs_query,as_dict=1)
    return [i.name for i in result_set] if result_set else []


def schedule_attendance_check():
    frappe.enqueue(create_attendance_check, queue='long', timeout=7000)
