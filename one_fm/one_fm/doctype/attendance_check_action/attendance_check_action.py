# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, getdate, nowdate

# Grace period (in days) auto-applied for both purchasing methods.
DEFAULT_GRACE_PERIOD = 14

# Statuses that resolve the action's grace period. Once the status is any of
# these, the employee's attendance checks revert to normal manual generation
# (no more auto-fill from the source check). "Draft" is the only active state.
GRACE_ENDING_STATUSES = ("Purchased", "Closed", "Deadline Breached")

# Penalty Code applied when an employee fails to purchase a new mobile within
# the grace period (per the disciplinary policy this is strictly code "18").
UNPURCHASED_MOBILE_PENALTY_CODE = "18"

# System-generated Supervisor Remarks stamped on the auto-created penalty
# (wrapped in _() at the call site so it translates to the job user's language).
UNPURCHASED_MOBILE_PENALTY_REMARKS = "Automated penalty issued due to failure to purchase a new mobile within the grace period."


class AttendanceCheckAction(Document):
	def before_naming(self):
		# Populate the naming inputs (employee, start_date) from the source
		# Attendance Check before the name is generated, so the
		# "HR-ACA-{employee}_{start_date}" expression always resolves.
		self.populate_from_attendance_check()

	def before_insert(self):
		# Guard against duplicate lifecycles: a new action can only be created
		# once the employee's previous one has been Closed.
		self.populate_from_attendance_check()
		self.validate_no_open_action()

	def validate(self):
		self.populate_from_attendance_check()
		self.set_grace_and_deadline()
		self.validate_deadline_breached_status()

	def validate_deadline_breached_status(self):
		"""Guard the manual "Deadline Breached" transition.

		Per the acceptance criteria a breach is only valid once the current date
		*strictly* exceeds the Deadline Date (i.e. the whole deadline day, end of
		day, has elapsed). The status is set manually by the assigned user — this
		simply prevents flagging a breach while the employee is still within the
		grace window.
		"""
		if self.status != "Deadline Breached":
			return

		if not self.deadline_date or getdate(nowdate()) <= getdate(self.deadline_date):
			frappe.throw(
				_("Status can only be set to 'Deadline Breached' after the Deadline Date ({0}) has passed.").format(
					frappe.format(self.deadline_date, {"fieldtype": "Date"}) if self.deadline_date else _("not set")
				)
			)

	def validate_no_open_action(self):
		"""Block creating a new Attendance Check Action when the employee already
		has one that is still blocking.

		A record keeps blocking a new lifecycle until its Deadline Date has passed
		or it has been Closed (see ``get_open_action_for_employee``). This prevents
		duplicate overlapping actions inside the same grace window while still
		letting a new issue raised after the deadline start its own action.
		"""
		if not self.employee:
			return

		open_action = get_open_action_for_employee(self.employee, exclude=self.name)
		if open_action:
			frappe.throw(
				_("An active Attendance Check Action ({0}) already exists for {1}. Close it, or wait for its Deadline Date to pass, before creating a new one.").format(
					open_action, self.employee_name or self.employee
				)
			)

	def populate_from_attendance_check(self):
		"""Fetch Employee, Action and Start Date (= Attendance Check Date) from the source issue."""
		if not self.attendance_check:
			return

		source = frappe.db.get_value(
			"Attendance Check",
			self.attendance_check,
			["employee", "date", "action"],
			as_dict=True,
		)
		if not source:
			return

		if not self.employee:
			self.employee = source.employee
		if not self.start_date:
			self.start_date = source.date
		if not self.action:
			self.action = source.action

	def set_grace_and_deadline(self):
		"""Keep Grace Period and Deadline Date mathematically consistent.

		- Selecting a Purchasing Method defaults the Grace Period to 14 days.
		- Deadline Date is treated as the source of truth when set: Grace Period
		  is derived from it (Deadline Date - Start Date).
		- Otherwise the Deadline Date is derived from Start Date + Grace Period.
		"""
		# Auto-set 14-day grace for Self Purchase / Company Loan when not already set.
		if self.purchasing_method and not self.grace_period:
			self.grace_period = DEFAULT_GRACE_PERIOD

		if self.start_date:
			if self.deadline_date:
				self.grace_period = date_diff(self.deadline_date, self.start_date)
			elif self.grace_period:
				self.deadline_date = add_days(self.start_date, self.grace_period)

		if self.grace_period and self.grace_period < 0:
			frappe.throw(_("Grace Period cannot be negative. Deadline Date must be on or after the Start Date."))

	def before_update_after_submit(self):
		# The Deadline Date is editable after submission (allow_on_submit) so an
		# operator can grant an extension on a locked record. Recompute the Grace
		# Period from the new Deadline Date so the two stay consistent — validate()
		# does not run on after-submit updates, so this must be done explicitly.
		self.set_grace_and_deadline()

	def on_submit(self):
		# "Closed" is the submitted state.
		self.db_set("status", "Closed")

		# When the action is closed with "Has not Purchased a New Mobile" ticked,
		# the employee failed to resolve the hardware issue within the grace period.
		# Raise the disciplinary penalty automatically, in the background, once this
		# submission has committed (enqueue_after_commit) so the job reads a
		# persisted, Closed record.
		if self.has_not_purchased_a_new_mobile:
			frappe.enqueue(
				method="one_fm.one_fm.doctype.attendance_check_action.attendance_check_action.create_penalty_for_unpurchased_mobile",
				queue="short",
				enqueue_after_commit=True,
				action_name=self.name,
			)


def get_open_action_for_employee(employee, exclude=None, on_date=None):
	"""Return the name of an Attendance Check Action that still blocks creating a
	new one for the employee, or None.

	An action keeps blocking a fresh lifecycle until either its Deadline Date has
	*passed* (the current date is strictly after the deadline) or it has been
	Closed. This lets a genuinely new issue raised after the deadline start its
	own action, while preventing duplicate overlapping actions inside the same
	grace window. An action with no Deadline Date set is treated as not-yet-passed
	and therefore keeps blocking.

	Args:
		employee (str): Employee to check.
		exclude (str, optional): Attendance Check Action name to exclude (self).
		on_date (str | date, optional): Date to test the deadline against
			(defaults to today).
	"""
	if not employee:
		return None

	on_date = getdate(on_date) if on_date else getdate(nowdate())

	filters = {
		"employee": employee,
		"status": ["!=", "Closed"],
		"docstatus": ["<", 2],
	}
	if exclude:
		filters["name"] = ["!=", exclude]

	candidates = frappe.get_all(
		"Attendance Check Action",
		filters=filters,
		fields=["name", "deadline_date"],
	)
	for candidate in candidates:
		if not candidate.deadline_date or getdate(candidate.deadline_date) >= on_date:
			return candidate.name

	return None


def get_active_grace_action(employee, on_date):
	"""Return the open Attendance Check Action whose grace window covers ``on_date``.

	The grace period is active only while the action is still in "Draft" (and not
	cancelled) and ``on_date`` falls within the inclusive window
	``start_date <= on_date <= deadline_date``. Once the assigned user moves the
	status to Purchased, Closed or Deadline Breached, the grace period ends and
	the employee's attendance checks revert to normal manual generation.

	Args:
		employee (str): Employee to check.
		on_date (str | date): The date to test against the grace window
			(the Attendance Check's ``date``).

	Returns:
		frappe._dict | None: ``{"name", "attendance_check"}`` of the active
		action, or ``None`` when no grace period is active.
	"""
	if not employee or not on_date:
		return None

	on_date = getdate(on_date)

	return frappe.db.get_value(
		"Attendance Check Action",
		{
			"employee": employee,
			"status": "Draft",
			"docstatus": ["<", 2],
			"start_date": ["<=", on_date],
			"deadline_date": [">=", on_date],
		},
		["name", "attendance_check"],
		as_dict=True,
	)


def create_penalty_for_unpurchased_mobile(action_name):
	"""Background job: raise a Penalty And Investigation for a closed action whose
	employee failed to purchase a new mobile within the grace period.

	Triggered from ``AttendanceCheckAction.on_submit`` (after commit) only when the
	"Has not Purchased a New Mobile" checkbox is ticked. The generated penalty is
	created as a draft so the standard disciplinary workflow can proceed from there.

	The penalty is populated per the disciplinary policy:
	  - Applied Penalty Code is strictly "18".
	  - Incident Date is the closure date (today).
	  - Issuer is the Employee linked to the HR Settings "Attendance Check Action
	    User" (a User); left blank if that user has no Employee record.
	  - Location and Department are fetched from the employee's master profile.
	  - Supervisor Remarks carries the system-generated message.
	  - The originating Attendance Check Action is linked back for traceability.

	Runs with ``ignore_permissions=True``: this is system automation and the closing
	operator (e.g. Payroll Operator) has no create permission on the penalty doctype.
	"""
	try:
		action = frappe.get_doc("Attendance Check Action", action_name)

		# Re-validate the trigger conditions on the persisted record — guards against
		# a stale enqueue if the checkbox was cleared before the commit landed.
		if not action.has_not_purchased_a_new_mobile or action.status != "Closed":
			return

		if not action.employee:
			return

		# Idempotency: never raise a second penalty for the same action (e.g. on an
		# amendment or a re-run of the job).
		if frappe.db.exists(
			"Penalty And Investigation",
			{"attendance_check_action": action.name, "docstatus": ["!=", 2]},
		):
			return

		# Resolve the configured action User to their Employee record for the Issuer
		# (the Issuer field links to Employee, the setting stores a User). Leave the
		# Issuer blank if no Employee is linked to that user — the record is still raised.
		action_user = frappe.db.get_single_value("HR Settings", "attendance_check_action_user")
		issuer = frappe.db.get_value("Employee", {"user_id": action_user}, "name") if action_user else None

		# Location and Department come from the employee's master profile.
		employee_details = frappe.db.get_value(
			"Employee", action.employee, ["site", "department"], as_dict=True
		) or frappe._dict()

		penalty = frappe.new_doc("Penalty And Investigation")
		penalty.employee = action.employee
		penalty.issuer = issuer
		penalty.applied_penalty_code = UNPURCHASED_MOBILE_PENALTY_CODE
		penalty.incident_date = nowdate()
		penalty.issuance_date = nowdate()
		penalty.location = employee_details.site
		penalty.department = employee_details.department
		penalty.supervisor_remarks = _(UNPURCHASED_MOBILE_PENALTY_REMARKS)
		penalty.attendance_check_action = action.name
		penalty.insert(ignore_permissions=True)
		# No explicit commit: the background-job runner commits on success. Committing
		# here would also break test isolation by persisting past the test rollback.
	except Exception:
		frappe.log_error(
			title="Attendance Check Action Penalty Creation Failed",
			message=f"Attendance Check Action: {action_name}\n{frappe.get_traceback()}",
		)
