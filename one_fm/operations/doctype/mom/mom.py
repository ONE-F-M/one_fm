# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
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
		self.sync_tasks_from_tables()

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
				parts = attendees.attendee_name.split()
				first_name = parts[0]
				last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
				general_attendees_list.append({'first_name': first_name, 'last_name': last_name})

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
		if self.project_type != "External":
			self.create_task_and_assign()
		else:
			self.create_poc_check()
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
				op_task.custom_mom = self.name

				# Clear and append child table rows properly
				op_task.custom_assigned_to = []
				if issue.user:
					op_task.append("custom_assigned_to", {
						"user": issue.user
					})
				op_task.flags.ignore_links = True
				op_task.flags.ignore_workflow = True
				op_task.save(ignore_permissions=True)

				if issue.user:
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

	def sync_tasks_from_tables(self):
		if self.docstatus != 0:
			return

		# Sync last_action table
		for row in self.last_action:
			self._sync_row_to_task(row, is_last_action=True)

		# Sync pending_actions table
		for row in self.pending_actions:
			self._sync_row_to_task(row, is_last_action=False)

	def _sync_row_to_task(self, row, is_last_action=False):
		if not row.task:
			# Create new Task
			task = frappe.new_doc("Task")
			task.project = self.project
			task.subject = row.subject or (row.description[:30] if row.description else _("MOM Task"))
			task.description = row.description
			task.priority = row.priority or "Medium"
			task.status = row.status or "Open"
			task.exp_end_date = row.due_date
			task.custom_mom = (self.last_mom_name or self.name) if is_last_action else self.name
			
			if row.user:
				task.append("custom_assigned_to", {"user": row.user})
			
			task.flags.ignore_links = True
			task.flags.ignore_workflow = True
			task.save(ignore_permissions=True)
			row.task = task.name
		else:
			# Update existing Task if any field changed
			task = frappe.get_doc("Task", row.task)
			changed = False
			
			if task.subject != row.subject and row.subject:
				task.subject = row.subject
				changed = True
			if task.description != row.description:
				task.description = row.description
				changed = True
			if task.priority != row.priority and row.priority:
				task.priority = row.priority
				changed = True
			if task.status != row.status and row.status:
				task.status = row.status
				task.workflow_state = row.status
				if row.status == "Completed":
					task.completed_by = frappe.session.user
					task.completed_on = today()
				changed = True
			if task.exp_end_date != row.due_date:
				task.exp_end_date = row.due_date
				changed = True
			
			# Check user assignment
			assigned_users = [d.user for d in task.custom_assigned_to]
			if row.user and (len(assigned_users) != 1 or assigned_users[0] != row.user):
				task.custom_assigned_to = []
				task.append("custom_assigned_to", {"user": row.user})
				changed = True
			elif not row.user and assigned_users:
				task.custom_assigned_to = []
				changed = True
				
			if changed:
				task.flags.ignore_links = True
				old_get_workflow = task.meta.get_workflow
				task.meta.get_workflow = lambda: None
				try:
					task.save(ignore_permissions=True)
				finally:
					task.meta.get_workflow = old_get_workflow
   
@frappe.whitelist()
def review_last_internal_mom(mom,project):
	last_mom = frappe.db.get_list('MOM', filters={ 
		'name': ['!=', mom ],
		'project': project
	
	},
	order_by='date desc',
	page_length=1

	)
	if len(last_mom)>0:
		return frappe.get_doc('MOM',last_mom[0].name)


@frappe.whitelist()
def review_last_external_mom(mom,site):
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
def review_pending_actions(project: str):
	from frappe.query_builder import DocType

	Task = DocType("Task")
	ToDo = DocType("ToDo")

	data = (
		frappe.qb.from_(Task)
		.left_join(ToDo)
		.on(
			(Task.name == ToDo.reference_name)
			& (ToDo.reference_type == "Task")
			& (ToDo.status == "Open")
		)
		.select(
			Task.name.as_("task"),
			Task.subject.as_("subject"),
			Task.status.as_("status"),
			Task.priority.as_("priority"),
			Task.description.as_("description"),
			ToDo.date.as_("due_date"),
			ToDo.allocated_to.as_("user"),
		)
		.where(Task.project == project)
		.where(Task.status.notin(["Completed", "Cancelled"]))
	).run(as_dict=True)

	return data

@frappe.whitelist()
def mark_task_as_done(task_name: str):
    if not frappe.db.exists("Task", task_name):
        frappe.throw(_("Task {0} does not exist").format(task_name))

    task = frappe.get_doc("Task", task_name)
    task.check_permission("write")

    frappe.db.set_value("Task", task_name, {
        "workflow_state": "Completed",
        "status": "Completed",
        "completed_by": frappe.session.user,
        "completed_on": today(),
    })

    from frappe.query_builder import DocType
    ToDo = DocType("ToDo")
    open_todos = (
        frappe.qb.from_(ToDo)
        .select(ToDo.name)
        .where(ToDo.reference_type == "Task")
        .where(ToDo.reference_name == task_name)
        .where(ToDo.status == "Open")
    ).run(as_dict=True)

    for todo in open_todos:
        frappe.db.set_value("ToDo", todo.name, "status", "Closed")

    frappe.db.commit()

    return {"success": True, "task": task_name}

@frappe.whitelist()
def review_last_actions(last_mom_name: str = None, project: str = None):
	"""Fetch all Tasks created by the last MOM with their live status from Task + ToDo."""
	if not last_mom_name:
		return []

	from frappe.query_builder import DocType

	Task = DocType("Task")
	ToDo = DocType("ToDo")

	data = (
		frappe.qb.from_(Task)
		.left_join(ToDo)
		.on(
			(Task.name == ToDo.reference_name)
			& (ToDo.reference_type == "Task")
			& (ToDo.status == "Open")
		)
		.select(
			Task.name.as_("task"),
			Task.subject.as_("subject"),
			Task.status.as_("status"),
			Task.priority.as_("priority"),
			Task.description.as_("description"),
			ToDo.date.as_("due_date"),
			ToDo.allocated_to.as_("user"),
		)
		.where(Task.custom_mom == last_mom_name)
	).run(as_dict=True)

	# Fallback: if no tasks are explicitly linked, find tasks in the project matching the last MOM's action subjects/descriptions
	if not data and last_mom_name:
		if frappe.db.exists("MOM", last_mom_name):
			last_mom = frappe.get_doc("MOM", last_mom_name)
			if last_mom.action:
				subjects = [a.subject for a in last_mom.action if a.subject]
				descriptions = [a.description for a in last_mom.action if a.description]
				
				if subjects or descriptions:
					query = (
						frappe.qb.from_(Task)
						.left_join(ToDo)
						.on(
							(Task.name == ToDo.reference_name)
							& (ToDo.reference_type == "Task")
							& (ToDo.status == "Open")
						)
						.select(
							Task.name.as_("task"),
							Task.subject.as_("subject"),
							Task.status.as_("status"),
							Task.priority.as_("priority"),
							Task.description.as_("description"),
							ToDo.date.as_("due_date"),
							ToDo.allocated_to.as_("user"),
						)
						.where(Task.project == last_mom.project)
					)
					
					if subjects and descriptions:
						query = query.where((Task.subject.isin(subjects)) | (Task.description.isin(descriptions)))
					elif subjects:
						query = query.where(Task.subject.isin(subjects))
					elif descriptions:
						query = query.where(Task.description.isin(descriptions))
						
					data = query.run(as_dict=True)

	return data


@frappe.whitelist()
def update_task_from_mom(task_name: str, subject: str = None, description: str = None,
	priority: str = None, status: str = None, due_date: str = None, user: str = None):
	"""Sync edits made in the MOM child table back to the actual Task."""
	if not frappe.db.exists("Task", task_name):
		frappe.throw(_("Task {0} does not exist").format(task_name))

	task = frappe.get_doc("Task", task_name)
	task.check_permission("write")

	if subject is not None:
		task.subject = subject
	if description is not None:
		task.description = description
	if priority is not None:
		task.priority = priority
	if status is not None:
		task.status = status
		task.workflow_state = status
		if status == "Completed":
			task.completed_by = frappe.session.user
			task.completed_on = today()
	if due_date is not None:
		task.exp_end_date = due_date
	if user is not None:
		task.custom_assigned_to = []
		if user:
			task.append("custom_assigned_to", {"user": user})

	task.flags.ignore_links = True
	old_get_workflow = task.meta.get_workflow
	task.meta.get_workflow = lambda: None
	try:
		task.save(ignore_permissions=True)
	finally:
		task.meta.get_workflow = old_get_workflow
	return {"success": True, "task": task_name}

@frappe.whitelist()
def fetch_designation_of_users(list_of_users: list = []):
	try:
		return frappe.db.sql("""
							SELECT employee_name, designation from `tabEmployee`
							WHERE user_id IN %s
							""",(tuple(loads(list_of_users)), ) ,as_dict=1)
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(), title="Error encountered while fetching users designation (MOM)")


@frappe.whitelist()
def get_project_users(project):
	doc = frappe.get_doc("Project", project)
	users = []
	users.append(doc.project_manager_name) if all((doc.project_manager_name, doc.project_manager, doc.project_type == "Internal")) else None
	users.extend([user.full_name for user in doc.users])
	return users