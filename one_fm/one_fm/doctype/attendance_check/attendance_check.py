# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt
from datetime import datetime, timedelta

from frappe.model.document import Document
import frappe,json
from frappe import _
from frappe.desk.form.assign_to import add as add_assignment
from frappe.utils import add_days, today, now, get_url_to_form, getdate
from one_fm.utils import (
    production_domain,
    fetch_attendance_manager_user
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
        self.validate_is_replaced_shift_assignment()
        self.validate_justification()

    def validate_is_replaced_shift_assignment(self):
        if self.attendance_status and self.attendance_status != "Absent" and self.shift_assignment:
            if frappe.db.get_value("Shift Assignment", self.shift_assignment, "is_replaced") == 1:
                frappe.throw(_(f"{self.employee_name} was replaced for this shift and cannot be marked present."))

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

    def on_submit(self):
        if not self.attendance_status:
            frappe.throw(_('To Approve the record set Attendance Status'))
        shift_working = frappe.db.get_value("Employee", self.employee, "shift_working")
        if self.attendance_status == "On Leave":
            self.check_on_leave_record()
        if self.attendance_status == "Day Off" and shift_working:
            self.validate_day_off()
        self.mark_attendance()

    def check_on_leave_record(self):
        if self.attendance_status == "On Leave":
            draft_leave_records = self.get_draft_leave_records()
            if draft_leave_records and len(draft_leave_records) > 0:
                doc_url = get_url_to_form('Leave Application',draft_leave_records[0].get('name'))
                error_template = frappe.render_template(
                    'one_fm/templates/emails/attendance_check_alert.html',
                    context={
                        'doctype':'Leave Application',
                        'current_user':frappe.session.user,
                        'date':self.date,
                        'approver':draft_leave_records[0].get('leave_approver_name'),
                        'page_link':doc_url,
                        'employee_name':self.employee_name
                    }
                )
                frappe.throw(error_template)
            else:
                link_to_new_leave = frappe.utils.get_url('/app/leave-application/new-leave-application-1')
                frappe.throw(f"""
                    <p>Please note that a Leave Application has not been created for <b>{self.employee_name}</b>.</p>
                    <hr>
                    To create a leave application
                    <a class="btn btn-primary btn-sm"
                    href='{link_to_new_leave}?doc_id={self.name}&doctype={self.doctype}'
                    target="_blank" onclick=" ">
                        Click Here
                    </a>
                 """)

    def get_draft_leave_records(self):
        return frappe.db.sql(f"""
            select
                employee_name, leave_approver_name, name
            from
                `tabLeave Application`
            where
                employee = '{self.employee}'
                and
                '{self.date}' >= from_date
                and
                '{self.date}' <= to_date
                and
                docstatus = 0
            """,
            as_dict=True
        )

    def validate_day_off(self):
        if self.attendance_status == "Day Off":
            # Check if shift request for that day exists
            draft_shift_request = self.get_draft_shift_request()
            if draft_shift_request and len(draft_shift_request) > 0:
                doc_url = get_url_to_form('Shift Request',draft_shift_request[0].get('name'))
                approver_full_name = frappe.db.get_value("User",draft_shift_request[0].get('approver'), 'full_name')
                error_template = frappe.render_template(
                    "one_fm/templates/emails/attendance_check_alert.html",
                    context={
                        "doctype":"Shift Request",
                        "current_user":frappe.session.user,
                        "date":self.date,
                        "approver":approver_full_name,
                        "page_link":doc_url,
                        "employee_name":self.employee_name
                    }
                )
                frappe.throw(error_template)
            else:
                # Cancelled or shift request not created at all
                link_to_new_shift_request = frappe.utils.get_url('/app/shift-request/new-shift-request-1')
                frappe.throw(f"""
                    <p>
                        Please note that a shift request has not been created for
                        <b>{self.employee_name}</b> on <b>{self.date}</b>
                    </p>
                    <hr>
                    To create a Shift Request
                    <a class="btn btn-primary btn-sm"
                    href='{link_to_new_shift_request}?doc_id={self.name}&doctype={self.doctype}'
                    target="_blank" onclick=" ">
                        Click Here
                    </a>
                 """)

    def get_draft_shift_request(self):
        return frappe.db.sql(f"""
            select
                name,approver
            from
                `tabShift Request`
            where
                docstatus = 0
                and
                employee = '{self.employee}'
                and
                from_date <= '{self.date}'
                and
                to_date >='{self.date}'
            """,
            as_dict=1
        )

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

def create_attendance_check(attendance_date=None):
    if production_domain():
        if not attendance_date:
            attendance_date = add_days(today(), -1)
        attendance_date = getdate(attendance_date)

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
            
            doc = frappe.get_doc(filters)
            doc.flags.ignore_mandatory = 1
            doc.insert(ignore_permissions=1)
        except Exception as e:
            if not "Attendance Check already exist for" in str(e):
                frappe.log_error(message=frappe.get_traceback(), title="Attendance Check Creation")
        if count%10==0:
            frappe.db.commit()
    frappe.db.commit()

@frappe.whitelist()
def check_attendance_manager(email: str) -> bool:
    return frappe.db.get_value("Employee", {"user_id": email}) == frappe.db.get_single_value("ONEFM General Setting", "attendance_manager")

def attendance_check_pending_approval_check():
    pending_approval_attendance_checks = get_pending_approval_attendance_check(48)
    if pending_approval_attendance_checks and len(pending_approval_attendance_checks) > 0:
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

def schedule_attendance_check():
    frappe.enqueue(create_attendance_check, queue='long', timeout=7000)
