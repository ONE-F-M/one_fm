# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

# Final states meaning the candidate arrived; both set the Candidate Country Process to Joined
ARRIVED_STATES = ("Arrived", "Joined")
ARRIVING_STATES = ("Onboarding Confirmed", "Pending Support Departments")


class ArrivalandDeployment(Document):
    def validate(self):
        self.designation = get_job_applicant_designation(self.job_applicant)

        if self.has_value_changed("workflow_state"):
            self.validate_workflow_role()

        if self.get("workflow_state") == "Onboarding Confirmed" and self.candidate_country_process and not self.transportation_manager:
            frappe.throw(_("Please fill in the Transportation Manager before confirming onboarding."))

        if self.get("workflow_state") == "Pending Onboarding":
            if not self.arrival_date:
                frappe.throw(_("Please ensure Arrival Date is filled before submitting to Onboarding."))
            if self.candidate_country_process:
                if not self.arrival_time or not self.ticket_attachment or not self.flight_number or not self.airline or not self.terminal or not self.arrival_airport:
                    frappe.throw(_("Please ensure Arrival Time, Flight Number, Airline, Terminal, Ticket Attachment, and Arrival Airport are filled for Overseas hires before submitting to Onboarding."))

        # Keep the plain status field (used for reporting/CCP sync) in step with the
        # actual workflow_state -- Pending/Draft/Pending Onboarding stay "Pending".
        if self.get("workflow_state") in ARRIVING_STATES:
            self.status = "Arriving"
        elif self.get("workflow_state") in ARRIVED_STATES:
            self.status = "Joined"
        elif self.get("workflow_state") == "Did Not Arrive":
            self.status = "Did Not Arrive"

        self.update_tracker_status()

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
        if self.get("workflow_state") in ARRIVED_STATES:
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

        if self.get("workflow_state") == "Onboarding Confirmed" and old_state != "Onboarding Confirmed":
            self.close_assignments()
            self.assign_transportation_manager()

        if self.get("workflow_state") == "Did Not Arrive" and old_state != "Did Not Arrive":
            self.close_assignments()
            self.notify_recruiter_arrival_outcome("Did Not Arrive")

        if self.get("workflow_state") in ARRIVED_STATES and old_state not in ARRIVED_STATES:
            self.close_assignments()
            self.notify_recruiter_arrival_outcome("Joined")

        if self.candidate_country_process:
            if self.get("workflow_state") in ARRIVED_STATES and old_state not in ARRIVED_STATES:
                frappe.db.set_value("Candidate Country Process", self.candidate_country_process, "status", "Joined")
            elif self.get("workflow_state") == "Did Not Arrive" and old_state != "Did Not Arrive":
                frappe.db.set_value("Candidate Country Process", self.candidate_country_process, "status", "Did Not Arrive")
            
            if self.get("workflow_state") != old_state:
                from one_fm.one_fm.doctype.candidate_country_process.candidate_country_process import recalculate_ccp_live_eta
                recalculate_ccp_live_eta(self.candidate_country_process)

    def validate_workflow_role(self):
        """Onboarding confirms; the Transportation Manager marks arrival for overseas hires, the Onboarding Officer for local hires."""
        roles = frappe.get_roles()
        if "System Manager" in roles:
            return

        state = self.get("workflow_state")
        if state == "Onboarding Confirmed" and "Onboarding Officer" not in roles:
            frappe.throw(_("Only the Onboarding Officer can confirm onboarding."))
        if state in ("Arrived", "Did Not Arrive"):
            required_role = "Transportation Manager" if self.candidate_country_process else "Onboarding Officer"
            if required_role not in roles:
                frappe.throw(_("Only the {0} can mark whether the candidate arrived.").format(_(required_role)))

    def close_assignments(self):
        """Close the open ToDos on this arrival once its step is done."""
        from frappe.desk.form.assign_to import clear as clear_assignment

        clear_assignment(self.doctype, self.name)

    def assign_transportation_manager(self):
        """Give the Transportation Manager the pickup task once onboarding is confirmed (overseas hires only)."""
        if not self.transportation_manager:
            return

        from frappe.desk.form.assign_to import add as add_assignment
        from frappe.utils import formatdate

        add_assignment({
            "assign_to": [self.transportation_manager],
            "doctype": self.doctype,
            "name": self.name,
            "description": _("Kindly arrange the airport pickup for {0}, arriving {1} {2} on {3}. Mark Arrived or Did Not Arrive once done.").format(
                self.candidate_name, formatdate(self.arrival_date), self.arrival_time or "", self.flight_number or ""
            ),
        })

    def notify_onboarding_officer(self):
        if not self.onboarding_officer:
            return

        officers = [officer for officer in (self.onboarding_officer, self.second_onboarding_officer) if officer]
        officer_emails = [
            email for email in (frappe.db.get_value("User", officer, "email") for officer in officers) if email
        ]

        job_applicant_name, nationality, designation = None, None, None
        if self.candidate_country_process:
            job_applicant = frappe.db.get_value("Candidate Country Process", self.candidate_country_process, "job_applicant")
            if job_applicant:
                job_applicant_name, nationality = frappe.db.get_value(
                    "Job Applicant", job_applicant, ["applicant_name", "one_fm_nationality"]
                )
                designation = get_job_applicant_designation(job_applicant)
        display_name = job_applicant_name or self.candidate_name

        from frappe.desk.form.assign_to import add as add_assignment
        try:
            add_assignment({
                "assign_to": officers,
                "doctype": self.doctype,
                "name": self.name,
                "description": f"Dear Onboarding Officer,\n\nKindly prepare onboarding for {display_name}, arriving on {self.arrival_date or 'TBD'}."
            })
        except Exception as e:
            frappe.log_error(title="Onboarding Assignment Error", message=f"Failed to assign onboarding officer for {self.name}: {str(e)}")

        if not officer_emails:
            return

        from frappe.utils import escape_html, formatdate

        subject = _("New Candidate Ready for Onboarding: {0}, arriving {1}").format(
            escape_html(display_name), formatdate(self.arrival_date)
        )
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
            recipients=officer_emails,
            cc=get_onboarding_mailbox() if self.email_onboarding_mailbox else None,
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
                designation = get_job_applicant_designation(job_applicant)

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


def get_job_applicant_designation(job_applicant):
    """The Job Applicant's Designation, or its One FM Designation when that is the only one filled."""
    if not job_applicant:
        return None
    designation, one_fm_designation = frappe.db.get_value(
        "Job Applicant", job_applicant, ["designation", "one_fm_designation"]
    )
    return designation or one_fm_designation


def get_onboarding_mailbox():
    """The onboarding mailbox from Hiring Settings."""
    return frappe.db.get_value(
        "Arrival Department Email", {"parenttype": "Hiring Settings", "department": "Onboarding"}, "email"
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



