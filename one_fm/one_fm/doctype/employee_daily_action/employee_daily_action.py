# Copyright (c) 2025, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate,add_days
from one_fm.utils import  get_approver

class EmployeeDailyAction(Document):
	def validate(self):
		self.validate_manager()
		self.fetch_todos()


	def fetch_todos(self):
		""" Fetch all the todos for the employee for the current date """

		if not self.todays_plan_and_accomplishments: #If created from console
			todays_todos = frappe.db.get_all("ToDo", {"allocated_to": self.employee_email, "date": self.date},['reference_name', 'reference_type', 'name', 'status','description','type'])
			for todo in todays_todos:
				row = self.append("todays_plan_and_accomplishments")
				row.todo = todo.name
				row.todo_type = todo.type
				row.reference_type = todo.reference_type
				row.reference = todo.reference_name
				row.planned = 0
				row.description = todo.description
				row.completed = 1 if todo.status != "Open" else 0

		if not self.tomorrows_plan: #If created from console
			tomorrows_todos = frappe.db.get_all("ToDo", {"allocated_to": self.employee_email, "date": add_days(getdate(self.date),1)},['reference_name', 'reference_type', 'name', 'status','description','type'])
			for todo in tomorrows_todos:
				row = self.append("tomorrows_plan")
				row.todo = todo.name
				row.description = todo.description
				row.todo_type = todo.type
				row.reference_type = todo.reference_type
				row.reference = todo.reference_name


	def create_blockers(self):
		"Create blockers for the employee from the blockers table"
		for blocker in self.blocker_table:
			blocker_doc = frappe.new_doc("Blocker")
			blocker_doc.user = self.employee_email
			blocker_doc.assigned_to = self.manager_email
			blocker_doc.priority = blocker.priority
			blocker_doc.date = self.date
			blocker_doc.status = "Open"
			blocker_doc.blocker_details = blocker.problem
			blocker_doc.reference_doctype = self.doctype
			blocker_doc.reference_name = self.name
			blocker_doc.save(ignore_permissions=True)
			frappe.db.commit()

	def  validate_manager(self):
		"""Ensure that a manager is set from the shift,site or reports to field """
		reports_to = get_approver(self.employee)
		if not reports_to:
			frappe.throw(f"No Reports to set for {self.employee_name}")
		self.reports_to = reports_to



	def on_submit(self):
		self.create_blockers()
