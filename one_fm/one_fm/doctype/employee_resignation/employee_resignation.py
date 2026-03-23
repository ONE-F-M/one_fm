# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class EmployeeResignation(Document):
	def validate(self):
		self.set_supervisor()

	def before_save(self):
		self.set_supervisor()

	def set_supervisor(self):
		"""
		Automatically populate the Supervisor (User) field based on:
		1. Employee's Reports To → linked Employee's user_id
		2. Employee's Site → Operations Site's site_supervisor → their user_id
		3. Employee's Project → Project's project_manager → their user_id

		Does nothing if supervisor is already set or employee is not set.
		"""
		if not self.employee or self.supervisor:
			return

		# 1. Reports To
		reports_to = frappe.db.get_value("Employee", self.employee, "reports_to")
		if reports_to:
			user_id = frappe.db.get_value("Employee", reports_to, "user_id")
			if user_id:
				self.supervisor = user_id
				return

		# 2. Site Supervisor
		site = frappe.db.get_value("Employee", self.employee, "site")
		if site:
			site_supervisor = frappe.db.get_value("Operations Site", site, "site_supervisor")
			if site_supervisor:
				user_id = frappe.db.get_value("Employee", site_supervisor, "user_id")
				if user_id:
					self.supervisor = user_id
					return

		# 3. Project Manager
		project = frappe.db.get_value("Employee", self.employee, "project")
		if project:
			project_manager = frappe.db.get_value("Project", project, "project_manager")
			if project_manager:
				user_id = frappe.db.get_value("Employee", project_manager, "user_id")
				if user_id:
					self.supervisor = user_id

	def on_submit(self):
		if self.employee and self.relieving_date:
			frappe.db.set_value("Employee", self.employee, "relieving_date", self.relieving_date)

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

