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
				
				# Supervisor / HR should attach letter for manually added resignation
				if not row.resignation_letter and frappe.session.user != row.employee:
					emp_name = frappe.db.get_value("Employee", row.employee, "employee_name") or row.employee
					frappe.throw("Missing Resignation Letter for " + str(emp_name))

	def before_save(self):
		self.set_supervisor()
		
		# Enforce relieving_date explicitly for Supervisor before forwarding
		if self.get("workflow_state") in ("Pending Operations Manager", "Approved"):
			if not self.relieving_date:
				frappe.throw("<b>Relieving Date</b> is mandatory at this stage. The Supervisor must specify the final date before pushing to Operations Manager.")

		# Enforce replacement_required explicitly for Operations Manager
		if self.get("workflow_state") == "Approved" and not self.replacement_required:
			frappe.throw("You must explicitly select <b>Yes</b> or <b>No</b> for 'Is a Replacement Required?' before you can save or approve.")

	def set_supervisor(self):
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
		
		# Blank supervisor if ghost or completely empty
		self.supervisor = None

	def on_submit(self):
		if self.get("employees") and self.relieving_date:
			for row in self.employees:
				if row.employee:
					frappe.db.set_value("Employee", row.employee, "relieving_date", self.relieving_date)

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
				
			pmr.insert(ignore_permissions=True)
			
			frappe.msgprint(
				_("Project Manpower Request generated successfully: <a href='/app/project-manpower-request/{0}'><b>{0}</b></a> (Click to open)").format(pmr.name),
				title=_("PMR Created"),
				indicator="green"
			)
