# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class EmployeeResignation(Document):
	def validate(self):
		self.set_supervisor()
		self.validate_employees()
		self.validate_resignation_letters()

		# Enforce relieving_date explicitly for Supervisor before forwarding
		if self.get("workflow_state") in ("Pending Operations Manager", "Approved"):
			if not self.relieving_date or not self.resignation_initiation_date:
				frappe.throw(
					_("Resignation Initiation Date and Relieving Date are mandatory at this stage. The Supervisor must specify these before pushing to Operations Manager."),
					title=_("Missing Required Fields")
				)

		self.validate_dates()

	def validate_dates(self):
		if self.resignation_initiation_date and self.relieving_date:
			if self.relieving_date < self.resignation_initiation_date:
				frappe.throw(_("Relieving Date cannot be before Resignation Initiation Date."))

	def validate_employees(self):
		# Ensure all employees belong to the same project and designation
		if self.get("employees"):
			projects = set()
			designations = set()
			for row in self.employees:
				if not row.employee:
					continue
					
				emp_data = frappe.db.get_value("Employee", row.employee, ["project", "designation", "employee_name"], as_dict=True)
				if emp_data:
					# Validation: Project and Designation must exist to spawn PMR later
					if not emp_data.project:
						frappe.throw(_("Employee <b>{0} ({1})</b> has no <b>Project</b> assigned in their profile. Please update the Employee profile first.").format(emp_data.employee_name, row.employee))
					
					if not emp_data.designation:
						frappe.throw(_("Employee <b>{0} ({1})</b> has no <b>Designation</b> assigned in their profile. Please update the Employee profile first.").format(emp_data.employee_name, row.employee))

					projects.add(emp_data.project)
					designations.add(emp_data.designation)
					
			if len(projects) > 1:
				frappe.throw(_("All employees added to this collective resignation MUST belong to the exact same Project. You mixed: {0}").format(", ".join(projects)))
				
			if len(designations) > 1:
				frappe.throw(_("All employees added to this collective resignation MUST share the exact same Designation. You mixed: {0}").format(", ".join(designations)))
		
			# Set the master project and designation allocation to the shared values
			if projects:
				self.project_allocation = list(projects)[0]
			if designations:
				self.designation = list(designations)[0]

	def validate_resignation_letters(self):
		# We only strictly enforce attachments if the document is being submitted 
		# or if it's moving beyond the Draft phase to a supervisor.
		if self.docstatus == 0 and self.get("workflow_state") in (None, "Draft", ""):
			return

		if self.get("employees"):
			for row in self.employees:
				if not row.employee:
					continue
				
				# Mandatory for EVERYONE (Employee, Supervisor, HR)
				if not row.resignation_letter:
					emp_name = frappe.db.get_value("Employee", row.employee, "employee_name") or row.employee
					frappe.throw(_("Missing Resignation Letter for <b>{0}</b>. Please click the pencil edit icon ✏️ on their row and attach the file before submitting.").format(str(emp_name)), title=_("Missing Attachments"))

	def on_update(self):
		old_doc = self.get_doc_before_save()
		if not old_doc or old_doc.get("workflow_state") != self.workflow_state:
			self.sync_status_to_employees()
			
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
		from one_fm.api.v1.utils import resolve_active_user
		
		offboarding_officers = get_users_with_role("Offboarding Officer")
		for user in offboarding_officers:
			recipients.add(resolve_active_user(user))

		subject = _("Employee Resignation Approved: {0}").format(self.name)
		message = _("The employee resignation {0} has been fully approved by the Operations Manager and is now ready for offboarding processing.").format(self.name)

		if self.get("employees"):
			emp_list = []
			for row in self.employees:
				if row.employee:
					emp_name = frappe.db.get_value("Employee", row.employee, "employee_name") or row.employee
					emp_list.append(emp_name)
					# Optionally notify the employee directly if they have an active user ID
					user_id = frappe.db.get_value("Employee", row.employee, "user_id")
					if user_id:
						recipients.add(user_id)
			
			if emp_list:
				message += "<br><br>" + _("Employees involved:") + "<ul>"
				for emp in emp_list:
					message += "<li>{}</li>".format(emp)
				message += "</ul>"
				
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
		self.set_supervisor()
		
		# Enforce relieving_date explicitly for Supervisor before forwarding
		if self.get("workflow_state") in ("Pending Operations Manager", "Approved"):
			if not self.relieving_date:
				frappe.throw(
					_("Relieving Date is mandatory at this stage. The Supervisor must specify the final date before pushing to Operations Manager."),
					title=_("Missing Relieving Date")
				)

		# Enforce Operations Manager and Offboarding Officer only during Managerial stages
		state = self.get("workflow_state")
		if state and state not in ("Draft", "Pending Relieving Date Correction"):
			if state in ("Pending Operations Manager", "Approved"):
				if not self.operations_manager:
					frappe.throw(_("Please specify the <b>Operations Manager</b> before saving or submitting."))
				if not self.offboarding_officer:
					frappe.throw(_("Please specify the <b>Offboarding Officer</b> before saving or submitting."))

		# Enforce replacement_required explicitly for Operations Manager
		if self.get("workflow_state") == "Approved":
			if not self.replacement_required:
				frappe.throw(
					_("You must explicitly select Yes or No for 'Is a Replacement Required?' before you can save or approve."),
					title=_("Replacement Required")
				)

	def set_supervisor(self):
		# Only auto-resolve supervisor if it hasn't already been set manually
		if self.get("supervisor"):
			return
		
		# We base supervisor routing on the FIRST employee
		if not self.get("employees"):
			return
			
		first_emp = self.employees[0].employee
		if not first_emp:
			return

		# 1. Reports To
		reports_to = frappe.db.get_value("Employee", first_emp, "reports_to")
		if reports_to:
			user_id = frappe.db.get_value("Employee", reports_to, "user_id")
			if user_id and frappe.db.exists("User", user_id):
				self.supervisor = user_id
				return

		# 2. Site Supervisor
		site = frappe.db.get_value("Employee", first_emp, "site")
		if site:
			site_supervisor = frappe.db.get_value("Operations Site", site, "site_supervisor")
			if site_supervisor:
				user_id = frappe.db.get_value("Employee", site_supervisor, "user_id")
				if user_id and frappe.db.exists("User", user_id):
					self.supervisor = user_id
					return

		# 3. Project Manager
		project = frappe.db.get_value("Employee", first_emp, "project")
		if project:
			project_manager = frappe.db.get_value("Project", project, "project_manager")
			if project_manager:
				user_id = frappe.db.get_value("Employee", project_manager, "user_id")
				if user_id and frappe.db.exists("User", user_id):
					self.supervisor = user_id
					return
		
		self.supervisor = None

	def on_submit(self):
		self.sync_status_to_employees()
		if self.get("employees"):
			for row in self.employees:
				if row.employee:
					if row.resignation_letter:
						file_name = row.resignation_letter.split('/')[-1] if '/' in row.resignation_letter else row.resignation_letter
						
						if not frappe.db.exists("File", {"attached_to_doctype": "Employee", "attached_to_name": row.employee, "file_url": row.resignation_letter}):
							try:
								from frappe.utils.file_manager import save_url
								save_url(row.resignation_letter, file_name, "Employee", row.employee, "Home/Attachments", 1)
							except Exception as e:
								frappe.log_error(frappe.get_traceback(), "Error attaching resignation file to Employee")
					
					frappe.db.set_value("Employee", row.employee, {
						"resignation_date": self.resignation_initiation_date,
						"relieving_date": self.relieving_date,
						"current_resignation": self.name
					})

		if self.replacement_required == "Yes":
			pmr = frappe.new_doc("Project Manpower Request")
			pmr.reason = "Exit"
			pmr.employee_resignation = self.name
			pmr.priority = self.replacement_priority
			pmr.count = len(self.get("employees", []))
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
			
			for row in self.get("language_requirements"):
				new_row = pmr.append("language_requirements", {})
				row_dict = row.as_dict().copy()
				for field in ("name", "parent", "parentfield", "parenttype", "creation", "modified", "modified_by", "owner"):
					row_dict.pop(field, None)
				new_row.update(row_dict)
				
			for row in self.get("skill_requirements"):
				new_row = pmr.append("skill_requirements", {})
				row_dict = row.as_dict().copy()
				for field in ("name", "parent", "parentfield", "parenttype", "creation", "modified", "modified_by", "owner"):
					row_dict.pop(field, None)
				new_row.update(row_dict)
				
			for row in self.get("certification_requirements"):
				new_row = pmr.append("certification_requirements", {})
				row_dict = row.as_dict().copy()
				for field in ("name", "parent", "parentfield", "parenttype", "creation", "modified", "modified_by", "owner"):
					row_dict.pop(field, None)
				new_row.update(row_dict)
				
			pmr.workflow_state = "Draft"
			pmr.insert(ignore_permissions=True)
			frappe.db.set_value("Project Manpower Request", pmr.name, "workflow_state", "Draft")

	def on_trash(self):
		for row in self.get("employees", []):
			if row.employee:
				frappe.db.set_value("Employee", row.employee, {
					"resignation_status": "",
					"current_resignation": ""
				})

	def sync_status_to_employees(self):
		status = self.workflow_state or "Draft"
		for row in self.get("employees", []):
			if row.employee:
				update_data = {
					"resignation_status": status,
					"current_resignation": self.name,
					"resignation_date": self.resignation_initiation_date,
					"relieving_date": self.relieving_date,
				}
				if row.resignation_letter:
					update_data["resignation_letter_date"] = row.get("resignation_letter_date") or self.resignation_initiation_date
				frappe.db.set_value("Employee", row.employee, update_data, update_modified=False)
