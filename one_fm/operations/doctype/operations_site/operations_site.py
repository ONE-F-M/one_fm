# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr
from frappe.model.document import Document
import json
from frappe.core.doctype.version.version import get_diff

class OperationsSite(Document):
	def validate(self):
		self.validate_user_role()
		if len(self.poc) == 0:
			frappe.throw("POC list is mandatory.")
		self.validate_project_status()

	def validate_project_status(self):
		# validate active employees
		if self.status=='Inactive':
			active_emp_sites = frappe.db.sql(f"""
				SELECT name, employee_name FROM tabEmployee WHERE site="{self.name}" AND status='Active'
			""", as_dict=1)
			# confirm active employees for site and related shifts
			if active_emp_sites:
				msg = "The site `{0}` is linked with {1} employee(s):<br/>".format(self.name, len(active_emp_sites))
				for employee in active_emp_sites:
					msg += "<br/>"+"<a href='/app/employee/{0}'>{0}: {1}</a>".format(employee.name, employee.employee_name)
				msg += '</br></br><a href="/app/employee?status=Active&site={0}">click here to view the list</a>'.format(self.name)
				frappe.throw(_("{0}".format(msg)))

		if self.status == "Active" and self.project:
			active_open = False
			if frappe.db.get_value('Project', self.project, 'status') != 'Open':
				active_open = "Open"
			elif frappe.db.get_value('Project', self.project, 'is_active') != 'Yes':
				active_open = "Active"
			if active_open:
				frappe.throw(_("The Project '<b>{0}</b>' selected in the Site '<b>{1}</b>' is <b>Not {2}</b>. <br/> To make the Site atcive first make the project {2}".format(self.project, self.name, active_open)))

	def update_shift_post_role_status(self):
		# check if employee in any of the existing site, shift, role, post
		if frappe.db.exists("Operations Shift", {'site':self.name}):
			frappe.db.sql(f"""
				UPDATE `tabOperations Shift` set status="{self.status}"
				WHERE site="{self.name}";
			""")
		if frappe.db.exists("Operations Post", {'site':self.name}):
			frappe.db.sql(f"""
				UPDATE `tabOperations Post` set status="{self.status}"
				WHERE site="{self.name}";
			""")
			operations_post = frappe.db.sql(f"""
				SELECT name, status FROM `tabOperations Post` 
				WHERE site="{self.name}";
			""", as_dict=1)
			frappe.enqueue(self.trigger_operations_post_update, queue="long", operations_post=operations_post)

		if frappe.db.exists("Operations Role", {'site':self.name}):
			frappe.db.sql(f"""
				UPDATE `tabOperations Role` set status="{self.status}"
				WHERE site="{self.name}";
			""")

	def trigger_operations_post_update(self, operations_post):
		"""
			This method triggers on_update in Operations Post
		"""
		for i in operations_post:
			frappe.get_doc("Operations Post", i.name).on_update()


		
	def validate_user_role(self):
		site_supervisor = self.get_employee_user_id(self.account_supervisor)
		# project_manager = self.get_project_manager()
		# roles = frappe.get_roles(frappe.session.user)

		# if "Operations Manager" not in roles and site_supervisor != frappe.session.user and project_manager != frappe.session.user:
		# 	frappe.throw(_("You don't have sufficient previliges to update this document."))
  
	def clear_cache(self):
		if self.has_value_changed('account_supervisor'):
			frappe.cache.delete_key('user_permissions')
   
	def on_update(self):
		self.clear_cache()
		doc_before_save = self.get_doc_before_save()
		self.update_shift_post_role_status()
		# changes = self.get_changes()
		# self.notify_changes()
		# self.update_permissions(doc_before_save)
		# self.notify_poc_changes(changes)

	def get_changes(self):
		doc_before_save = self.get_doc_before_save()
		return get_diff(doc_before_save, self, for_child=True)

	def get_field_label(self, doctype, fieldname):
		return frappe.get_meta(doctype).get_field(fieldname).label

	def notify_changes(self):
		changes = self.get_changes()
		if changes:
			if changes.changed:
				line_manager = self.get_line_manager()

				subject = '{person} made below changes to Site: {site}.\nPlease review the changes and take appropriate action.'.format(person=self.modified_by, site=self.name)
				message = ''
				if changes.changed:
					for change in changes.changed:
						fieldname, old_value, new_value = change
						label = self.get_field_label(self.doctype, fieldname)
						message = message + 'Value of {label} was changed from {old_value} to {new_value}.\n'.format(label=label, old_value=old_value, new_value=new_value)

					diff = frappe.as_json(changes.changed)
					self.update_log(diff, message, line_manager)
					recipients = [line_manager]
					create_notification_log(_(subject), _(message), recipients, self)

				# create_notification_log(subject, message,[line_manager], self)
			if changes.added or changes.removed or changes.row_changed:
				self.notify_poc_changes(changes)

	def get_line_manager(self):
		manager = frappe.get_value("Employee", {"user_id": frappe.session.user}, "reports_to")
		return frappe.get_value("Employee", {"name": manager}, "user_id")

	def update_permissions(self, doc_before_save):
		"""
			Add permissions for Site Supervisor and remove permission to any other person on assignment
		"""
		if doc_before_save.account_supervisor != self.account_supervisor:
			supervisor_user = self.get_employee_user_id(self.account_supervisor)
			permission = frappe.db.exists("User Permission", {"allow": self.doctype, "for_value": self.name})
			if permission:
				perm_doc = frappe.get_doc("User Permission", permission)
				perm_doc.user = supervisor_user
				perm_doc.save(ignore_permissions=True)
			else:
				perm_doc = frappe.new_doc("User Permission")
				perm_doc.user = supervisor_user
				perm_doc.allow = self.doctype
				perm_doc.for_value = self.name
				perm_doc.allow_to_all_doctypes = 1
				perm_doc.save(ignore_permissions=True)
			frappe.db.commit()

	def get_employee_user_id(self, employee):
		return frappe.get_value("Employee", {"name": employee}, "user_id")

	def get_project_manager(self):
		project_manager = frappe.get_value("Project", { "name": self.project}, "account_manager")
		project_manager_user = self.get_employee_user_id(project_manager)
		return project_manager_user

	def notify_poc_changes(self, changes):
		# Variables needed for notification
		subject = '{person} made below changes to Site POC: {site}.\n'.format(person=self.modified_by, site=self.name)
		message = ''

		if changes.row_changed:
			for change in changes.row_changed:
				row_name, idx, docname, field_changes = change
				for field_change in field_changes:
					fieldname, old_value, new_value = field_change
					label = self.get_field_label("POC", fieldname)
					message = message + "Value of {label} changed from {old_value} to {new_value}.\n".format(label=label, old_value=old_value, new_value=new_value)

		if changes.added:
			for change in changes.added:
				if(change[0] == "poc"):
					message = message + "{poc_name} has been added as a POC.\n".format(poc_name=change[1].poc)
				else:
					changes.added.remove(change)
		if changes.removed:
			for change in changes.removed:
				if(change[0] == "poc"):
					message = message + "{poc_name} has been removed as a POC.\n".format(poc_name=change[1].poc)
				else:
					changes.removed.remove(change)
		recipients = self.get_recipients()
		create_notification_log(_(subject), _(message), recipients, self)

	def update_log(self, diff, message, line_manager):
		frappe.db.sql("""
			INSERT INTO
				`tabOperations Changes`
			(idx, parent, parentfield, parenttype, name, diff, review_status, modified_by_user, modified_on, assigned_to, message)
			VALUES ({idx}, "{parent}","{parentfield}","{parenttype}","{name}",'{diff}',"{status}","{modified_by}","{modified}","{assigned_to}","{message}")
		""".format(
			idx=(len(self.changes_log or [])+1),
			parent=self.name,
			parentfield="changes_log",
			parenttype=self.doctype,
			name=frappe.generate_hash(length=10),
			diff=diff,
			message=message,
			status="Pending",
			modified_by=self.modified_by,
			modified=self.modified,
			assigned_to=line_manager))


	def get_recipients(self):
		"""
			Get line managers. Site Supervisor, Project Manager, Operations Manager.
		"""
		project_manager_user = self.get_project_manager()

		operations_manager = frappe.get_list("Employee", {"designation": "Operations Manager"}, ignore_permissions=True)
		recipient_list = []
		for manager in operations_manager:
			manager_user = self.get_employee_user_id(manager.name)
			recipient_list.append(manager_user)
		recipient_list.append(project_manager_user)
		return recipient_list

def create_notification_log(subject, message, for_users, reference_doc):
	for user in for_users:
		doc = frappe.new_doc('Notification Log')
		doc.subject = subject
		doc.email_content = message
		doc.for_user = user
		doc.document_type = reference_doc.doctype
		doc.document_name = reference_doc.name
		doc.from_user = reference_doc.modified_by
		doc.insert(ignore_permissions=True)
		frappe.publish_realtime(event='eval_js', message="frappe.show_alert({message: '"+message+"', indicator: 'blue'})", user=user)


@frappe.whitelist()
def changes_action(action, parent, ids):
	ids = [id for id in ids.rstrip(",").split(",")]
	ids = ', '.join(['"{}"'.format(value) for value in ids])
	if action == "Approved":
		cleanup_logs(parent, ids)
	elif action == "Rejected":
		log = frappe.db.sql("""
			select diff from `tabOperations Changes` where name in ({ids})
		""".format(ids=ids), as_dict=1)
		for change in log:
			change = json.loads(frappe._dict(change).diff)
			revert_changes(change, "Operations Site", parent)
		cleanup_logs(parent, ids)
	return True

def revert_changes(change, doctype, docname):
	cond = ', '.join(['{fieldname}="{old_value}"'.format(fieldname=field[0], old_value=field[1]) for field in change])
	

	if cond:
		frappe.db.sql("""
			UPDATE `tab{doctype}` SET {cond} WHERE name="{docname}"
		""".format(doctype=doctype, cond=cond, docname=docname))
		frappe.db.commit()
	return True

def cleanup_logs(parent, ids):
	if parent and ids:
		frappe.db.sql("""
			delete from `tabOperations Changes` where parenttype="Operations Site" and parent="{parent}" and name in ({ids})
		""".format(parent=parent,ids=ids))
		frappe.db.commit()


@frappe.whitelist()
def create_posts(data, site, project=None):
	try:
		data = frappe._dict(json.loads(data))
		post_names = data.post_names
		shifts = data.shifts
		skills = data.skills
		designations = data.designations
		gender = data.gender
		sale_item = data.sale_item
		post_template = data.post_template
		post_description = data.post_description
		post_location = data.post_location

		for shift in shifts:
			for post_name in post_names:
				operations_post = frappe.new_doc("Operations Post")
				operations_post.post_name = post_name["post_name"]
				operations_post.gender = gender
				operations_post.post_location = post_location
				operations_post.post_description = post_description
				operations_post.post_template = post_template
				operations_post.sale_item = sale_item
				operations_post.site_shift = shift["shift"]
				operations_post.site = site
				operations_post.project = project
				for designation in designations:
					operations_post.append("designations",{
						"designation": designation["designation"],
						"primary": designation["primary"] if "primary" in designation else 0
					})
				for skill in skills:
					operations_post.append("skills",{
						"skill": skill["skill"],
						"minimum_proficiency_required": skill["minimum_proficiency_required"]
					})
				operations_post.save()

		frappe.db.commit()
		frappe.msgprint(_("Posts created successfully."))
	except Exception as e:
		frappe.throw(_(frappe.get_traceback()))
