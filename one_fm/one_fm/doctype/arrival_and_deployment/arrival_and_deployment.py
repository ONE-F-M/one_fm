# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

# Final states meaning the candidate arrived; both set the Candidate Country Process to Joined
ARRIVED_STATES = ("Arrived", "Joined")
ARRIVING_STATES = ("Onboarding Confirmed", "Pick Up Arranged", "Pending Support Departments")
PICKUP_STATES = ("Onboarding Confirmed", "Pick Up Arranged")
MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


class ArrivalandDeployment(Document):
    def validate(self):
        self.designation = get_job_applicant_designation(self.job_applicant)
        self.hiring_type = get_hiring_type(self.candidate_country_process)

        if self.has_value_changed("workflow_state"):
            self.validate_workflow_role()

        if self.get("workflow_state") == "Onboarding Confirmed" and self.candidate_country_process and not self.transportation_manager:
            frappe.throw(_("Please fill in the Transportation Manager before confirming onboarding."))

        if self.get("workflow_state") == "Pending Onboarding":
            if self.has_value_changed("workflow_state"):
                self.recruiter = frappe.session.user
            if not self.arrival_date:
                frappe.throw(_("Please ensure Arrival Date is filled before submitting to Onboarding."))
            if self.candidate_country_process:
                if not self.ticket_attachment:
                    frappe.throw(_("Please attach the Ticket for Overseas hires before submitting to Onboarding."))

        # Keep the plain status field (used for reporting/CCP sync) in step with the
        # actual workflow_state -- Pending/Draft/Pending Onboarding stay "Pending".
        if self.get("workflow_state") in ARRIVING_STATES:
            self.status = "Arriving"
        elif self.get("workflow_state") in ARRIVED_STATES:
            self.status = "Joined"
        elif self.get("workflow_state") == "Did Not Arrive":
            self.status = "Did Not Arrive"

        self.department = get_ccp_department(self.candidate_country_process) or self.department
        self.update_tracker_status()

    def onload(self):
        self.set_onload("ccp_department", get_ccp_department(self.candidate_country_process))

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
            if self.candidate_country_process:
                self.close_assignments()
                self.assign_transportation_manager()
        elif (
            self.get("workflow_state") in PICKUP_STATES
            and self.get_doc_before_save()
            and self.has_value_changed("transportation_manager")
        ):
            self.move_pickup_task(self.get_doc_before_save().transportation_manager)

        if (
            old_state == "Onboarding Confirmed"
            and self.get("workflow_state") in ARRIVED_STATES + ("Did Not Arrive",)
            and self.candidate_country_process
        ):
            self.cancel_pickup_task()

        if self.get("workflow_state") == "Did Not Arrive" and old_state != "Did Not Arrive":
            self.close_assignments()
            self.notify_recruiter_arrival_outcome("Did Not Arrive")

        if self.get("workflow_state") in ARRIVED_STATES and old_state not in ARRIVED_STATES:
            self.close_assignments()
            self.notify_recruiter_arrival_outcome("Joined")

        if self.candidate_country_process:
            if self.department and not get_ccp_department(self.candidate_country_process):
                frappe.db.set_value("Candidate Country Process", self.candidate_country_process, "department", self.department)

            if (
                self.get("workflow_state") == "Pending Onboarding"
                and old_state != "Pending Onboarding"
                and frappe.db.get_value("Candidate Country Process", self.candidate_country_process, "status") == "In Process"
            ):
                frappe.db.set_value("Candidate Country Process", self.candidate_country_process, "status", "Arriving")
            elif self.get("workflow_state") in ARRIVED_STATES and old_state not in ARRIVED_STATES:
                frappe.db.set_value("Candidate Country Process", self.candidate_country_process, "status", "Joined")
            elif self.get("workflow_state") == "Did Not Arrive" and old_state != "Did Not Arrive":
                frappe.db.set_value("Candidate Country Process", self.candidate_country_process, "status", "Did Not Arrive")
            
            if self.get("workflow_state") != old_state:
                from one_fm.one_fm.doctype.candidate_country_process.candidate_country_process import recalculate_ccp_live_eta
                recalculate_ccp_live_eta(self.candidate_country_process)

    def validate_workflow_role(self):
        """Onboarding or the Recruiter confirms; the Transportation Manager (overseas) or Onboarding Officer (local) or the Recruiter marks arrival."""
        roles = frappe.get_roles()
        if "System Manager" in roles:
            return

        state = self.get("workflow_state")
        if state == "Onboarding Confirmed" and not {"Onboarding Officer", "Recruiter"} & set(roles):
            frappe.throw(_("Only the Onboarding Officer or the Recruiter can confirm onboarding."))
        if state == "Pick Up Arranged" and "Transportation Manager" not in roles:
            frappe.throw(_("Only the Transportation Manager can arrange the pickup."))
        if state in ("Arrived", "Did Not Arrive"):
            required_role = "Transportation Manager" if self.candidate_country_process else "Onboarding Officer"
            if not {required_role, "Recruiter"} & set(roles):
                frappe.throw(
                    _("Only the {0} or the Recruiter can mark whether the candidate arrived.").format(_(required_role))
                )

    def close_assignments(self):
        """Mark the open ToDos on this arrival Closed once its step is done."""
        from frappe.desk.form.assign_to import close_all_assignments

        close_all_assignments(self.doctype, self.name)

    def move_pickup_task(self, previous_transportation_manager):
        """Hand the pickup task to the new Transportation Manager when it changes after onboarding is confirmed."""
        from frappe.desk.form.assign_to import remove as remove_assignment

        if previous_transportation_manager:
            remove_assignment(self.doctype, self.name, previous_transportation_manager)
        self.assign_transportation_manager()

    def cancel_pickup_task(self):
        """The Recruiter marked the arrival before any pickup was arranged, so the pickup task is cancelled, not closed."""
        if not self.transportation_manager:
            return

        from frappe.desk.form.assign_to import remove as remove_assignment

        remove_assignment(self.doctype, self.name, self.transportation_manager)

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
            "description": _("Kindly arrange the airport pickup for {0}, arriving {1}; the flight is on the attached ticket. Click Arrange Pick Up, then mark Arrived or Did Not Arrive.").format(
                self.candidate_name, formatdate(self.arrival_date)
            ),
        })

    def notify_onboarding_officer(self):
        if not self.onboarding_officer:
            return

        officers = [officer for officer in (self.onboarding_officer, self.second_onboarding_officer) if officer]
        officer_emails = [
            email for email in (frappe.db.get_value("User", officer, "email") for officer in officers) if email
        ]

        job_applicant_name = None
        if self.candidate_country_process:
            job_applicant = frappe.db.get_value("Candidate Country Process", self.candidate_country_process, "job_applicant")
            if job_applicant:
                job_applicant_name = frappe.db.get_value("Job Applicant", job_applicant, "applicant_name")
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

        if not officer_emails or frappe.flags.arrival_bulk_email:
            return

        from frappe.utils import escape_html, formatdate

        subject = _("New Candidate Ready for Onboarding: {0}, arriving {1}").format(
            escape_html(display_name), formatdate(self.arrival_date)
        )
        message = f'''
        <p>Dear Onboarding Team,</p>
        <p>A new candidate is ready for onboarding:</p>
        {build_arrivals_tables([self])}
        <p>Please review the <a href="/app/arrival-and-deployment/{self.name}">Arrival and Deployment Document</a> and prepare accordingly.</p>
        '''

        sender = get_email_sender(self.recruiter)
        frappe.enqueue(
            method=frappe.sendmail,
            queue='short',
            enqueue_after_commit=True,
            recipients=officer_emails,
            cc=get_onboarding_mailbox() if self.email_onboarding_mailbox else None,
            sender=sender.sender,
            reply_to=sender.reply_to,
            subject=subject,
            message=message + sender.assigned_by
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
            enqueue_after_commit=True,
            recipients=[recruiter_email],
            subject=subject,
            message=message
        )


@frappe.whitelist(methods=["POST"])
def bulk_submit_to_onboarding(names: str):
    """Submit the selected arrivals to onboarding and send each Onboarding Officer group one email with a table."""
    frappe.has_permission("Arrival and Deployment", "write", throw=True)
    arrivals = apply_bulk_workflow(names, "Submit to Onboarding")
    groups = {}
    for arrival in arrivals:
        key = (
            arrival.onboarding_officer,
            arrival.second_onboarding_officer,
            arrival.email_onboarding_mailbox,
        )
        groups.setdefault(key, []).append(arrival)

    for (officer, second_officer, copy_mailbox), group in groups.items():
        recipients = [
            frappe.db.get_value("User", user, "email") for user in (officer, second_officer) if user
        ]
        send_arrivals_email(
            recipients=[email for email in recipients if email],
            cc=get_onboarding_mailbox() if copy_mailbox else None,
            subject=_("New Arrivals Ready for Onboarding: {0} candidates").format(len(group)),
            intro=_("Dear Onboarding Team,<br>Find new arrival details for the following candidates:"),
            arrivals=group,
            sent_by=frappe.session.user,
        )


@frappe.whitelist(methods=["POST"])
def bulk_confirm_onboarding(names: str):
    """Confirm onboarding for the selected arrivals and send each Transportation Manager one pickup email."""
    frappe.has_permission("Arrival and Deployment", "write", throw=True)
    arrivals = apply_bulk_workflow(names, "Confirm Onboarding")
    groups = {}
    for arrival in arrivals:
        if arrival.transportation_manager:
            groups.setdefault((arrival.transportation_manager, arrival.recruiter), []).append(arrival)

    for (transportation_manager, recruiter), group in groups.items():
        send_arrivals_email(
            recipients=[frappe.db.get_value("User", transportation_manager, "email")],
            cc=None,
            subject=_("Airport Pickups to Arrange: {0} arrivals").format(len(group)),
            intro=_("Dear {0},<br>Kindly arrange the airport pickup for the following arrivals:").format(
                frappe.db.get_value("User", transportation_manager, "full_name")
            ),
            arrivals=group,
            sent_by=recruiter,
        )


@frappe.whitelist(methods=["POST"])
def bulk_attach_ticket(names: str, file_url: str):
    """Attach one uploaded ticket to every selected arrival that is still in Draft or Pending Onboarding."""
    frappe.has_permission("Arrival and Deployment", "write", throw=True)
    ticket = frappe.get_doc("File", {"file_url": file_url})
    ticket.check_permission("read")

    refused = []
    for name in frappe.parse_json(names):
        arrival = frappe.get_doc("Arrival and Deployment", name)
        arrival.check_permission("write")
        if arrival.get("workflow_state") not in ("Draft", "Pending Onboarding"):
            refused.append(name)
            continue
        ticket.create_attachment_copy(arrival.doctype, arrival.name, "ticket_attachment")
        arrival.ticket_attachment = ticket.file_url
        arrival.save()

    if refused:
        frappe.msgprint(
            _("The ticket was not attached to {0}, because they are past Pending Onboarding.").format(
                ", ".join(refused)
            ),
            indicator="orange",
        )


def apply_bulk_workflow(names, action):
    """Apply the action to each selected arrival, report the ones that could not move, and return the moved ones."""
    from frappe.model.workflow import apply_workflow

    moved, failures = [], []
    frappe.flags.arrival_bulk_email = True
    try:
        for name in frappe.parse_json(names):
            frappe.db.savepoint("arrival_bulk")
            try:
                moved.append(apply_workflow(frappe.get_doc("Arrival and Deployment", name), action))
            except (frappe.ValidationError, frappe.PermissionError) as e:
                frappe.db.rollback(save_point="arrival_bulk")
                frappe.clear_last_message()
                failures.append(f"{name}: {e}")
    finally:
        frappe.flags.arrival_bulk_email = False

    if failures:
        frappe.msgprint(
            _("These arrivals could not {0}:").format(action) + "<br>" + "<br>".join(failures),
            title=_(action),
            indicator="orange",
        )
    return moved


def send_arrivals_email(recipients, cc, subject, intro, arrivals, sent_by=None):
    """Send one email listing the arrivals, with a table per arrival date."""
    if not recipients:
        return
    sender = get_email_sender(sent_by)
    review = _("Please review the {0} and prepare accordingly.").format(
        f'<a href="{get_arrivals_list_url(arrivals)}">{_("Arrival and Deployment Documents")}</a>'
    )
    frappe.sendmail(
        recipients=recipients,
        cc=cc,
        sender=sender.sender,
        reply_to=sender.reply_to,
        subject=subject,
        message=f"<p>{intro}</p>{build_arrivals_tables(arrivals)}<p>{review}</p>{sender.assigned_by}",
    )


def get_arrivals_list_url(arrivals):
    """The Arrival and Deployment list, filtered to the arrivals in the email."""
    return "/app/arrival-and-deployment?" + urlencode(
        {"name": frappe.as_json(["in", [arrival.name for arrival in arrivals]], indent=None)}
    )


def build_arrivals_tables(arrivals):
    """One HTML table per arrival date, with the candidate details Onboarding and Transportation use and a link to each arrival."""
    from frappe.utils import escape_html, formatdate

    groups = {}
    for arrival in arrivals:
        groups.setdefault(getdate(arrival.arrival_date) if arrival.arrival_date else None, []).append(arrival)

    headers = [
        _("S.No"), _("Arrival and Deployment"), _("Job Applicant"), _("Hiring Type"), _("Agency"), _("Department"), _("Designation"),
        _("Candidate Name"), _("Nationality"), _("Gender"), _("DOB"), _("Passport #"),
    ]
    cell = 'style="border:1px solid #ccc;padding:4px 8px"'
    tables = []
    for arrival_date, group in sorted(groups.items(), key=lambda item: (item[0] is None, item[0] or getdate("1900-01-01"))):
        heading = format_arrival_date(arrival_date)
        rows = []
        for idx, arrival in enumerate(group, start=1):
            hiring_type = arrival.hiring_type or get_hiring_type(arrival.candidate_country_process)
            values = [
                idx,
                arrival.job_applicant,
                _(hiring_type) if hiring_type else "",
                arrival.agency_name,
                arrival.department,
                arrival.designation,
                arrival.candidate_name,
                arrival.nationality,
                arrival.gender,
                formatdate(arrival.date_of_birth) if arrival.date_of_birth else "",
                arrival.passport_number,
            ]
            cells = [f"<td {cell}>{escape_html(str(v or ''))}</td>" for v in values]
            cells.insert(
                1,
                f'<td {cell}><a href="/app/arrival-and-deployment/{arrival.name}">{escape_html(arrival.name or "")}</a></td>',
            )
            rows.append("<tr>" + "".join(cells) + "</tr>")
        header_row = "<tr>" + "".join(f"<th {cell}>{h}</th>" for h in headers) + "</tr>"
        tables.append(
            f"<p><b>{_('Arrival Date')}:</b> {escape_html(heading)}</p>"
            f'<table style="border-collapse:collapse">{header_row}{"".join(rows)}</table>'
        )
    return "".join(tables)


def format_arrival_date(arrival_date):
    """The arrival date as it reads in the emails, e.g. 25th May 2023."""
    if not arrival_date:
        return _("TBD")
    date = getdate(arrival_date)
    if 11 <= date.day % 100 <= 13 or date.day % 10 not in (1, 2, 3):
        day = _("{0}th").format(date.day)
    elif date.day % 10 == 1:
        day = _("{0}st").format(date.day)
    elif date.day % 10 == 2:
        day = _("{0}nd").format(date.day)
    else:
        day = _("{0}rd").format(date.day)
    return f"{day} {_(MONTHS[date.month - 1])} {date.year}"


def get_email_sender(user=None):
    """The sender (the arrival's Recruiter, else whoever is acting): name on the outgoing address, email for replies, and who assigned the arrival ticket."""
    from frappe.email.doctype.email_account.email_account import EmailAccount
    from frappe.utils import escape_html, get_formatted_email

    user = user or frappe.session.user
    full_name, email = frappe.db.get_value("User", user, ["full_name", "email"])
    account = EmailAccount.find_default_outgoing()

    return frappe._dict(
        sender=get_formatted_email(user, mail=account.email_id) if account else None,
        reply_to=email,
        assigned_by=f"<p>{_('Arrival ticket was assigned by {0}.').format(escape_html(full_name or user))}</p>",
    )


def get_ccp_department(candidate_country_process):
    """The department on the Candidate Country Process, which wins over the one on the arrival."""
    return candidate_country_process and frappe.db.get_value(
        "Candidate Country Process", candidate_country_process, "department"
    )


def get_hiring_type(candidate_country_process):
    """Overseas when the arrival comes from a Candidate Country Process, else Local."""
    return "Overseas" if candidate_country_process else "Local"


def get_job_applicant_designation(job_applicant):
    """The Job Applicant's Designation, or its One FM Designation when that is the only one filled."""
    row = job_applicant and frappe.db.get_value(
        "Job Applicant", job_applicant, ["designation", "one_fm_designation"], as_dict=True
    )
    if not row:
        return None
    return row.designation or row.one_fm_designation


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



