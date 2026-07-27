# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ArrivalandDeployment(Document):
    def validate(self):
        if self.get("workflow_state") in ["Joined", "Did Not Arrive"]:
            roles = frappe.get_roles()
            if self.candidate_country_process:
                if "Transportation Manager" not in roles and "System Manager" not in roles and frappe.session.user != "Administrator":
                    frappe.throw(_("Only the Transportation Manager can perform this action for Overseas hires."))
            else:
                if "Accommodation User" not in roles and "System Manager" not in roles and frappe.session.user != "Administrator":
                    frappe.throw(_("Only General Services can perform this action for Local hires."))

        if self.get("workflow_state") == "Pending Onboarding":
            if not self.arrival_date:
                frappe.throw(_("Please ensure Arrival Date is filled before submitting to Onboarding."))
            if self.candidate_country_process:
                if not self.arrival_time or not self.ticket_attachment or not self.flight_number or not self.airline or not self.terminal or not self.arrival_airport:
                    frappe.throw(_("Please ensure Arrival Time, Flight Number, Airline, Terminal, Ticket Attachment, and Arrival Airport are filled for Overseas hires before submitting to Onboarding."))

        # Keep the plain status field (used for reporting/CCP sync) in step with the
        # actual workflow_state -- Pending/Draft/Pending Onboarding stay "Pending".
        if self.get("workflow_state") == "Pending Support Departments":
            self.status = "Arriving"
        elif self.get("workflow_state") == "Joined":
            self.status = "Joined"
        elif self.get("workflow_state") == "Did Not Arrive":
            self.status = "Did Not Arrive"

        self.update_tracker_status()

    def before_save(self):
        if self.get("workflow_state") == "Pending Support Departments" and not self.support_assigned_on:
            self.support_assigned_on = frappe.utils.now_datetime()

    def update_tracker_status(self):
        """Sync status back to the Candidate Country Process tracker row (non-recursive)."""
        if not self.candidate_country_process:
            return
        rows = frappe.get_all(
            "Candidate Country Process Details",
            filters={"parent": self.candidate_country_process, "process_name": "Arrival & Deployment"},
            fields=["name"],
            limit=1,
        )
        if not rows:
            return

        sync_status = self.status
        if self.get("workflow_state") == "Joined":
            sync_status = "Joined"
        elif self.get("workflow_state") == "Did Not Arrive":
            sync_status = "Did Not Arrive"

        updates = {"status": sync_status}
        if self.arrival_date:
            updates["actual_date"] = self.arrival_date

        for field, value in updates.items():
            frappe.db.set_value("Candidate Country Process Details", rows[0].name, field, value, update_modified=True)

    def on_update(self):
        """Notify the CCP engine to evaluate downstream triggers."""
        old_state = self.get_doc_before_save().get("workflow_state") if self.get_doc_before_save() else None

        if self.get("workflow_state") == "Pending Onboarding" and old_state != "Pending Onboarding":
            self.notify_onboarding_officer()

        if self.get("workflow_state") == "Did Not Arrive" and old_state != "Did Not Arrive":
            self.notify_recruiter_arrival_outcome("Did Not Arrive")

        if self.get("workflow_state") == "Pending Support Departments" and old_state != "Pending Support Departments":
            self.assign_support_departments()

        if self.get("workflow_state") == "Joined" and old_state != "Joined":
            self.clear_support_assignments()
            self.notify_recruiter_arrival_outcome("Joined")

        if self.candidate_country_process:
            if self.get("workflow_state") == "Joined" and old_state != "Joined":
                frappe.db.set_value("Candidate Country Process", self.candidate_country_process, "status", "Joined")
            elif self.get("workflow_state") == "Did Not Arrive" and old_state != "Did Not Arrive":
                frappe.db.set_value("Candidate Country Process", self.candidate_country_process, "status", "Did Not Arrive")
            
            if self.get("workflow_state") != old_state:
                from one_fm.one_fm.doctype.candidate_country_process.candidate_country_process import recalculate_ccp_live_eta
                recalculate_ccp_live_eta(self.candidate_country_process)

    def assign_support_departments(self):
        """Create an Arrival Acknowledgement per department and assign a ToDo to each.

        Department users (Warehouse, General Services, Finance, Transportation, Operations)
        generally have no role that grants access to Arrival and Deployment itself, so the
        ToDo points at their own Arrival Acknowledgement record instead -- a self-contained
        copy of the candidate/flight details they need, with an Acknowledge button.
        """
        instructions = {
            "Transportation": "Kindly arrange Airport Pick Up Accordingly.",
            "General Services": "Kindly arrange accommodation Accordingly and confirm the date and time for GS Orientation.",
            "Finance": "Kindly arrange 30 KD as Loan Amount for the arriving employees.",
            "Warehouse": "Kindly arrange their Uniforms and welcome kit accordingly.",
            "Operations": "Kindly arrange shifts and inform me accordingly to update shift allocation during onboarding and confirm the date and time for Operations Orientation.",
        }
        departments = [
            ("Warehouse", self.warehouse),
            ("General Services", self.general_services),
            ("Operations", self.operations_admin),
            ("Transportation", self.transportation_manager),
            ("Finance", self.finance),
        ]

        overseas_only = ("Transportation", "Finance")

        for department, user in departments:
            if not user:
                continue
            if department in overseas_only and not self.candidate_country_process:
                continue
            self.create_arrival_acknowledgement(department, user, instructions[department])

    def create_arrival_acknowledgement(self, department, user, instruction):
        from frappe.desk.form.assign_to import add as add_assignment

        ack_name = frappe.db.exists(
            "Arrival Acknowledgement",
            {"arrival_and_deployment": self.name, "department": department},
        )
        if not ack_name:
            ack = frappe.new_doc("Arrival Acknowledgement")
            ack.arrival_and_deployment = self.name
            ack.department = department
            ack.assigned_to = user
            ack.candidate_name = self.candidate_name
            ack.passport_number = self.passport_number
            ack.arrival_date = self.arrival_date
            ack.arrival_time = self.arrival_time
            ack.flight_number = self.flight_number
            ack.airline = self.airline
            ack.terminal = self.terminal
            ack.arrival_airport = self.arrival_airport
            ack.ticket_attachment = self.ticket_attachment
            ack.insert()
            ack_name = ack.name

            # Frappe unconditionally defaults every Time-type field to nowtime() on
            # insert (frappe.model.create_new.set_dynamic_default_values) -- there's no
            # way to opt out via field config, so orientation_time would otherwise look
            # "already filled in" the moment this record is created, defeating both the
            # mandatory validation and the department's ability to tell it's still blank.
            frappe.db.set_value("Arrival Acknowledgement", ack_name, "orientation_time", None, update_modified=False)

        try:
            add_assignment({
                "assign_to": [user],
                "doctype": "Arrival Acknowledgement",
                "name": ack_name,
                "description": f"Dear {user},\n\n{instruction}",
            })
        except Exception as e:
            frappe.log_error(title="Arrival Assignment Error", message=f"Assignment failed for {ack_name}: {str(e)}")

    def clear_support_assignments(self):
        """Clear each department's ToDo -- these live on their own Arrival
        Acknowledgement record, not on this document, since that's where the
        assignment actually gets created (see create_arrival_acknowledgement)."""
        from frappe.desk.form.assign_to import clear as clear_assignment
        try:
            clear_assignment(self.doctype, self.name)
        except Exception:
            pass

        for ack_name in frappe.get_all(
            "Arrival Acknowledgement", filters={"arrival_and_deployment": self.name}, pluck="name"
        ):
            try:
                clear_assignment("Arrival Acknowledgement", ack_name)
            except Exception as e:
                frappe.log_error(title="Arrival Assignment Error", message=f"Failed to clear assignment for {ack_name}: {str(e)}")


    def notify_onboarding_officer(self):
        if not self.onboarding_officer:
            return

        officer_email = frappe.db.get_value("User", self.onboarding_officer, "email")

        job_applicant_name, nationality, designation = None, None, None
        if self.candidate_country_process:
            job_applicant = frappe.db.get_value("Candidate Country Process", self.candidate_country_process, "job_applicant")
            if job_applicant:
                job_applicant_name, nationality, designation = frappe.db.get_value(
                    "Job Applicant", job_applicant, ["applicant_name", "one_fm_nationality", "one_fm_designation"]
                )
        display_name = job_applicant_name or self.candidate_name

        from frappe.desk.form.assign_to import add as add_assignment
        try:
            add_assignment({
                "assign_to": [self.onboarding_officer],
                "doctype": self.doctype,
                "name": self.name,
                "description": f"Dear Onboarding Officer,\n\nKindly prepare onboarding for {display_name}, arriving on {self.arrival_date or 'TBD'}."
            })
        except Exception as e:
            frappe.log_error(title="Onboarding Assignment Error", message=f"Failed to assign onboarding officer for {self.name}: {str(e)}")

        if not officer_email:
            return

        from frappe.utils import escape_html
        subject = f"New Candidate Ready for Onboarding: {escape_html(display_name)}"
        message = f'''
        <p>Dear Onboarding Officer,</p>
        <p>A new candidate is ready for onboarding:</p>
        <ul>
            <li><b>Name:</b> {escape_html(display_name)}</li>
            <li><b>Designation:</b> {escape_html(designation) if designation else 'N/A'}</li>
            <li><b>Nationality:</b> {escape_html(nationality) if nationality else 'N/A'}</li>
            <li><b>Arriving on:</b> {self.arrival_date or 'TBD'}</li>
        </ul>
        <p>Please review the <a href="/app/arrival-and-deployment/{self.name}">Arrival and Deployment Document</a> and prepare accordingly.</p>
        '''

        frappe.enqueue(
            method=frappe.sendmail,
            queue='short',
            recipients=[officer_email],
            subject=subject,
            message=message
        )

    def notify_recruiter_arrival_outcome(self, outcome):
        """outcome: "Joined" (arrived) or "Did Not Arrive" """
        if not self.recruiter:
            return

        recruiter_email = frappe.db.get_value("User", self.recruiter, "email")
        if not recruiter_email:
            return

        designation = None
        if self.candidate_country_process:
            job_applicant = frappe.db.get_value("Candidate Country Process", self.candidate_country_process, "job_applicant")
            if job_applicant:
                designation = frappe.db.get_value("Job Applicant", job_applicant, "one_fm_designation")

        arrived = outcome == "Joined"
        from frappe.utils import escape_html
        subject = f"{'Candidate Arrived' if arrived else 'Urgent: Candidate Did Not Arrive'} - {escape_html(self.candidate_name)}"
        message = f'''
        <p>Dear Recruiter,</p>
        <p>Please be informed that the candidate <b>{escape_html(self.candidate_name)}</b>
        ({escape_html(designation) if designation else 'N/A'}) {'has arrived as scheduled.' if arrived else 'did not arrive as scheduled.'}</p>
        <p>Please review the <a href="/app/arrival-and-deployment/{self.name}">Arrival and Deployment Document</a>{'' if arrived else ' and take necessary action'}.</p>
        '''

        frappe.enqueue(
            method=frappe.sendmail,
            queue='short',
            recipients=[recruiter_email],
            subject=subject,
            message=message
        )


def has_permission(doc, ptype=None, user=None, **kwargs):
    """
    Transportation Manager gets a real read/write grant on Arrival and Deployment
    (see the DocType's own permissions, restricted to workflow_state via permlevel)
    so confirm_arrival() no longer needs ignore_permissions -- but only scoped to
    records where they're the assigned transportation contact. Without this hook,
    that plain role-permission grant would let every Transportation Manager read
    and write every candidate's record company-wide, not just the ones assigned
    to them.

    Every other role with real access here (System Manager, HR Manager, HR User,
    Recruitment Manager, Recruiter, Senior Recruiter, Interviewer) already has
    unrestricted doctype-level access and is unaffected -- this hook only narrows
    things down for Transportation Manager specifically.
    """
    user = user or frappe.session.user
    if user == "Administrator":
        return None

    roles = frappe.get_roles(user)
    if "Transportation Manager" not in roles:
        return None

    if any(role in roles for role in (
        "System Manager", "HR Manager", "HR User", "Recruitment Manager",
        "Recruiter", "Senior Recruiter", "Interviewer",
    )):
        return None

    if doc.get("transportation_manager") == user:
        return None

    return False



