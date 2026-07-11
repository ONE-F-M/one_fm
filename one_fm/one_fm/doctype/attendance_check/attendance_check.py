# Copyright (c) 2023, ONE FM and contributors
# For license information, please see license.txt
from datetime import datetime, timedelta

from frappe.model.document import Document
from one_fm.processor import sendemail
import frappe,json
from frappe import _
from frappe.desk.form.assign_to import add as add_assignment
from frappe.utils import add_days, today, now, get_url_to_form, getdate
from one_fm.utils import (
    production_domain,
    fetch_attendance_manager_user,
    has_super_user_role,
    get_shift_supervisor,
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

        # Set site supervisor
        self.fetch_and_set_site_supervisor()

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
                employee = '{self.employee}'
                and
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



    
    def get_approver(self,employee):
        '''
            Method to get the line manager employee of an employee with the priority
            args:
                employee: name of Employee object
            return: employee reference of the line manager or None
        '''

        if not frappe.db.exists("Employee", {'name':employee}):
            frappe.log_error(title="Employee does not exists", message=f"Employee {employee} does not exists")
            return None

        employee_field_list = ["user_id", "reports_to", "shift", "site", "shift_working", "employee_name"]
        employee_data = frappe.db.get_value('Employee', employee, employee_field_list, as_dict=1)

        line_manager = employee_data.reports_to if employee_data.reports_to else None

        if not line_manager:
            if employee_data.user_id and has_super_user_role(employee_data.user_id):
                line_manager = employee

        if not line_manager:
            if employee_data.shift_working:
                if employee_data.site:
                    line_manager = frappe.db.get_value('Operations Site', employee_data.site, 'site_supervisor')
                if not line_manager and employee_data.shift:
                    line_manager = get_shift_supervisor(employee_data.shift,date=self.date)
                if not line_manager:
                    project = frappe.db.get_value('Operations Site', employee_data.site, 'project')
                    if project:
                        line_manager = frappe.db.get_value('Project', project, 'account_manager')
                if line_manager:
                    return line_manager
                
            else:
                if employee_data.site:
                    line_manager = frappe.db.get_value('Operations Site', employee_data.site, 'site_supervisor')

                if not line_manager and employee_data.shift:
                    line_manager = get_shift_supervisor(employee_data.shift,date=self.date)

                if not line_manager:
                    frappe.log_error(title="Missing Data", message=f"Please ensure that the Reports To or Operations Site Supervisor is set for {employee_data.employee_name}, Since the employee is not shift working")

        return line_manager

    def set_attedance_check_approver(self):
        approver = self.get_approver(self.employee)
        if approver:
            self.approver = frappe.db.get_value("Employee", approver, "user_id")

    def fetch_and_set_site_supervisor(self):
        site = None
        
        # 1. Try to get site from Shift Assignment
        if self.shift_assignment:
            site = frappe.db.get_value("Shift Assignment", self.shift_assignment, "site")
        
        # 2. Fallback to Employee Site Allocation
        if not site:
            site = frappe.db.get_value("Employee", self.employee, "site")
            
        if site:
            # Always set operations_site when a site is resolved
            self.operations_site = site

            # Conditionally set site supervisor details if available
            supervisor = frappe.db.get_value("Operations Site", site, "site_supervisor")
            if supervisor:
                self.site_supervisor = supervisor
                # self.site_supervisor_name will be auto-fetched or we can set it
                self.site_supervisor_name = frappe.db.get_value("Employee", supervisor, "employee_name")

    def after_insert(self):
        """
            Assign document to supervisors
        """
        pass


    def validate(self):
        self.validate_is_replaced_shift_assignment()
        self.validate_justification()
        self.set_action()

    def validate_is_replaced_shift_assignment(self):
        if self.attendance_status and self.attendance_status == "Present" and self.shift_assignment:
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

            if self.justification in ["Out-of-site location", "User not assigned to shift", "Forgot to check in"]:
                if not self.screenshot:
                    frappe.throw("Please Attach ScreenShot")
            else:
                self.screenshot = ""
        else:
            self.justification = ""

        if self.justification == "Approved by Administrator" and not check_attendance_manager(email=frappe.session.user):
            frappe.throw("Only the Attendance manager can select 'Approved by Administrator' ")

    def set_action(self):
        """Server-side logic to auto-populate the action field based on justification and verification answers."""
        if self.attendance_status != "Present" or not self.justification:
            self.action = ""
            return

        justification = self.justification

        if justification == "Forgot to check in":
            self.action = "Penalize the Employee"

        elif justification in ("Other", "Approved by Administrator"):
            self.action = "No Action Required"

        elif justification == "Out-of-site location":
            if self.is_the_employee_physically_onsite == "Yes":
                self.action = "Issue a New Mobile"
            elif self.is_the_employee_physically_onsite == "No":
                self.action = "Employee must check in at correct place"

        elif justification == "User not assigned to shift":
            if self.is_the_employee_assigned_to_the_correct_shift == "No":
                self.action = "Penalize the Supervisor"
            elif self.is_the_employee_assigned_to_the_correct_shift == "Yes":
                if self.did_the_employee_try_to_check_in_outside_working_hours == "Yes":
                    self.action = "Penalize the Employee"
                elif self.did_the_employee_try_to_check_in_outside_working_hours == "No":
                    self.action = "Raise Ticket to Helpdesk"

        elif justification == "Mobile isn't supporting the app":
            if self.is_the_mobile_specification_up_to_the_standard == "No":
                self.action = "Issue a New Mobile"
            elif self.is_the_mobile_specification_up_to_the_standard == "Yes":
                self.action = "Raise Ticket to Helpdesk"

        elif justification == "Application is missing geolocation permissions":
            if self.were_proper_permissions_given_to_the_app == "No":
                self.action = "Employee must correct app settings"
            elif self.were_proper_permissions_given_to_the_app == "Yes":
                self.action = "Issue a New Mobile"

    def on_submit(self):
        if not self.attendance_status:
            frappe.throw(_('To Approve the record set Attendance Status'))
        self.update_employee_checkin_records()
        shift_working = frappe.db.get_value("Employee", self.employee, "shift_working")
        if self.attendance_status == "On Leave":
            self.check_on_leave_record()
        if self.attendance_status in {"Day Off", "Client Day Off"} and shift_working:
            self.validate_day_off()
        if self.attendance_status != "On Leave":
            self.mark_attendance()
        # Auto-create Penalty And Investigation on approval (Stories 1, 2, 3)
        self.create_penalty_on_approval()
        # Auto-create Attendance Check Action when action is "Issue a New Mobile"
        self.create_attendance_check_action()

    def create_attendance_check_action(self):
        """Auto-generate an Attendance Check Action (Draft) when this check is
        submitted with the action 'Issue a New Mobile'.

        Enqueued to run in the background *after commit* so it can never block,
        delay or freeze the Attendance Check approval — mirroring the penalty
        creation pattern in ``create_penalty_on_approval``.
        """
        if self.action != "Issue a New Mobile":
            return

        frappe.enqueue(
            _create_attendance_check_action_doc,
            queue="short",
            timeout=120,
            enqueue_after_commit=True,
            attendance_check=self.name,
        )

    def create_penalty_on_approval(self):
        """Evaluate the justification gateway and trigger background penalty creation if applicable."""
        if self.attendance_status != "Present" or not self.justification:
            return

        penalty_params = None

        # Story 1: Forgot to check in → penalize the employee
        if self.justification == "Forgot to check in":

            # Resolve penalty code: use "1" if it exists, otherwise leave blank
            applied_penalty_code = "1" if frappe.db.exists("Penalty Code", "1") else None

            issuer = self._get_issuer_from_employee_hierarchy()
            location = self._get_location_from_employee_site()
            penalty_params = {
                "employee": self.employee,
                "issuer": issuer,
                "applied_penalty_code": applied_penalty_code,
                "incident_date": self.date,
                "location": location,
                "supervisor_remarks": "Forgot to check in",
            }

        # Story 2: User not assigned to shift — employee timing error
        elif (
            self.justification == "User not assigned to shift"
            and self.is_the_employee_assigned_to_the_correct_shift == "Yes"
            and self.did_the_employee_try_to_check_in_outside_working_hours == "Yes"
        ):

            # Resolve penalty code: use "18" if it exists, otherwise leave blank
            applied_penalty_code = "18" if frappe.db.exists("Penalty Code", "18") else None

            issuer = self._get_employee_from_approver()
            location = self._get_location_with_event_fallback()
            penalty_params = {
                "employee": self.employee,
                "issuer": issuer,
                "applied_penalty_code": applied_penalty_code,
                "incident_date": self.date,
                "location": location,
                "supervisor_remarks": "User not assigned to shift",
            }

        # Story 3: User not assigned to shift — supervisor roster error
        elif (
            self.justification == "User not assigned to shift"
            and self.is_the_employee_assigned_to_the_correct_shift == "No"
        ):
            # The offender is the supervisor (the approver on the Attendance Check)
            offender = self._get_employee_from_approver()

            # Resolve penalty code: use "18" if it exists, otherwise leave blank
            applied_penalty_code = "18" if frappe.db.exists("Penalty Code", "18") else None

            # The issuer is the employee's Reports To
            issuer = frappe.db.get_value("Employee", offender, "reports_to") if offender else None
            location = self._get_location_from_employee_site()
            if offender:
                penalty_params = {
                    "employee": offender,
                    "issuer": issuer,
                    "applied_penalty_code": applied_penalty_code,
                    "incident_date": self.date,
                    "location": location,
                    "supervisor_remarks": "User not assigned to shift",
                }

        if penalty_params:
            frappe.enqueue(
                _create_penalty_document,
                queue="short",
                timeout=120,
                penalty_params=penalty_params,
                attendance_check_name=self.name,
            )

    def _get_issuer_from_employee_hierarchy(self):
        """Get the Site Supervisor / Shift Supervisor / Reports To for the employee."""
        approver_employee = self.get_approver(self.employee)
        return approver_employee if approver_employee else None

    def _get_employee_from_approver(self):
        """Get the Employee record whose user_id matches the Attendance Check's approver."""
        if not self.approver:
            return None
        return frappe.db.get_value("Employee", {"user_id": self.approver, "status": "Active"}, "name")

    def _get_location_from_employee_site(self):
        """Get the Operations Site from the Employee's allocated site (or from the Attendance Check)."""
        # Prefer the operations_site already set on this Attendance Check
        if self.operations_site:
            return self.operations_site
        # Fall back to the Employee's site allocation
        site = frappe.db.get_value("Employee", self.employee, "site")
        return site if site else None

    def _get_location_with_event_fallback(self):
        """Try to get event_location from Shift Assignment, fall back to Employee's Operations Site.

        Note: event_location is a Data field on Shift Assignment (not a Link to Operations Site).
        If event_location is set, try to find a matching Operations Site by name.
        If not found, fall back to Employee's Operations Site.
        """
        if self.shift_assignment:
            event_location = frappe.db.get_value("Shift Assignment", self.shift_assignment, "event_location")
            if event_location:
                # event_location is a Data field — check if it matches an Operations Site
                if frappe.db.exists("Operations Site", event_location):
                    return event_location
                # If not a valid Operations Site, try the site from shift assignment
                sa_site = frappe.db.get_value("Shift Assignment", self.shift_assignment, "site")
                if sa_site:
                    return sa_site
        return self._get_location_from_employee_site()

    def update_employee_checkin_records(self):
        if self.attendance_status == "Present":
            employment_type = frappe.db.get_value("Employee", self.employee, "employment_type")
            if employment_type == "Full-time":
                if self.checkin_record:
                    self.update_employee_checkin(self.checkin_record, self.start_time)
                else:
                    self.create_employee_checkin_record(self.start_time, "IN")
                if self.checkout_record:
                    self.update_employee_checkin(self.checkout_record, self.end_time)
                else:
                    self.create_employee_checkin_record(self.end_time, "OUT")

    def update_employee_checkin(self, checkin_name, time):
        frappe.db.set_value("Employee Checkin", checkin_name, {
            "time": time,
            "source": "Attendance Check"
        })

    def create_employee_checkin_record(self, time, log_type):
        existing_checkin = self.get_existing_employee_checkin(time, log_type)
        if existing_checkin:
            self.update_employee_checkin(existing_checkin, time)
            return
        checkin = frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": self.employee,
            "time": time,
            "log_type": log_type,
            "shift_assignment": self.shift_assignment,
            "source": "Attendance Check"
        })
        checkin.insert(ignore_permissions=True)

    def get_existing_employee_checkin(self, time, log_type):
        return frappe.db.get_value(
            "Employee Checkin",
            {
                "employee": self.employee,
                "time": time
            }
        )

    def check_on_leave_record(self):
        if self.attendance_status == "On Leave":
            # Check for approved leave record
            if not self.get_approved_leave_records(): # if approval occurs while the document is still being created
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
    def get_approved_leave_records(self):
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
                docstatus = 1
            """,
            as_dict=True
        )

    def validate_day_off(self):
        if self.attendance_status in {"Day Off", "Client Day Off"}:
            # Check if shift request for that day exists
            shift_request = self.get_shift_request()
            if shift_request:
                workflow_state = shift_request[0].get("workflow_state")
                if workflow_state in {"Draft", "Pending Approval"}:
                    doc_url = get_url_to_form('Shift Request',shift_request[0].get('name'))
                    approver_full_name = frappe.db.get_value("User", shift_request[0].get('approver'), 'full_name')
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
                elif workflow_state == "Approved":
                    return

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

    def get_shift_request(self):
        return frappe.db.sql(f"""
            select
                name, approver, workflow_state
            from
                `tabShift Request`
            where
                employee = '{self.employee}'
                and
                from_date <= '{self.date}'
                and
                to_date >='{self.date}'
            """,
            as_dict=1
        )

    def mark_attendance(self):
        attendance = None
        if getattr(self, "attendance", None):
            linked_attendance = frappe.db.get_value(
                "Attendance",
                self.attendance,
                ["status", "name", "docstatus"],
                as_dict=1
            )
            if linked_attendance and linked_attendance.docstatus < 2:
                attendance = linked_attendance

        if not attendance:
            attendance = self.get_existing_attendance()

        if attendance:
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
                "roster_type": self.roster_type
            },
            ["status", "name"],
            as_dict=1
        )

    def update_existing_attendance_record(self, attendance):
        if attendance.status != self.attendance_status:
            working_hours = self.get_shift_working_hours(self.shift_assignment)
            frappe.db.set_value("Attendance", attendance.name, {
                "status": self.attendance_status,
                "reference_doctype": self.doctype,
                "reference_docname": self.name,
                "working_hours": working_hours,
                "comment": "Updated from Attendance Check"
            }, update_modified=True)

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

def _create_penalty_document(penalty_params, attendance_check_name):
    """Background job: Create a Draft Penalty And Investigation document.

    Args:
        penalty_params (dict): Fields to set on the Penalty And Investigation document.
        attendance_check_name (str): Name of the originating Attendance Check (for logging).
    """
    try:
        penalty = frappe.new_doc("Penalty And Investigation")
        penalty.employee = penalty_params.get("employee")
        penalty.issuer = penalty_params.get("issuer")
        penalty.applied_penalty_code = penalty_params.get("applied_penalty_code")
        penalty.incident_date = penalty_params.get("incident_date")
        penalty.issuance_date = frappe.utils.today()
        penalty.supervisor_remarks = penalty_params.get("supervisor_remarks")

        # Location is a Link to Operations Site — only set if the site_location resolves
        location = penalty_params.get("location")
        if location:
            penalty.location = location

        penalty.flags.ignore_mandatory = True
        penalty.insert(ignore_permissions=True)

        frappe.db.commit()
        frappe.logger().info(
            f"Penalty And Investigation {penalty.name} created from Attendance Check {attendance_check_name}"
        )
    except Exception:
        frappe.log_error(
            title="Auto Penalty Creation Failed",
            message=f"Attendance Check: {attendance_check_name}\n{frappe.get_traceback()}"
        )

def _create_attendance_check_action_doc(attendance_check):
    """Background job: create a Draft Attendance Check Action for an Attendance Check
    whose action is 'Issue a New Mobile'.

    Args:
        attendance_check (str): Name of the source Attendance Check.
    """
    try:
        # Skip if an action already exists for this check (re-submit / retry safety).
        if frappe.db.exists("Attendance Check Action", {"attendance_check": attendance_check}):
            return

        source = frappe.db.get_value(
            "Attendance Check",
            attendance_check,
            ["employee", "date", "action"],
            as_dict=True,
        )
        if not source or source.action != "Issue a New Mobile":
            return

        # The Attendance Check Action is named HR-ACA-{employee}_{start_date}; guard
        # against a name collision from another roster type on the same day.
        expected_name = f"HR-ACA-{source.employee}_{source.date}"
        if frappe.db.exists("Attendance Check Action", expected_name):
            return

        action_doc = frappe.new_doc("Attendance Check Action")
        action_doc.attendance_check = attendance_check
        action_doc.employee = source.employee
        action_doc.action = "Issue a New Mobile"
        action_doc.start_date = source.date
        action_doc.status = "Draft"
        action_doc.insert(ignore_permissions=True)

        frappe.db.commit()
    except Exception:
        frappe.log_error(
            title="Attendance Check Action Creation Failed",
            message=f"Attendance Check: {attendance_check}\n{frappe.get_traceback()}",
        )


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
            insert_attendance_check_records(attendance_not_marked_shift_employees, attendance_date)

def get_absentees_on_date(attendance_date):
    shift_permission_employees = frappe.db.get_list('Shift Permission', filters={'date': attendance_date}, pluck='employee')
    day_off_employees = frappe.db.get_list('Employee Schedule', filters={'date': attendance_date, 'employee_availability': ['in', ['Client Day Off', 'Day Off']]}, pluck='employee')
    excluded_employees = shift_permission_employees + day_off_employees

    return frappe.get_all("Attendance",
        filters={
            'docstatus': 1,
            'status': 'Absent',
            'attendance_date': attendance_date,
            "employee": ["not in", excluded_employees]
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
    
    # Fetch all the employees who is shift working but no attendance marked
    return frappe.db.sql("""
        SELECT
            sa.employee
        FROM
            `tabShift Assignment` sa
        LEFT JOIN
            `tabAttendance` att
        ON
            sa.employee = att.employee AND att.attendance_date = %(attendance_date)s
        WHERE
            sa.start_date <= %(attendance_date)s
            AND sa.end_date >= %(attendance_date)s
            AND sa.docstatus = 1
            AND sa.status = 'Active'
            AND att.name IS NULL
            AND sa.employee NOT IN (
                SELECT employee 
                FROM `tabEmployee Schedule` 
                WHERE date = %(attendance_date)s 
                AND employee_availability IN ('Client Day Off', 'Day Off')
            )
    """, {"attendance_date": attendance_date}, as_dict=1)

def insert_attendance_check_records(details, attendance_date):
    employee_ids = [d.get("employee") for d in details]
    # Fetch shift assignments for all employees in a single query
    shift_assignments = frappe.get_all(
        "Shift Assignment",
        filters=[
            ["start_date", "<=", attendance_date],
            ["end_date", ">=", attendance_date],
            ["docstatus", "=", 1],
            ["employee", "in", employee_ids],
        ],
        fields=["employee"],
    )
    employees_with_shifts = {sa.employee for sa in shift_assignments}

    # Fetch employees with attendance by timesheet in a single query
    employees_by_timesheet = frappe.get_all(
        "Employee",
        filters={"name": ["in", employee_ids], "attendance_by_timesheet": 1},
        fields=["name"],
    )
    employees_with_timesheet = {emp.name for emp in employees_by_timesheet}

    # Story 7: Pre-fetch yesterday's "Issue a New Mobile" records for carryover
    yesterday = add_days(attendance_date, -1)
    yesterday_carryover = _get_yesterday_carryover_data(employee_ids, yesterday)

    for count, data in enumerate(details):
        try:
            employee = data.get("employee")
            has_shift = employee in employees_with_shifts
            on_timesheet = employee in employees_with_timesheet

            if has_shift or on_timesheet:
                filters = {
                    "doctype": "Attendance Check",
                    "employee": employee,
                    "date": attendance_date,
                    "attendance": data.get("attendance", ""),
                    "roster_type": data.get("roster_type", "Basic"),
                    "attendance_by_timesheet": on_timesheet,
                    "marked_attendance_status": data.get("attendance_status", ""),
                    "shift_assignment": data.get("shift_assignment", ""),
                    "attendance_marked": 1 if data.get("attendance") else 0,
                    "comment": data.get("attendance_comment", ""),
                }

                # Story 7: Apply carryover from yesterday if "Issue a New Mobile"
                carryover = yesterday_carryover.get(employee)
                if carryover:
                    filters.update({
                        "justification": carryover.get("justification", ""),
                        "action": carryover.get("action", ""),
                        "is_the_employee_physically_onsite": carryover.get("is_the_employee_physically_onsite", ""),
                        "is_the_mobile_specification_up_to_the_standard": carryover.get("is_the_mobile_specification_up_to_the_standard", ""),
                        "were_proper_permissions_given_to_the_app": carryover.get("were_proper_permissions_given_to_the_app", ""),
                        "mobile_brand": carryover.get("mobile_brand", ""),
                        "mobile_model": carryover.get("mobile_model", ""),
                        "screenshot": carryover.get("screenshot", ""),
                        "attendance_status": "Present",
                    })

                doc = frappe.get_doc(filters)
                doc.flags.ignore_mandatory = 1
                doc.insert(ignore_permissions=1)
        except Exception as e:
            if "Attendance Check already exist for" not in str(e):
                frappe.log_error(message=frappe.get_traceback(), title="Attendance Check Creation")
        if count % 10 == 0:
            frappe.db.commit()
    frappe.db.commit()


def _get_yesterday_carryover_data(employee_ids, yesterday):
    """Fetch yesterday's Attendance Check records that had action = 'Issue a New Mobile'.

    Returns a dict keyed by employee ID with the fields to carry over.
    """
    if not employee_ids:
        return {}

    yesterday_records = frappe.get_all(
        "Attendance Check",
        filters={
            "employee": ["in", employee_ids],
            "date": yesterday,
            "action": "Issue a New Mobile",
            "docstatus": ["<", 2],
        },
        fields=[
            "employee", "justification", "action",
            "is_the_employee_physically_onsite",
            "is_the_mobile_specification_up_to_the_standard",
            "were_proper_permissions_given_to_the_app",
            "mobile_brand", "mobile_model", "screenshot",
        ],
    )

    carryover_map = {}
    for rec in yesterday_records:
        carryover_map[rec.employee] = rec

    return carryover_map


@frappe.whitelist()
def check_attendance_manager(email: str) -> bool:
    return (frappe.db.get_value("Employee", {"user_id": email}) == frappe.db.get_single_value("ONEFM General Setting", "attendance_manager")) or (frappe.session.user == "Administrator")

def attendance_check_pending_approval_check():
    pending_approval_attendance_checks = get_pending_approval_attendance_check(48)
    if pending_approval_attendance_checks and len(pending_approval_attendance_checks) > 0:
        # Issue Penalty to the assigned approver
        issue_penalty_to_the_assigned_approver(pending_approval_attendance_checks)
        # Assign the attendance checks to attendance manager for approval
        assign_attendance_manager(pending_approval_attendance_checks)

        frappe.db.commit()

def get_pending_approval_attendance_check(hours):
    # Method to get list of attendance check, which is in panding approval state after a given hours
    date_time = datetime.strptime(now(), '%Y-%m-%d %H:%M:%S.%f') - timedelta(hours=hours)
    return  frappe.db.sql("""
        select
            name, _assign as assign_to
        from
            `tabAttendance Check`
        where
            creation <= %s
            and
            docstatus = 0

    """, (date_time), as_dict=1)


def issue_penalty_to_the_assigned_approver(pending_approval_attendance_checks):
    try:
        approvers = {}
        for pending_approval_attendance_check in pending_approval_attendance_checks:

            if pending_approval_attendance_check.get('assign_to'):
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
    except:
        frappe.log_error(title = "Error Creating Penalty Documents",message = frappe.get_traceback())

def fetch_existing_todos(manager):
    """Fetch the existing todos for attendance checks assigned to the attendance manager
    Args:
        manager (Str): User
    """
    existing_todos = frappe.get_all("ToDo",{'allocated_to':manager,'status':'Open','reference_type':'Attendance Check'},['reference_name'])
    return [i.reference_name for i in existing_todos]


def create_split_query(todos,limit,manager,today,today_datetime):
    """
    This is to mitigate max_allowed_packet errors when the query size is too large
    Args:
        todos (_type_): all todos
        limit (int): the number of todos per string
    """
    def create_sql_query(sublist):
        values = []
        for d in sublist:
            vals = f"""
                '{manager}_{d.name}',
                 '{manager}',
                 'Attendance Check',
                 '{d.name}',
                 "Assignment for Attendance Check {d.name}",
                 'Medium',
                 'Open',
                 '{today}',
                "Administrator",
                "Action",
                "Administrator",
                '{today_datetime}',
               '{today_datetime}'
               """
            values.append(f"({vals})")
        query = """ INSERT INTO `tabToDo`
                (`name`,`allocated_to`, `reference_type`, `reference_name`,
                `description`, `priority`,`status`, `date`,`owner`,`type`,`assigned_by`,`creation`, `modified`)
                VALUES """ + ', '.join(values)
        return query

    split_lists = [todos[i:i + limit] for i in range(0, len(todos), limit)]

    # Creating SQL query strings for each sublist
    sql_queries = [create_sql_query(sublist) for sublist in split_lists]

    return sql_queries

def create_todos(manager,todos):
    """Create todos for the attendance manager
      Using this approach because there a potential for over 50k entries and timeout

    Args:
        manager (str): attenance manager user
        todos (list): a list of dicts with todo details
    """
    try:
        today = frappe.utils.getdate()
        today_datetime = frappe.utils.get_datetime()

        if len(todos)>10000:
            # Query needs to be split to avoid max query package error
            split_query =create_split_query(todos,10000,manager,today,today_datetime)
            for each in split_query:
                frappe.db.sql(each,values=[])
        else:
            query = """
                INSERT INTO
                    `tabToDo`
                    (
                        `name`,`allocated_to`, `reference_type`, `reference_name`,`description`, `priority`,
                        `status`, `date`, `assigned_by`,`creation`, `modified`,`type`,`owner`
                    )
                VALUES
            """
            query_body = """"""
            for each in todos:
                query_body+= f"""
                        (
                            "{'_'.join([manager,each.name])}", "{manager}", "{'Attendance Check'}", "{each.name}",
                            "Assignment for Attendance Check {each.name}", "{'Medium'}", "{'Open'}", '{today}',
                            "Administrator",'{today_datetime}','{today_datetime}',"Action","Administrator"
                        ),"""
            if query_body:
                query += query_body[:-1]
                frappe.db.sql(query,values=[])
        frappe.db.commit()
    except:
        frappe.log_error(title = "Error Assigning to Attendance Manager",message = frappe.get_traceback())

def notify_manager(manager):
    """Notify the manager that new todos have been created for them

    Args:
        manager (str): attendance manager
    """
    try:
        page_link = frappe.utils.get_url()+f'/app/todo?date={frappe.utils.get_date_str(frappe.utils.getdate())}&allocated_to={manager}'
        msg = frappe.render_template('one_fm/templates/emails/attendance_manager_todo_assignment.html', context={"manager": manager,'page_link':page_link})
        sendemail(recipients= [manager], content=msg, subject="Pending Attendance Checks", delayed=False)
    except:
        frappe.log_error(title = "Error Notifying  Attendance Manager",message = frappe.get_traceback())





def assign_attendance_manager(pending_approval_attendance_checks):
    attendance_manager_user = fetch_attendance_manager_user()
    if attendance_manager_user:
        existing_todos = fetch_existing_todos(attendance_manager_user)
        filtered_pending_approval_attendance_check = [i for i in pending_approval_attendance_checks if i.name not in existing_todos ]
        create_todos(attendance_manager_user,filtered_pending_approval_attendance_check)
        if filtered_pending_approval_attendance_check:
            notify_manager(attendance_manager_user)


def schedule_attendance_check():
    frappe.enqueue(create_attendance_check, queue='long', timeout=7000)