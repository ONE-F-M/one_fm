# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class EmployeeResignation(Document):
	def validate(self):
		self.set_allocations()
		self.set_supervisor()
		self.validate_employee_permissions()
		self.set_employee_allocation_details()
		self.validate_resignation_letter()

		# Enforce relieving_date explicitly for Supervisor before forwarding
		if self.get("workflow_state") in ("Pending Operations Manager", "Approved"):
			if not self.relieving_date or not self.resignation_initiation_date:
				frappe.throw(
					_("Resignation Initiation Date and Relieving Date are mandatory at this stage. The Supervisor must specify these before pushing to Operations Manager."),
					title=_("Missing Required Fields")
				)



		# Enforce Operations Manager and Offboarding Officer only during Managerial stages
		state = self.get("workflow_state")
		if state and state not in ("Draft", "Pending Relieving Date Correction"):
			if state in ("Pending Operations Manager", "Approved"):
				if not self.operations_manager and self.shift_working:
					frappe.throw(_("Please specify the <b>Operations Manager</b> before saving or submitting."))
				if not self.offboarding_officer:
					frappe.throw(_("Please specify the <b>Offboarding Officer</b> before saving or submitting."))

			# Enforce Supervisor Remarks once the resignation has moved past the
			# Supervisor's own review stage (mandatory_depends_on in the JSON is
			# client-side only in this Frappe version, so it must be backed up here).
			if state != "Pending Supervisor" and not self.supervisor_remarks:
				frappe.throw(_("Please provide Supervisor Remarks before proceeding."), title=_("Missing Remarks"))

			# Operations Manager Remarks only applies to shift-workers -- corporate
			# hires skip the Operations Manager stage entirely (direct Pending
			# Supervisor -> Approved transition), so Supervisor Remarks above already
			# covers their only reviewer.
			if state == "Approved" and self.shift_working and not self.operations_manager_remarks:
				frappe.throw(_("Please provide Operations Manager Remarks before approving."), title=_("Missing Remarks"))

		# Enforce replacement_required explicitly for Operations Manager / Approved.
		# Non-shift-workers skip the Operations Manager stage entirely (direct
		# Pending Supervisor -> Approved transition), so they're auto-exempted
		# rather than forced to answer -- they never see the field at all.
		if self.get("workflow_state") == "Approved":
			if not self.shift_working:
				self.replacement_required = "No"
			elif not self.replacement_required:
				frappe.throw(
					_("You must explicitly select Yes or No for 'Is a Replacement Required?' before you can approve and spawn a PMR."),
					title=_("Replacement Required")
				)

		self.validate_dates()

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
		if frappe.session.user in [self.supervisor, self.operations_manager, self.offboarding_officer]:
			return

		# Allow Operation Admin, T4 Admin, and Transportation Manager to edit replacement details in Pending Operations Manager state.
		# Restricted to just those fields server-side too -- the JS only locks the form
		# UI, which doesn't stop a direct save/API call from touching anything else.
		if self.get("workflow_state") == "Pending Operations Manager" and any(role in roles for role in ["Operation Admin", "T4 Admin", "Transportation Manager"]):
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

	def send_approval_notification(self):
		recipients = set()
		if getattr(self, "supervisor", None):
			recipients.add(self.supervisor)
			
		if getattr(self, "owner", None):
			recipients.add(self.owner)
			
		from frappe.utils.user import get_users_with_role
		offboarding_officers = get_users_with_role("Offboarding Officer")
		for user in offboarding_officers:
			recipients.add(user)

		subject = _("Employee Resignation Approved: {0}").format(self.name)
		message = _("The employee resignation {0} has been fully approved by the Operations Manager and is now ready for offboarding processing.").format(self.name)

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
def get_employee_resignation_details(employee):
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
			["site_supervisor", "operations_manager"], as_dict=True)
		if site_data:
			result["operations_manager"] = site_data.get("operations_manager")
			if site_data.get("site_supervisor"):
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

