# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.hr.utils import EmployeeBoardingController
from frappe.model.mapper import get_mapped_doc

class IncompleteTaskError(frappe.ValidationError): pass

class OnboardEmployee(EmployeeBoardingController):
	def validate(self):
		# remove the task if linked before submitting the form
		if self.amended_from:
			for activity in self.activities:
				activity.task = ''

	def validate_employee_creation(self):
		if self.docstatus != 1:
			frappe.throw(_("Submit this to create the Employee record"))
		else:
			for activity in self.activities:
				if not activity.required_for_employee_creation:
					continue
				else:
					task_status = frappe.db.get_value("Task", activity.task, "status")
					if task_status not in ["Completed", "Cancelled"]:
						frappe.throw(_("All the mandatory Task for employee creation hasn't been done yet."), IncompleteTaskError)

	def on_submit(self):
		# create the project for the given employee onboarding
		# project_name = _(self.doctype) + " : "
		# if self.doctype == "Employee Onboarding":
		# 	project_name += self.job_applicant
		# else:
		# 	project_name += self.employee
		# project = frappe.get_doc({
		# 		"doctype": "Project",
		# 		"project_name": project_name,
		# 		"expected_start_date": self.date_of_joining if self.doctype == "Employee Onboarding" else self.resignation_letter_date,
		# 		"department": self.department,
		# 		"company": self.company
		# 	}).insert(ignore_permissions=True)
		# self.db_set("project", project.name)
		self.db_set("boarding_status", "Pending")
		self.reload()
		# self.create_task_and_notify_user()

	def create_task_and_notify_user(self):
		# create the task for the given project and assign to the concerned person
		for activity in self.activities:
			if activity.task:
				continue

			task = frappe.get_doc({
					"doctype": "Task",
					"project": self.project,
					"subject": activity.activity_name + " : " + self.employee_name,
					"description": activity.description,
					"department": self.department,
					"company": self.company,
					"task_weight": activity.task_weight
				}).insert(ignore_permissions=True)
			activity.db_set("task", task.name)
			users = [activity.user] if activity.user else []
			if activity.role:
				user_list = frappe.db.sql_list('''select distinct(parent) from `tabHas Role`
					where parenttype='User' and role=%s''', activity.role)
				users = users + user_list

				if "Administrator" in users:
					users.remove("Administrator")

			# assign the task the users
			if users:
				self.assign_task_to_users(task, set(users))

	def assign_task_to_users(self, task, users):
		for user in users:
			args = {
				'assign_to' 	:	user,
				'doctype'		:	task.doctype,
				'name'			:	task.name,
				'description'	:	task.description or task.subject,
				'notify':	self.notify_users_by_email
			}
			assign_to.add(args)

	def on_cancel(self):
		# delete task project
		# for task in frappe.get_all("Task", filters={"project": self.project}):
		# 	frappe.delete_doc("Task", task.name, force=1)
		# frappe.delete_doc("Project", self.project, force=1)
		# self.db_set('project', '')
		# for activity in self.activities:
		# 	activity.db_set("task", "")
		pass

	def on_update_after_submit(self):
		self.create_task_and_notify_user()

@frappe.whitelist()
def make_employee(source_name, target_doc=None):
	doc = frappe.get_doc("Employee Onboarding", source_name)
	doc.validate_employee_creation()
	def set_missing_values(source, target):
		target.personal_email = frappe.db.get_value("Job Applicant", source.job_applicant, "email_id")
		target.status = "Active"
	doc = get_mapped_doc("Employee Onboarding", source_name, {
			"Employee Onboarding": {
				"doctype": "Employee",
				"field_map": {
					"first_name": "employee_name",
					"employee_grade": "grade",
				}}
		}, target_doc, set_missing_values)
	return doc
