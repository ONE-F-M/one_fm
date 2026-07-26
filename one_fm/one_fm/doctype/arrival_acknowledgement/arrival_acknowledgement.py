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


class ArrivalAcknowledgement(Document):
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

	def notify_onboarding_officer_of_acknowledgement(self):
		"""Notify the assigned Onboarding Officer every time a department acknowledges,
		including whatever orientation/site details that department collected along
		the way (see DEPARTMENT_REQUIRED_FIELDS) -- Operations gets Site Allocation
		plus Orientation Date/Time, General Services gets Orientation Date/Time.
		"""
		if not self.arrival_and_deployment:
			return

		onboarding_officer = frappe.db.get_value("Arrival and Deployment", self.arrival_and_deployment, "onboarding_officer")
		if not onboarding_officer:
			return

		officer_email = frappe.db.get_value("User", onboarding_officer, "email")
		if not officer_email:
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
				recipients=[officer_email],
				subject=f"{self.department} Acknowledged Arrival: {self.candidate_name}",
				message=message,
			)
		except Exception as e:
			frappe.log_error(title="Arrival Acknowledgement Notification Error", message=f"Notify failed for {self.name}: {str(e)}")


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
