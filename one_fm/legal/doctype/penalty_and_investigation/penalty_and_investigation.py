import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate

# Workflow states that count as an approved penalty when counting a repeat offence.
# "Completed" is where WI-001796's workflow ends; "Approved" was the end state of the
# definition exported before the criteria were written, so both are honoured until no
# record can be sitting in it.
APPROVED_STATES = ("Approved", "Completed")

# Offence level -> the Penalty Code's Penalty Level row, and the maximum level the
# matrix defines. A sixth offence keeps counting but is sanctioned as a fifth.
OFFENCE_LEVELS = ("1st", "2nd", "3rd", "4th", "5th")

# How far back a repeat offence is counted, measured from the incident.
LOOKBACK_DAYS = 365


class PenaltyAndInvestigation(Document):
	def validate(self):
		self.set_created_by()
		self.validate_penalty_code_is_active()
		self.validate_duplicate_penalty()
		self.calculate_offence_count()
		self.validate_workflow_transition()

	def set_created_by(self):
		"""Surface the raiser on the document (WI-001794).

		Frappe already records them in `owner`; this is the visible copy the BA's
		layout asks for, set once so it cannot drift from the real creator.
		"""
		if not self.created_by:
			self.created_by = self.owner or frappe.session.user

	def validate_penalty_code_is_active(self):
		"""A retired penalty code cannot be applied (WI-001794).

		Checked only when the code is being chosen, so that deactivating a code later
		does not make the penalties already issued under it unsaveable.
		"""
		if not self.applied_penalty_code:
			return

		if not (self.is_new() or self.has_value_changed("applied_penalty_code")):
			return

		if not frappe.db.get_value("Penalty Code", self.applied_penalty_code, "is_active"):
			frappe.throw(
				_("Penalty Code {0} is no longer active and cannot be applied.").format(
					frappe.bold(self.applied_penalty_code)
				)
			)

	def validate_workflow_transition(self):
		if not self.workflow_state:
			return

		old_state = self.get_db_value("workflow_state")
		if not old_state:
			return

		# Trim to handle trailing spaces in state names (e.g. "Pending Legal Investigation ")
		curr_state_trimmed = self.workflow_state.strip()
		old_state_trimmed = old_state.strip()

		if old_state_trimmed == "Pending Employee Response" and curr_state_trimmed == "Pending Supervisor Review":
			self._validate_employee_to_supervisor_transition()

		if old_state_trimmed == "Pending Supervisor Review" and curr_state_trimmed == "Pending HR Review":
			self._validate_supervisor_to_hr_transition()

		if old_state_trimmed == "Pending GM Decision" and curr_state_trimmed == "Pending Legal Investigation":
			if not self.general_manager_decision:
				frappe.throw(_("General Manager Decision is required before moving to Pending Legal Investigation"))

		if old_state_trimmed == "Pending HR Review" and curr_state_trimmed == "Pending GM Decision":
			if not self.hr_remarks or not self.hr_investigation_report:
				frappe.throw(_("HR Remarks and HR Investigation Report are required before moving to Pending GM Decision"))

	def _validate_employee_to_supervisor_transition(self):
		if not self.employee_remarks:
			frappe.throw(_("Employee Remarks are required before moving to Pending Supervisor Review"))

	def _validate_supervisor_to_hr_transition(self):
		if not self.supervisor_remarks or not self.supervisor_incident_report:
			frappe.throw(_("Supervisor Remarks and Supervisor Incident Report are required before moving to Pending HR Review"))

	def validate_duplicate_penalty(self):
		if not self.employee or not self.applied_penalty_code or not self.incident_date:
			return

		duplicate = frappe.db.exists(
			"Penalty And Investigation",
			{
				"employee": self.employee,
				"applied_penalty_code": self.applied_penalty_code,
				"incident_date": self.incident_date,
				"name": ["!=", self.name],
				"docstatus": ["!=", 2],
			},
		)

		if duplicate:
			frappe.throw(
				_("An active penalty investigation already exists for Employee {0} with Penalty Code {1} on {2}").format(
					self.employee, self.applied_penalty_code, self.incident_date
				)
			)

	def calculate_offence_count(self):
		if not self.applied_penalty_code:
			# WI-001795: a non-code deduction - uniform replacement, damage - is not a
			# repeat offence, so no history is consulted and the count reads zero
			# rather than carrying a figure from whenever a code was last selected.
			# Applied Level and Salary Deduction Days are deliberately left alone.
			self.offence_count = 0
			return

		if not self.employee or not self.incident_date:
			return

		# The rolling window runs back from the INCIDENT, not from today. Measuring it
		# from today mis-sanctioned any backdated penalty: an incident entered late
		# would count prior offences the incident itself predates, and drop ones that
		# were live when it happened.
		lookback_start = add_days(getdate(self.incident_date), -LOOKBACK_DAYS)

		# Only approved penalties count towards a repeat offence; drafts and cancelled
		# records are ignored (docstatus 1 excludes both).
		previous_count = frappe.db.count(
			"Penalty And Investigation",
			{
				"employee": self.employee,
				"workflow_state": ["in", APPROVED_STATES],
				"applied_penalty_code": self.applied_penalty_code,
				"incident_date": [">=", lookback_start],
				"name": ["!=", self.name],
				"docstatus": 1,
			},
		)

		# The current offence count is the previous count plus this one. The count is
		# never capped - a sixth offence reads as 6 - but the sanction reuses the
		# highest level the penalty matrix defines.
		self.offence_count = previous_count + 1
		level = min(self.offence_count, len(OFFENCE_LEVELS))
		self.applied_level = OFFENCE_LEVELS[level - 1]

		self.set_sanction_from_penalty_code()

	def set_sanction_from_penalty_code(self):
		"""Read the sanction for the applied level off the Penalty Code matrix."""
		penalty_code_doc = frappe.get_cached_doc("Penalty Code", self.applied_penalty_code)

		row = next(
			(
				r
				for r in penalty_code_doc.get("penalty_level") or []
				if r.offence_level == self.applied_level
			),
			None,
		)

		if not row:
			self.action_type = None
			self.penalty_category = None
			self.salary_deduction_days = 0
			self.salary_deduction_amount = 0
			return

		self.action_type = row.deduction_type
		self.salary_deduction_days = row.salary_deduction_days
		# Category mirrors the action for a code-driven penalty; the manual, code-less
		# path (Uniform / Damage) is WI-001795's.
		self.penalty_category = (
			row.deduction_type if row.deduction_type in ("Warning", "Salary Deduction") else None
		)
		# A warning carries no money. The amount stays read-only and is derived, so a
		# stale figure from an earlier level cannot survive a recalculation. flt, not
		# cint: the matrix's smallest deduction is half a day.
		if not flt(self.salary_deduction_days):
			self.salary_deduction_amount = 0


@frappe.whitelist()
def get_incident_site_project(employee: str, incident_date: str | None = None) -> dict:
	"""Return the operations site and project to pre-fill for a penalty's employee.

	The form needs the site/project the employee was rostered to on the incident
	date. Reading Employee Schedule (roster data) straight from the client would
	force every penalty-raiser to hold read permission on the whole roster; this
	method instead confirms the caller may raise a penalty, then returns only the
	two fields - nothing else of the schedule is exposed.
	"""
	# Only someone allowed to create a Penalty And Investigation may look this up.
	if not frappe.has_permission("Penalty And Investigation", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if not employee:
		return {}

	site = project = None

	# The working roster row for that day wins; get_all is used deliberately so the
	# lookup does not depend on the caller having Employee Schedule read permission.
	if incident_date:
		schedule = frappe.get_all(
			"Employee Schedule",
			filters={
				"employee": employee,
				"date": incident_date,
				"employee_availability": "Working",
			},
			fields=["site", "project"],
			limit=1,
		)
		if schedule:
			site = schedule[0].site
			project = schedule[0].project

	# Fall back to the Employee master when there is no working roster row.
	if not site and not project:
		emp = frappe.db.get_value("Employee", employee, ["site", "project"], as_dict=True)
		if emp:
			site = emp.site
			project = emp.project

	return {"site": site, "project": project}


@frappe.whitelist()
def get_penalty_count():
	user = frappe.session.user
	count = frappe.db.count("Penalty And Investigation", {
		"employee_user": user,
		"docstatus": ["!=", 2]
	})

	return {
		"value": count,
		"fieldtype": "Int",
		"route": ["List", "Penalty And Investigation", "", {"docstatus": ["!=", 2]}]
	}


@frappe.whitelist()
def get_last_penalty_status():
	user = frappe.session.user
	latest_record = frappe.db.get_list(
		"Penalty And Investigation",
		filters={"employee_user": user},
		fields=["name", "workflow_state"],
		order_by="creation desc",
		limit=1,
	)

	if not latest_record:
		return {"value": _("None"), "fieldtype": "Data", "route": ["New", "Penalty And Investigation", ""]}

	record = latest_record[0]
	return {
		"value": f'{record.workflow_state}',
		"fieldtype": "Data",
		"route": ["Form", "Penalty And Investigation", record.name],
	}
