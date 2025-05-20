# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from json import loads

import frappe
from frappe.utils import today, format_date
from frappe.desk.form.assign_to import add as add_assignment
from frappe.model.document import Document
from frappe import _

class MOM(Document):
	def autoname(self):
		formated_today_date = format_date(today(), 'dd-mm-yyyy')
		target_project_docs = frappe.db.count(self.doctype, filters={"project": self.project})
		# Format the name as `DD-MM-YYYY|Project|##`
		self.name = f"{formated_today_date}|{self.project}|{target_project_docs + 1:02d}"

	def validate(self):
		attendees_count = 0
		for attendee in self.attendees[:]:
			if attendee.attended_meeting:
				attendees_count = attendees_count + 1
			
		if self.issues == "Yes" and len(self.action) < 1:
			frappe.throw(_("Please add Action taken to the table."))

		self.validate_poc_and_general_attendance()

	def create_poc_check(self):
		"""
			Create a POC Check if all the rows in the attendees table in a MOM record are not checked as attended
		"""	
		table_checks  = [int(i.attended_meeting) for i in self.attendees]
		if not any(table_checks):
		#Create POC Check if no row in the POC table is marked
			poc_check = frappe._dict()
			poc_check.doctype = "POC Check"
			poc_check.project = self.project
			poc_check.site = self.site
			poc_check.supervisor = self.supervisor
			poc_check.supervisor_name = self.supervisor_name
			poc_check.mom = self.name
			attendees_list = []
			general_attendees_list = []
			for each in self.attendees:
				attendees_list.append({'poc_name':each.poc_name,'poc_designation':each.poc_designation})

			for attendees in self.general_attendance:
				general_attendees_list.append({'attendee_name':attendees.attendee_name})

			poc_check.general_attendees = general_attendees_list
			poc_check.mom_poc_table = attendees_list
			poc_check_doc = frappe.get_doc(poc_check)
			poc_check_doc.save()
			mom_user  = frappe.get_value("Employee",self.supervisor,'user_id')
			if mom_user:
				add_assignment({
						'doctype': "POC Check",
						'name': poc_check_doc.name,
						'assign_to': [mom_user],
						'description':f"Kindly fill and submit this document to update the POC details for Site: {self.site} and Project: {self.project}",
						"date": frappe.utils.getdate(),
						"priority": "Medium"
					})
				frappe.db.commit()
			frappe.msgprint(_(f"POC Check {poc_check_doc.name} Created!"),
                alert=True, indicator='green')


				
			
	def on_submit(self):
		self.create_poc_check()
		project_type = frappe.db.get_value("Project", self.project, "project_type")
		if project_type != "External":
			self.create_task_and_assign()
		else:
			if self.issues == "Yes":
				self.create_task_and_assign()
	
 
	def create_task_and_assign(self):
		if len(self.action) > 0:
			for issue in self.action:
				op_task = frappe.new_doc("Task")
				if not issue.subject and issue.description:
					op_task.subject = issue.description[:30]
				else:
					op_task.subject = issue.subject
				op_task.description = issue.description
				op_task.priority = issue.priority
				op_task.project = self.project 
				op_task.save(ignore_permissions=True)

				add_assignment({
					'doctype': "Task",
					'name': op_task.name,
					'assign_to': [issue.user],
					"date": issue.due_date,
					"priority": issue.priority if issue.priority in {"Low", "Medium", "High"} else "High"
				})

			frappe.db.commit()


	def validate_poc_and_general_attendance(self):
		is_attended = any(obj.attended_meeting for obj in self.attendees) or any(obj.attended_meeting for obj in self.general_attendance)
		if not is_attended:
			frappe.throw(_("At least one POC or General Attendance must be marked present."))
   

@frappe.whitelist()
def review_last_mom(mom,site):
	last_mom = frappe.db.get_list('MOM', filters={ 
		'name': ['!=', mom ],
		'site': site
	
	},
	order_by='date desc',
	page_length=1

	)
	if len(last_mom)>0:
		return frappe.get_doc('MOM',last_mom[0].name)

@frappe.whitelist()
def review_pending_actions(project):
	filters = {'project': project}
	data = frappe.db.sql("""
							SELECT task.subject AS subject, task.priority AS priority, task.description AS description, 
								todo.date AS due_date, todo.allocated_to AS user
							FROM `tabTask` AS task
							LEFT JOIN `tabToDo` AS todo ON task.name = todo.reference_name AND todo.reference_type = 'Task'
							WHERE (task.project = %(project)s) AND (task.status != 'Completed' AND task.status != 'Cancelled')
						""", filters, as_dict=1)
	return data

@frappe.whitelist()
def fetch_designation_of_users(list_of_users: list = []):
	try:
		return frappe.db.sql("""
							SELECT employee_name, designation from `tabEmployee`
							WHERE user_id IN %s
							""",(tuple(loads(list_of_users)), ) ,as_dict=1)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Error encountered while fetching users designation (MOM)")


@frappe.whitelist()
def get_project_users(project):
    doc = frappe.get_doc("Project", project)
    return [u.full_name for u in doc.users]
