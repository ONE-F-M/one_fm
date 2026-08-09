# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

# States at which the employee/actor is still reviewing -- i.e. the states a
# resignation departs FROM via a reviewer's own transition. Used to figure out
# which step's remarks (Negotiation / Performance / Complaints) must exist
# before the document is allowed to leave that state.
REVIEW_STATES = (
	"Pending Line Manager",
	"Pending Supervisor",
	"Pending T4 Admin",
	"Pending Janitorial Head Supervisor",
	"Pending Security Manager",
	"Pending Project Manager",
)

# Friendly label for a departed stage, used only when writing a Remarks
# History log entry.
STAGE_LABELS = {
	"Pending Line Manager": "Line Manager",
	"Pending Supervisor": "Supervisor",
	"Pending T4 Admin": "T4 Admin",
	"Pending Janitorial Head Supervisor": "Janitorial Head Supervisor",
	"Pending Security Manager": "Security Manager",
	"Pending Project Manager": "Project Manager",
}


class EmployeeResignation(Document):
	def validate(self):
		self.set_allocations()
		self.set_current_salary()
		self.classify_t4_route()
		self.set_supervisor()
		self.set_t4_admin()
		self.set_cleaning_head_supervisor()
		self.set_security_manager()
		self.set_project_manager()
		self.validate_employee_permissions()
		self.set_employee_allocation_details()
		self.validate_resignation_letter()
		self.validate_step_remarks()

		# Enforce relieving_date explicitly before forwarding out of any review stage
		if self.get("workflow_state") in REVIEW_STATES + ("Approved",):
			if not self.relieving_date or not self.resignation_initiation_date:
				frappe.throw(
					_("Resignation Initiation Date and Relieving Date are mandatory at this stage."),
					title=_("Missing Required Fields")
				)

		# Enforce Project Manager and Offboarding Officer during the final stages.
		# Project Manager only applies to the Shift path -- Non-Shift's Line
		# Manager approves directly into "Approved" without ever routing through
		# Project Manager at all. Offboarding Officer applies to both branches.
		state = self.get("workflow_state")
		if state in ("Pending Project Manager", "Approved"):
			if not self.project_manager and self.shift_working:
				frappe.throw(_("Please specify the <b>Project Manager</b> before saving or submitting."))
			if not self.offboarding_officer:
				frappe.throw(_("Please specify the <b>Offboarding Officer</b> before saving or submitting."))

		# Enforce replacement_required explicitly for Project Manager / Approved.
		# Non-shift-workers never reach the Project Manager stage at all (Line
		# Manager is the sole final approver for that branch), so they're
		# auto-exempted rather than forced to answer.
		if self.get("workflow_state") == "Approved":
			if not self.shift_working:
				self.replacement_required = "No"
			elif not self.replacement_required:
				frappe.throw(
					_("You must explicitly select Yes or No for 'Is a Replacement Required?' before you can approve and spawn a PMR."),
					title=_("Replacement Required")
				)

		# Once a replacement is confirmed as needed, Nationality/Gender/Salary
		# feed the auto-created PMR directly (create_pmr()) -- enforce them
		# before approving so the PMR is never spawned with blanks.
		if self.replacement_required == "Yes" and self.get("workflow_state") in ("Pending Project Manager", "Approved"):
			missing = [
				label for value, label in (
					(self.replacement_nationality, _("Replacement Nationality")),
					(self.replacement_gender, _("Replacement Gender")),
					(self.replacement_salary, _("Replacement Salary")),
				) if not value
			]
			if missing:
				frappe.throw(
					_("Please specify {0} before approving, since a replacement is required.").format(", ".join(missing)),
					title=_("Missing Replacement Details")
				)

		self.validate_dates()

	def validate_step_remarks(self):
		"""Every review stage must record its Negotiation / Performance / Complaints
		remarks before the document can move past that stage -- remarks are
		entered before the transition fires, never after. Performance,
		Complaints, and Resignation Negotiation Remarks are shared, reused
		fields (not a per-stage history), so on a successful transition the
		filled-in remarks are appended to the read-only Remarks History log
		and the live fields are cleared -- otherwise the next stage's actor
		could advance without ever writing their own remarks, since the
		previous stage's text would still be sitting there satisfying the
		check. The log itself keeps the full chain, in order."""
		state = self.get("workflow_state")
		if not state or state in ("Draft", "Pending Relieving Date Correction", "Withdrawn"):
			return

		before = self.get_doc_before_save()
		departing_state = before.get("workflow_state") if before else None

		if departing_state and departing_state != state and departing_state in REVIEW_STATES:
			if not (self.negotiation_remarks and self.performance_remarks and self.complaints_remarks):
				frappe.throw(
					_("Please record Negotiation, Performance, and Complaints remarks for the <b>{0}</b> stage before proceeding.").format(departing_state),
					title=_("Missing Remarks")
				)

			entry = "\n".join([
				f"{STAGE_LABELS.get(departing_state, departing_state)}:",
				f"Performance: {self.performance_remarks}",
				f"Complaints: {self.complaints_remarks}",
				f"Negotiation: {self.negotiation_remarks}",
			])
			self.remarks_log = f"{self.remarks_log}\n\n{entry}" if self.remarks_log else entry

			self.negotiation_remarks = None
			self.performance_remarks = None
			self.complaints_remarks = None

	def validate_dates(self):
		if self.resignation_initiation_date and self.relieving_date:
			if self.relieving_date < self.resignation_initiation_date:
				frappe.throw(_("Relieving Date cannot be before Resignation Initiation Date."))

	def validate_employee_permissions(self):
		# Standard employees can only resign themselves, unless they are acting in an authorized workflow capacity
		roles = frappe.get_roles()
		authorized_roles = ["HR Manager", "System Manager"]
		
		if any(role in roles for role in authorized_roles):
			return
			
		# Allow workflow assignees to modify the document
		if frappe.session.user in [
			self.supervisor, self.t4_admin, self.cleaning_head_supervisor,
			self.security_manager, self.project_manager, self.offboarding_officer,
		]:
			return

		# Allow Operation Admin, T4 Admin, and Transportation Manager to edit replacement details in Pending Project Manager state.
		# Restricted to just those fields server-side too -- the JS only locks the form
		# UI, which doesn't stop a direct save/API call from touching anything else.
		if self.get("workflow_state") == "Pending Project Manager" and any(role in roles for role in ["Operation Admin", "T4 Admin", "Transportation Manager"]):
			allowed_fields = {"replacement_required", "replacement_priority", "replacement_nationality", "replacement_gender", "replacement_salary"}
			before = self.get_doc_before_save()
			if before:
				for df in self.meta.fields:
					if df.fieldname in allowed_fields:
						continue
					if df.fieldtype in ("Table", "Table MultiSelect"):
						before_employees = [d.employee for d in (before.get(df.fieldname) or [])]
						after_employees = [d.employee for d in (self.get(df.fieldname) or [])]
						if before_employees != after_employees:
							frappe.throw(_("You can only edit the replacement decision fields at this stage."), frappe.PermissionError)
						continue
					if self.get(df.fieldname) != before.get(df.fieldname):
						frappe.throw(_("You can only edit the replacement decision fields at this stage."), frappe.PermissionError)
			return

		linked_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user})
		if not linked_employee:
			frappe.throw(_("Your user account is not linked to an Employee profile. You cannot initiate resignations."))

		if self.employee and self.employee != linked_employee:
			frappe.throw(_("You can only submit a resignation for yourself."), frappe.PermissionError)

	def set_employee_allocation_details(self):
		# Set project/designation from the resigning employee's profile (needed to spawn PMR later)
		if not self.employee:
			return

		emp_data = frappe.db.get_value("Employee", self.employee, ["project", "designation", "employee_name"], as_dict=True)
		if not emp_data:
			return

		if not emp_data.project:
			frappe.throw(_("Employee <b>{0} ({1})</b> has no <b>Project</b> assigned in their profile. Please update the Employee profile first.").format(emp_data.employee_name, self.employee))

		if not emp_data.designation:
			frappe.throw(_("Employee <b>{0} ({1})</b> has no <b>Designation</b> assigned in their profile. Please update the Employee profile first.").format(emp_data.employee_name, self.employee))

		self.project_allocation = emp_data.project
		self.designation = emp_data.designation

	def validate_resignation_letter(self):
		# We only strictly enforce the attachment if the document is being submitted
		# or if it's moving beyond the Draft phase to a supervisor.
		if self.docstatus == 0 and self.get("workflow_state") in (None, "Draft", ""):
			return

		if not self.employee:
			return

		if not self.resignation_letter:
			emp_name = frappe.db.get_value("Employee", self.employee, "employee_name") or self.employee
			frappe.throw(_("Missing Resignation Letter for <b>{0}</b>. Please attach the file before submitting.").format(str(emp_name)), title=_("Missing Attachments"))

	def on_update(self):
		self.sync_status_to_employee()
		old_doc = self.get_doc_before_save()
		if not self.is_new():
			if old_doc and old_doc.get("workflow_state") != "Approved" and self.get("workflow_state") == "Approved":
				self.send_approval_notification()
				self.notify_employee_app(
					_("Resignation Approved"),
					_("Your resignation has been approved."),
				)
			if old_doc and old_doc.get("workflow_state") != "Pending Relieving Date Correction" and self.get("workflow_state") == "Pending Relieving Date Correction":
				self.assign_employee_for_relieving_date_correction()
				self.notify_employee_app(
					_("Date Change Requested"),
					_("Your supervisor has requested a correction to your resignation dates."),
				)
			if old_doc and old_doc.get("workflow_state") == "Pending Relieving Date Correction" and self.get("workflow_state") != "Pending Relieving Date Correction":
				self.clear_employee_correction_assignment()

	def clear_employee_correction_assignment(self):
		"""The employee's ToDo from assign_employee_for_relieving_date_correction()
		is created manually, not via an Assignment Rule -- so Frappe's
		assignment-rule engine won't clear it (it only clears assignments its
		own rule created), and its mere presence blocks the engine from ever
		reassigning this document again. Remove it explicitly once the
		correction is resubmitted, so the Pending Supervisor/T4 Admin/Line
		Manager assignment rule can correctly take back over."""
		if not self.employee:
			return
		user_id = frappe.db.get_value("Employee", self.employee, "user_id")
		if not user_id:
			return

		from frappe.desk.form.assign_to import remove as remove_assignment
		for todo in frappe.get_all("ToDo", filters={
			"reference_type": self.doctype, "reference_name": self.name,
			"allocated_to": user_id, "status": "Open"
		}, fields=["allocated_to"]):
			try:
				remove_assignment(self.doctype, self.name, todo.allocated_to)
			except Exception:
				pass

	def notify_employee_app(self, title, body):
		"""Push a mobile-app notification straight to the employee's phone via
		FCM, alongside the email notifications above -- best-effort only,
		since a missing/stale device token shouldn't block the save (the
		underlying helper already swallows its own errors)."""
		if not self.employee:
			return
		from one_fm.utils import send_push_notification
		send_push_notification(self.employee, title, body, data={
			"type": "resignation_update",
			"resignation": self.name,
			"workflow_state": self.get("workflow_state"),
		})

	def assign_employee_for_relieving_date_correction(self):
		"""Whoever requested the correction (Supervisor/T4 Admin/etc.) isn't
		who needs to act here -- it's the employee's own relieving date to
		fix. Reassign to them instead of leaving it with whoever triggered
		the transition (Frappe defaults to assigning the acting user when
		nothing else is explicitly assigned)."""
		if not self.employee:
			return
		user_id = frappe.db.get_value("Employee", self.employee, "user_id")
		if not user_id:
			return

		from frappe.desk.form.assign_to import add as assign_to, remove as remove_assignment

		for todo in frappe.get_all("ToDo", filters={
			"reference_type": self.doctype, "reference_name": self.name, "status": "Open"
		}, fields=["allocated_to"]):
			if todo.allocated_to != user_id:
				try:
					remove_assignment(self.doctype, self.name, todo.allocated_to)
				except Exception:
					pass

		if not frappe.db.exists("ToDo", {
			"reference_type": self.doctype, "reference_name": self.name,
			"allocated_to": user_id, "status": "Open"
		}):
			assign_to({
				"assign_to": [user_id],
				"doctype": self.doctype,
				"name": self.name,
				"description": _("Please correct your Relieving Date and resubmit."),
			})

			from one_fm.processor import sendemail
			sendemail(
				recipients=[user_id],
				subject=_("Action Required: Correct Relieving Date for {0}").format(self.name),
				message=_("A correction to your Relieving Date has been requested for your resignation <b>{0}</b>. Please update it and resubmit.").format(self.name),
				reference_doctype=self.doctype,
				reference_name=self.name
			)

	def send_approval_notification(self):
		recipients = set()
		for field in ("supervisor", "t4_admin", "cleaning_head_supervisor", "security_manager", "project_manager", "owner"):
			value = getattr(self, field, None)
			if value:
				recipients.add(value)

		from frappe.utils.user import get_users_with_role
		offboarding_officers = get_users_with_role("Offboarding Officer")
		for user in offboarding_officers:
			recipients.add(user)

		subject = _("Employee Resignation Approved: {0}").format(self.name)
		message = _("The employee resignation {0} has been fully approved and is now ready for offboarding processing.").format(self.name)

		if self.employee:
			emp_name = frappe.db.get_value("Employee", self.employee, "employee_name") or self.employee
			message += "<br><br>" + _("Employee:") + " " + emp_name

			# Optionally notify the employee directly if they have an active user ID
			user_id = frappe.db.get_value("Employee", self.employee, "user_id")
			if user_id:
				recipients.add(user_id)

		if self.relieving_date:
			from frappe.utils import formatdate
			message += "<br>" + _("<b>Approved Relieving Date:</b> {0}").format(formatdate(self.relieving_date))

		if recipients:
			from one_fm.processor import sendemail
			sendemail(
				recipients=list(recipients),
				subject=subject,
				message=message,
				reference_doctype=self.doctype,
				reference_name=self.name
			)


	def before_save(self):
		self.set_allocations()

	def set_allocations(self):
		if not self.employee:
			return
		emp = frappe.db.get_value("Employee", self.employee, ["site", "project", "department", "shift", "custom_operations_role_allocation", "shift_working"], as_dict=True)
		if emp:
			self.site_allocation = emp.site
			self.project_allocation = emp.project
			self.department = emp.department
			self.shift_allocation = emp.shift
			self.operations_role_allocation = emp.custom_operations_role_allocation
			self.shift_working = emp.shift_working or 0

		if not self.shift_working:
			self.shift_category = None
		else:
			# Department is a generic "Operations - ONEFM" bucket for every
			# shift-working employee, T4 or not -- Project Allocation is what
			# actually distinguishes them (e.g. "T4 Airport").
			self.shift_category = "T4" if self.project_allocation and "t4" in self.project_allocation.lower() else "Operations"

	def classify_t4_route(self):
		"""Which T4 sub-team this resignation routes to, derived from the employee's
		Designation (a keyword match, not a manually-picked field)."""
		if self.shift_category != "T4":
			self.t4_route = None
			return

		designation = (self.designation or "").lower()
		if "security" in designation:
			self.t4_route = "Security"
		elif "janitor" in designation or "clean" in designation:
			self.t4_route = "Janitorial"
		else:
			self.t4_route = "Passenger-Customer Service"

	def set_current_salary(self):
		if not self.employee:
			return
		self.current_salary = frappe.db.get_value(
			"Salary Structure Assignment",
			{"employee": self.employee, "docstatus": 1, "from_date": ["<=", frappe.utils.today()]},
			"base",
			order_by="from_date desc",
		)

	def set_supervisor(self):
		# Only auto-resolve supervisor if it hasn't already been set manually
		if self.get("supervisor"):
			return

		if not self.employee:
			return

		from one_fm.utils import get_approver
		approver_emp = get_approver(self.employee)
		if approver_emp:
			user_id = frappe.db.get_value("Employee", approver_emp, "user_id")
			if user_id and frappe.db.exists("User", user_id):
				self.supervisor = user_id
				return

		self.supervisor = None

	def set_t4_admin(self):
		if self.shift_category != "T4" or self.get("t4_admin"):
			return
		self.t4_admin = self._first_user_with_role("T4 Admin")

	def set_cleaning_head_supervisor(self):
		if self.t4_route != "Janitorial" or self.get("cleaning_head_supervisor"):
			return
		self.cleaning_head_supervisor = self._first_user_with_role("Janitorial Head Supervisor")

	def set_security_manager(self):
		if self.t4_route != "Security" or self.get("security_manager"):
			return
		self.security_manager = self._first_user_with_role("Security Manager")

	def set_project_manager(self):
		# Applies to both T4 and Operations branches once they reach Project Manager.
		if self.get("project_manager"):
			return
		if not self.project_allocation:
			return

		# Project's own "Project Manager" field links to Employee, not User --
		# resolve it to the user account before assigning.
		pm_employee = frappe.db.get_value("Project", self.project_allocation, "project_manager")
		if pm_employee:
			user_id = frappe.db.get_value("Employee", pm_employee, "user_id")
			if user_id and frappe.db.exists("User", user_id):
				self.project_manager = user_id
				return

		self.project_manager = self._first_user_with_role("Project Manager")

	@staticmethod
	def _first_user_with_role(role):
		from frappe.utils.user import get_users_with_role
		users = get_users_with_role(role)
		return users[0] if users else None

	def on_submit(self):
		self.sync_status_to_employee()
		if self.employee:
			if self.resignation_letter:
				file_name = self.resignation_letter.split('/')[-1] if '/' in self.resignation_letter else self.resignation_letter

				if not frappe.db.exists("File", {"attached_to_doctype": "Employee", "attached_to_name": self.employee, "file_url": self.resignation_letter}):
					try:
						from frappe.utils.file_manager import save_url
						save_url(self.resignation_letter, file_name, "Employee", self.employee, "Home/Attachments", is_private=1)
					except Exception as e:
						frappe.log_error("Error attaching resignation file to Employee", str(e))

			frappe.db.set_value("Employee", self.employee, {
				"resignation_date": self.resignation_initiation_date,
				"resignation_letter_date": self.resignation_initiation_date,
				"relieving_date": self.relieving_date,
				"reason_for_leaving": self.reason_for_exit,
				"current_resignation": self.name
			})

		if self.replacement_required == "Yes":
			self.create_pmr()

	def create_pmr(self):
		pmr = frappe.new_doc("Project Manpower Request")
		pmr.reason = "Exit"
		pmr.employee_resignation = self.name
		pmr.priority = self.replacement_priority
		pmr.count = 1
		pmr.employment_type = self.employment_type
		pmr.designation = self.designation
		pmr.department = self.department
		pmr.ojt_days = self.ojt_days
		pmr.project_allocation = self.project_allocation
		pmr.site_allocation = self.site_allocation
		pmr.shift_allocation = self.shift_allocation
		pmr.operations_role_allocation = self.operations_role_allocation
		pmr.gender = self.replacement_gender
		pmr.nationality = self.replacement_nationality
		pmr.salary = self.replacement_salary
		pmr.deployment_date = self.relieving_date
		pmr.workflow_state = "Draft"
		pmr.insert()
		frappe.db.set_value("Project Manpower Request", pmr.name, "workflow_state", "Draft")
		# Write backlink so PMR's Connections panel shows this resignation with count 1
		frappe.db.set_value("Employee Resignation", self.name, "project_manpower_request", pmr.name)

		self.notify_pmr_owner_for_review(pmr.name)

	def notify_pmr_owner_for_review(self, pmr_name):
		"""Neither T4 Admin nor Project Manager fills in Recruiter/ERF
		(that's the recruiter's job once it's in their queue), but someone
		has to review the auto-created Draft and click "Submit to
		Recruiter" -- assign and notify whoever raised it so it doesn't
		just sit there unnoticed. T4 Admin for the T4 branch; Project
		Manager otherwise, since Operations has no T4-Admin-equivalent
		actor of its own."""
		owner = self.t4_admin or self.project_manager
		if not owner:
			return
		from frappe.desk.form.assign_to import add as assign_to

		assign_to({
			"assign_to": [owner],
			"doctype": "Project Manpower Request",
			"name": pmr_name,
			"description": _("Replacement approved for {0} -- please review this draft Project Manpower Request and submit it to the recruiter.").format(self.name),
		})

		from one_fm.processor import sendemail
		sendemail(
			recipients=[owner],
			subject=_("Action Required: Submit PMR {0} to Recruiter").format(pmr_name),
			message=_("A replacement Project Manpower Request <b>{0}</b> was auto-created for <b>{1}</b>. Please review it and submit it to the recruiter.").format(pmr_name, self.name),
			reference_doctype="Project Manpower Request",
			reference_name=pmr_name
		)

	def on_trash(self):
		if self.employee:
			frappe.db.set_value("Employee", self.employee, {
				"resignation_status": "",
				"current_resignation": ""
			})

	def sync_status_to_employee(self):
		if not self.employee:
			return
		status = self.workflow_state or "Draft"
		update_data = {
			"resignation_status": status,
			"current_resignation": self.name,
			"resignation_date": self.resignation_initiation_date,
			"resignation_letter_date": self.resignation_initiation_date,
			"relieving_date": self.relieving_date,
			"reason_for_leaving": self.reason_for_exit,
		}
		frappe.db.set_value("Employee", self.employee, update_data, update_modified=False)


@frappe.whitelist()
def get_employee_resignation_details(employee: str = None):
	"""Secure backend fetch to bypass frontend permission limits for restricted roles."""
	if not employee:
		return {}

	emp_data = frappe.db.get_value("Employee", employee, 
		["project", "department", "designation", "site", "employment_type", "shift", "custom_operations_role_allocation", "employee_name", "reports_to", "shift_working"], 
		as_dict=True)

	if not emp_data:
		return {}

	result = emp_data.copy()

	# Fetch Supervisor User ID
	if result.get("reports_to"):
		result["supervisor_id"] = frappe.db.get_value("Employee", result.get("reports_to"), "user_id")

	# Fetch Site Details
	if result.get("site"):
		site_data = frappe.db.get_value("Operations Site", result.get("site"),
			["site_supervisor"], as_dict=True)
		if site_data and site_data.get("site_supervisor"):
			result["site_supervisor_id"] = frappe.db.get_value("Employee", site_data.get("site_supervisor"), "user_id")

	return result


@frappe.whitelist()
def get_autocomplete_options() -> dict:
	"""Fetch all genders and nationalities for the replacement_gender/replacement_nationality Autocomplete fields."""
	if not frappe.has_permission("Employee Resignation", "read"):
		frappe.throw(_("Not permitted to access resignation details."), frappe.PermissionError)

	genders = frappe.get_all("Gender", fields=["name"], order_by="name asc")
	nationalities = frappe.get_all("Nationality", fields=["name"], order_by="name asc")

	return {
		"nationalities": [n.name for n in nationalities if n.name],
		"genders": [g.name for g in genders if g.name]
	}

