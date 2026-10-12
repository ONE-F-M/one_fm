# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

DEPARTMENT_ROLES = {
	"Transportation": ("Transportation Manager",),
	"General Services": ("Accommodation User",),
	"Finance": ("Finance User",),
	"Warehouse": ("Warehouse Supervisor",),
	"Operations": ("Operation Admin", "T4 Admin"),
}

# Extra fields a department must fill in (manual entry, directly on the form) before
# it can acknowledge -- General Services/Operations get write access to just these
# fields (see the DocType's own permissions + mandatory_depends_on on each field).
DEPARTMENT_REQUIRED_FIELDS = {
	"General Services": ("orientation_date", "orientation_time"),
	"Operations": ("site_allocation", "orientation_date", "orientation_time"),
}

# Tick on Arrival and Deployment that decides whether the department mailbox is emailed
DEPARTMENT_MAILBOX_FIELDS = {
	"Transportation": "email_transportation_mailbox",
	"General Services": "email_general_services_mailbox",
	"Finance": "email_finance_mailbox",
	"Warehouse": "email_warehouse_mailbox",
	"Operations": "email_operations_mailbox",
}


class ArrivalAcknowledgement(Document):
	def before_insert(self):
		self.set_candidate_job_details()

	def after_insert(self):
		if self.visa_copy and not attach_file_copy(self.visa_copy, self.doctype, self.name, "visa_copy"):
			self.db_set("visa_copy", None, update_modified=False)
		if self.department != "Warehouse":
			self.notify_department_email()

	def validate(self):
		"""mandatory_depends_on is client-side only in this Frappe version -- it's never
		evaluated by _get_missing_mandatory_fields() server-side, so enforce it here too,
		same as Arrival and Deployment's own validate() backs up its mandatory_depends_on
		fields.

		Skipped on initial creation: assign_support_departments() creates this record
		with these fields still blank, to be filled in later by the department -- only
		a subsequent save (the department actually entering the values, or trying to
		save without them) needs to be blocked.
		"""
		if self.is_new():
			return
		for fieldname in DEPARTMENT_REQUIRED_FIELDS.get(self.department, ()):
			if not self.get(fieldname):
				frappe.throw(_("{0} is mandatory for {1}.").format(frappe.unscrub(fieldname), self.department))

	def on_update(self):
		old_status = self.get_doc_before_save().get("status") if self.get_doc_before_save() else None
		if self.status == "Acknowledged" and old_status != "Acknowledged":
			self.notify_onboarding_officer_of_acknowledgement()
		if self.department == "Operations" and self.status == "Acknowledged":
			self.share_project_with_warehouse()

	def notify_onboarding_officer_of_acknowledgement(self):
		"""Notify the assigned Onboarding Officer every time a department acknowledges,
		including whatever orientation/site details that department collected along
		the way (see DEPARTMENT_REQUIRED_FIELDS) -- Operations gets Site Allocation
		plus Orientation Date/Time, General Services gets Orientation Date/Time.
		"""
		if not self.arrival_and_deployment:
			return

		officers = frappe.db.get_value(
			"Arrival and Deployment",
			self.arrival_and_deployment,
			["onboarding_officer", "second_onboarding_officer"],
		)
		officer_emails = [
			email
			for email in (frappe.db.get_value("User", officer, "email") for officer in officers if officer)
			if email
		]
		if not officer_emails:
			return

		from frappe.utils import escape_html

		details = ""
		if self.department == "Operations":
			details = (
				f"<li><b>Site Allocation:</b> {escape_html(self.site_allocation) if self.site_allocation else 'N/A'}</li>"
				f"<li><b>Orientation Date:</b> {self.orientation_date or 'N/A'}</li>"
				f"<li><b>Orientation Time:</b> {self.orientation_time or 'N/A'}</li>"
			)
		elif self.department == "General Services":
			details = (
				f"<li><b>Orientation Date:</b> {self.orientation_date or 'N/A'}</li>"
				f"<li><b>Orientation Time:</b> {self.orientation_time or 'N/A'}</li>"
			)

		message = (
			f"<p>Dear Onboarding Officer,</p>"
			f"<p><b>{escape_html(self.department)}</b> has acknowledged the arrival of "
			f"<b>{escape_html(self.candidate_name)}</b>.</p>"
		)
		if details:
			message += f"<ul>{details}</ul>"
		message += (
			f"<p>Please review the "
			f"<a href='/app/arrival-acknowledgement/{self.name}'>Arrival Acknowledgement</a> for full details.</p>"
		)

		try:
			frappe.enqueue(
				method=frappe.sendmail,
				queue="short",
				recipients=officer_emails,
				subject=f"{self.department} Acknowledged Arrival: {self.candidate_name}",
				message=message,
			)
		except Exception as e:
			frappe.log_error(title="Arrival Acknowledgement Notification Error", message=f"Notify failed for {self.name}: {str(e)}")

	def set_candidate_job_details(self):
		"""Copy the candidate's designation, and the visa for Transportation."""
		candidate_country_process, visa_copy = frappe.db.get_value(
			"Arrival and Deployment", self.arrival_and_deployment, ["candidate_country_process", "visa_copy"]
		)
		if self.department == "Transportation":
			self.visa_copy = visa_copy
		if not candidate_country_process:
			return

		job_applicant = frappe.db.get_value(
			"Candidate Country Process", candidate_country_process, "job_applicant"
		)
		if job_applicant:
			self.designation = frappe.db.get_value("Job Applicant", job_applicant, "one_fm_designation")

	def share_project_with_warehouse(self):
		"""Give Warehouse the project from the site Operations allocated, and email the warehouse mailbox when it changes."""
		warehouse_name = frappe.db.get_value(
			"Arrival Acknowledgement",
			{"arrival_and_deployment": self.arrival_and_deployment, "department": "Warehouse"},
		)
		if not warehouse_name:
			return

		warehouse = frappe.get_doc("Arrival Acknowledgement", warehouse_name)
		if warehouse.project == self.project:
			return
		warehouse.db_set("project", self.project)
		warehouse.notify_department_email()

	def notify_department_email(self):
		"""Email the department mailbox when its box is ticked on the arrival, with the visa for Transportation."""
		mailbox_ticked = frappe.db.get_value(
			"Arrival and Deployment", self.arrival_and_deployment, DEPARTMENT_MAILBOX_FIELDS[self.department]
		)
		department_email = mailbox_ticked and get_arrival_department_email(self.department)
		if not department_email:
			return

		from frappe.utils import escape_html, formatdate

		assigned_to_name = frappe.db.get_value("User", self.assigned_to, "full_name")
		details = [
			(_("Candidate"), self.candidate_name),
			(_("Designation"), self.designation),
			(_("Arrival Date"), formatdate(self.arrival_date)),
			(_("Arrival Time"), self.arrival_time),
			(_("Flight"), " ".join(filter(None, [self.airline, self.flight_number]))),
			(_("Assigned To"), assigned_to_name),
		]
		if self.project:
			details.append((_("Project"), self.project))
		rows = "".join(
			f"<li><b>{label}:</b> {escape_html(str(value or _('N/A')))}</li>" for label, value in details
		)
		link_label = _("Open Arrival Acknowledgement {0}").format(self.name)
		message = (
			f"<p>{_('Dear {0} Team,').format(escape_html(self.department))}</p>"
			f"<ul>{rows}</ul>"
			f"<p><a href='/app/arrival-acknowledgement/{self.name}'>{link_label}</a></p>"
		)
		frappe.sendmail(
			recipients=[department_email],
			subject=_("{0} Arrival on {1}: {2}").format(
				self.department, formatdate(self.arrival_date), self.candidate_name
			),
			message=message,
			attachments=[{"file_url": self.visa_copy}] if self.visa_copy else None,
			reference_doctype=self.doctype,
			reference_name=self.name,
		)


def attach_file_copy(file_url, doctype, name, fieldname):
	"""Attach an existing file to another record so its readers can open it.
	Returns False when there is no File record for the URL or the file is missing on disk."""
	file_name = frappe.db.get_value("File", {"file_url": file_url})
	if not file_name:
		return False
	file = frappe.get_doc("File", file_name)
	if not file.exists_on_disk():
		return False
	file.create_attachment_copy(doctype, name, fieldname)
	return True


def get_arrival_department_email(department):
	"""The department's mailbox from Hiring Settings."""
	return frappe.db.get_value(
		"Arrival Department Email", {"parenttype": "Hiring Settings", "department": department}, "email"
	)


@frappe.whitelist()
def acknowledge(name: str):
	doc = frappe.get_doc("Arrival Acknowledgement", name)
	required_roles = DEPARTMENT_ROLES.get(doc.department, ())
	roles = frappe.get_roles()

	if "System Manager" not in roles and not any(role in roles for role in required_roles):
		frappe.throw(_("Only users with the {0} role can acknowledge this.").format(" or ".join(required_roles)))

	if doc.status == "Acknowledged":
		return doc.status

	for fieldname in DEPARTMENT_REQUIRED_FIELDS.get(doc.department, ()):
		if not doc.get(fieldname):
			frappe.throw(_("Please fill in and save {0} before acknowledging.").format(frappe.unscrub(fieldname)))

	doc.status = "Acknowledged"
	doc.acknowledged_by = frappe.session.user
	doc.acknowledged_on = frappe.utils.now_datetime()
	doc.save()
	return doc.status


@frappe.whitelist()
def confirm_arrival(name: str, outcome: str):
	"""Transportation-only: once Transportation has acknowledged the pickup assignment,
	they separately confirm whether the candidate actually arrived. This drives
	Arrival and Deployment's workflow_state to Joined/Did Not Arrive on their behalf,
	reusing everything already wired to that (clearing other departments'
	assignments, syncing CCP status, recalculating the CCP timeline, notifying the
	recruiter).

	Transportation Manager has a real role-permission grant on Arrival and
	Deployment (see the DocType's own permissions, restricted to workflow_state via
	permlevel) scoped by has_permission() on that doctype to just the record where
	they're the assigned transportation contact -- exactly the record
	create_arrival_acknowledgement() routed to them, so this always matches in the
	legitimate flow. Deliberately still doesn't use
	frappe.model.workflow.apply_workflow(): the explicit role check above
	(mirroring what the transition's "allowed" role would enforce) plus the guards
	on doc.status/doc.arrival_confirmation already cover what it would validate,
	without coupling this to the Workflow doctype's own transition configuration.
	"""
	if outcome not in ("Arrived", "Did Not Arrive"):
		frappe.throw(_("Invalid arrival outcome."))

	doc = frappe.get_doc("Arrival Acknowledgement", name)

	if doc.department != "Transportation":
		frappe.throw(_("Arrival confirmation only applies to the Transportation department."))

	roles = frappe.get_roles()
	if "System Manager" not in roles and "Transportation Manager" not in roles:
		frappe.throw(_("Only Transportation Manager can confirm arrival."))

	if doc.status != "Acknowledged":
		frappe.throw(_("Please acknowledge before confirming arrival."))

	if doc.arrival_confirmation:
		return doc.arrival_confirmation

	doc.arrival_confirmation = outcome
	doc.save()

	ard = frappe.get_doc("Arrival and Deployment", doc.arrival_and_deployment)
	if ard.get("workflow_state") == "Pending Support Departments":
		ard.workflow_state = "Joined" if outcome == "Arrived" else "Did Not Arrive"
		ard.save()

	return doc.arrival_confirmation


def _run_bulk(names, fn, title):
	names = frappe.parse_json(names)
	failures = []
	for name in names:
		try:
			fn(name)
		except Exception as e:
			failures.append(f"{name}: {e}")
			frappe.clear_last_message()
	if failures:
		frappe.msgprint(
			_("Some records could not be processed:") + "<br>" + "<br>".join(failures),
			title=title,
			indicator="orange",
		)


@frappe.whitelist()
def bulk_acknowledge(names: str):
	"""Acknowledge multiple records in one go -- e.g. every candidate arriving on the
	same day, filtered by Arrival Date in the list view. Records whose department
	requires orientation/site fields must already have them filled in and saved
	individually first; any that don't are reported back as failures.
	"""
	_run_bulk(names, lambda name: acknowledge(name), _("Bulk Acknowledge"))


@frappe.whitelist()
def bulk_confirm_arrival(names: str, outcome: str):
	"""Confirm the same Arrived/Did Not Arrive outcome for multiple Transportation
	records at once -- e.g. everyone arriving the same day who's already been
	acknowledged.
	"""
	_run_bulk(names, lambda name: confirm_arrival(name, outcome), _("Bulk Confirm Arrival"))


def send_daily_acknowledgement_reminders():
	"""Daily nudge for any department that hasn't acknowledged yet -- replaces the
	reminder Arrival and Deployment used to send off its own boolean ack fields
	(dropped along with those fields in favour of this doctype's own status).

	Scoped to arrival_and_deployment.workflow_state == "Pending Support Departments"
	to match clear_support_assignments(), which already clears every department's
	ToDo (including Warehouse/General Services) the moment the record reaches
	"Joined" -- nagging after that point would contradict that existing signal.
	"""
	pending = frappe.get_all(
		"Arrival Acknowledgement",
		filters={"status": "Not Acknowledged"},
		fields=["name", "department", "assigned_to", "arrival_and_deployment"],
	)
	if not pending:
		return

	active_ards = set(frappe.get_all(
		"Arrival and Deployment",
		filters={
			"name": ["in", list({p.arrival_and_deployment for p in pending})],
			"workflow_state": "Pending Support Departments",
		},
		pluck="name",
	))

	for ack in pending:
		if ack.arrival_and_deployment not in active_ards or not ack.assigned_to:
			continue
		user_email = frappe.db.get_value("User", ack.assigned_to, "email")
		if not user_email:
			continue
		try:
			frappe.enqueue(
				method=frappe.sendmail,
				queue="short",
				recipients=[user_email],
				subject=f"Reminder: Action Required for {ack.arrival_and_deployment}",
				message=(
					f"<p>Dear {ack.department} Team,</p>"
					f"<p>Please note that the Arrival Acknowledgement "
					f"<a href='/app/arrival-acknowledgement/{ack.name}'>{ack.name}</a> "
					f"for {ack.arrival_and_deployment} is pending your acknowledgement.</p>"
					f"<p>Kindly review and acknowledge it at your earliest convenience.</p>"
				),
			)
		except Exception as e:
			frappe.log_error(title="Arrival Acknowledgement Reminder Error", message=f"Reminder failed for {ack.name}: {str(e)}")


def has_permission(doc, ptype=None, user=None, **kwargs):
	"""
	Access to an Arrival Acknowledgement is scoped by department role, not by who
	happens to be named in its assigned_to field -- so anyone holding the role for
	that department (e.g. Warehouse Supervisor) can see and acknowledge it, even if
	they weren't the specific individual assigned when the record was created.

	Each department role only has a plain read grant at the permission-table level
	(see the DocType's own permissions), which would otherwise let e.g. every
	Warehouse Supervisor read every OTHER department's records too. This hook denies
	that back unless the row's own department matches a role the user holds.

	Recruiter and Offboarding Officer see every department's records regardless (view
	across the board, matching their oversight role), but neither can acknowledge --
	acknowledge() below only accepts the matching department role or System Manager,
	so granting Recruiter "write" here doesn't let them approve anything: every field
	that actually changes on acknowledge (status, acknowledged_by, acknowledged_on) is
	read_only and can only move through that whitelisted method.
	"""
	user = user or frappe.session.user
	if user == "Administrator":
		return None

	roles = frappe.get_roles(user)
	if any(role in roles for role in ("System Manager", "HR Manager", "Onboarding Officer", "Recruiter", "Offboarding Officer")):
		return None

	required_roles = DEPARTMENT_ROLES.get(doc.department, ())
	if any(role in roles for role in required_roles):
		return None

	return False
