# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from json import loads

import frappe
from frappe.utils import today, format_date
from frappe.model.document import Document
from frappe import _

class MOM(Document):
	def autoname(self):
		formated_today_date = format_date(today(), 'dd-mm-yyyy')
		target_project_docs = frappe.db.count(self.doctype, filters={"project": self.project})
		# Format the name as `DD-MM-YYYY|Project|##`
		self.name = f"{formated_today_date}|{self.project}|{target_project_docs + 1:02d}"


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
			todos = frappe.get_all(
				"ToDo",
				filters={"reference_type": "Task", "reference_name": task_name, "status": "Open"},
				pluck="name",
			)
			if todos:
				frappe.db.set_value("ToDo", {"name": ["in", todos]}, "status", "Closed")
		task.exp_end_date = due_date
	if user is not None:
		task.custom_assigned_to = []
		if user:
			task.append("custom_assigned_to", {"user": user})

	task.flags.ignore_links = True
	task.flags.ignore_workflow = True
	task.save(ignore_permissions=True)
	return {"success": True, "task": task_name}

@frappe.whitelist()
def fetch_designation_of_users(list_of_users=None):
	try:
		# The client sends this as a JSON-encoded string; accept both str and list
		if isinstance(list_of_users, str):
			list_of_users = loads(list_of_users) if list_of_users else []

		if not list_of_users:
			return []

		return frappe.get_all(
			"Employee",
			filters={"user_id": ["in", list_of_users]},
			fields=["employee_name", "designation"],
		)
	except Exception:
		frappe.log_error(message=frappe.get_traceback(), title="Error encountered while fetching users designation (MOM)")


@frappe.whitelist()
def get_project_users(project: str | None = None):
	if not project:
		return []
	doc = frappe.get_doc("Project", project)
	users = []
	users.append(doc.project_manager_name) if all((doc.project_manager_name, doc.project_manager, doc.project_type == "Internal")) else None
	users.extend([user.full_name for user in doc.users])
	return users