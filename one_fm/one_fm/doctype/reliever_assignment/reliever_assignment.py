# Copyright (c) 2024, ONE FM and contributors
# For license information, please see license.txt

import json, time
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count
from frappe.utils import now, validate_email_address, getdate
from pypika.terms import Case
from one_fm.api.doc_events import get_employee_user_id



class RelieverAssignment(Document):
	def validate(self):
		self.set_user_ids()

	def before_insert(self):
		self.validate_leave_application()
		
		
	def after_insert(self):
		self.assign_roles()
		self.assign_todos()
		self.get_single_doctypes()
		self.get_approval_doctypes()
		
		# Update status after transferring responsibilities
		self.update_status("Transferred")
		self.save()

	def update_status(self, status):
		self.status = status

	def validate_leave_application(self):
		leave_application = frappe.get_value("Leave Application", self.leave_application, ["workflow_state", "from_date", "to_date", "custom_reliever_"], as_dict=1)

		if not ( leave_application.workflow_state == "Approved" and 
			(leave_application.from_date <= getdate() <= leave_application.to_date) and 
			(leave_application.custom_reliever_ is not None)):
			frappe.throw(_(f"Reliever Assignment record cannot be created for <b>Leave Application - {self.leave_application}</b>"))

	def set_user_ids(self):
		self._employee_user_id = get_employee_user_id(self.on_leave_employee)
		self._reliever_user_id = get_employee_user_id(self.reliever)


	def assign_roles(self):
		employee_on_leave_user = frappe.get_doc("User", self._employee_user_id)
		reliever_user = frappe.get_doc("User", self._reliever_user_id)
		
		roles = frappe._dict({
			"employee_on_leave": frappe._dict({
				"employee": self.on_leave_employee,
				"user_id": self._employee_user_id,
				"role_profile_name": employee_on_leave_user.role_profile_name,
				"roles": [role.role for role in employee_on_leave_user.roles]
			}),
			"reliever": frappe._dict({
				"employee": self.reliever,
				"user_id": self._reliever_user_id,
				"role_profile_name": reliever_user.role_profile_name,
				"roles": [role.role for role in reliever_user.roles]
			}),
		})
		
		# Log data for reversal
		self.add_assigned_documents("User", "Docfield", roles, "role_profile_name")

		roles_to_be_assigned = roles.employee_on_leave.roles + roles.reliever.roles
		# If both have role profile or If reliever has role profile and on leave employee doesn't
		if (employee_on_leave_user.role_profile_name and reliever_user.role_profile_name) or (not employee_on_leave_user.role_profile_name and reliever_user.role_profile_name):
			reliever_user.db_set("role_profile_name", None)

		reliever_user.add_roles(roles_to_be_assigned)

	def assign_todos(self):
		ToDo = DocType("ToDo")
		# Get open todos with reference_type and reference_name
		open_todos = (
			frappe.qb.from_(ToDo)
			.select(ToDo.name, ToDo.reference_type, ToDo.reference_name)
			.where(
				(ToDo.allocated_to == self._employee_user_id)
				& (ToDo.status == "Open")
			).orderby(ToDo.reference_type, order=frappe.qb.asc)
		).run(as_dict=True)
		
		if len(open_todos) > 0:
			# Log data for reversal
			self.add_assigned_documents("ToDo", "Docfield", open_todos, fieldname="allocated_to")

			frappe.qb.update(ToDo).set(ToDo.allocated_to, self._reliever_user_id).set(ToDo.modified, now()).where(
				ToDo.allocated_to == self._employee_user_id).where(ToDo.status == "Open").run()

			# frappe.enqueue(self.assign_todo_references, todos=open_todos)
			self.assign_todo_references(open_todos)

	def assign_todo_references(self, todos):
		# Assign references linked to ToDo if the reference_type is added in Reliever Assignment Settings doctype
		reliever_assignment_settings = frappe.get_doc("Reliever Assignment Settings")
	
		# List of doctypes from Reliever Assignment settings
		doctypes_list = [doc.reference_doctype for doc in reliever_assignment_settings.documents]

		# Config with fieldnames, fieldtype, statuses, and status_field of each allowed doctype
		config = frappe._dict({
				doc.reference_doctype: {
				"fieldnames": [fieldname.strip() for fieldname in doc.fieldnames.split(",")],
				"link_fieldtype": doc.link_fieldtype,
				"statuses_allowed": [status.strip() for status in doc.statuses.split(",")],
				"status_field": doc.status_field 
			} for doc in reliever_assignment_settings.documents
		})
	
		# Filtered out todos from all todos	based on reference_type	
		filtered_todos = [todo for todo in todos if todo.reference_type in doctypes_list]

		for todo in filtered_todos:
			# Doctype name
			configuration = config[todo.reference_type]
			# Allowed statuses e.g Draft, Open
			status_to_check = configuration["statuses_allowed"]
			# Status field e.g. workflow_state or status
			status_field = configuration["status_field"]
			value_to_replace = self.on_leave_employee if configuration["link_fieldtype"] == "Employee" else self._employee_user_id
			replaced_with = self.reliever if configuration["link_fieldtype"] == "Employee" else self._reliever_user_id
			# Fieldnames to check in the doctype
			fieldnames = configuration["fieldnames"]	
			for fieldname in fieldnames:
				if "name" in fieldname:
					replaced_with = self.reliever_name
					value_to_replace =self.on_leave_employee_name 
				self.add_assigned_documents(todo.reference_type, "Docfield", todo, fieldname=fieldname)
				ReferenceType = DocType(todo.reference_type)
				for fieldname in fieldnames:						
					frappe.qb.update(ReferenceType) \
						.set(ReferenceType[fieldname], replaced_with) \
						.set(ReferenceType.modified, now()) \
						.where(ReferenceType.name == todo.reference_name) \
						.where(ReferenceType[fieldname] == value_to_replace) \
						.where(ReferenceType[status_field].isin(status_to_check)) \
					.run()

	def add_assigned_documents(self, reference_doctype, based_on, doclist, fieldname=None, reference_docname=None):
		self.append("assigned_documents", {
			"reference_doctype": reference_doctype,
			"based_on": based_on,
			"doclist": json.dumps(doclist, indent=4),
			"fieldname": fieldname,
			"reference_docname": reference_docname
		})
		

	def get_single_doctypes(self):
		Doctype = DocType("DocType")
		Singles = DocType("Singles")
		Docfield = DocType("DocField")

		# Get the list of single doctypes which contain Employee/User link field
		single_doctypes_query = (
			frappe.qb.from_(Docfield)
			.left_join(Doctype)
			.on(Docfield.parent == Doctype.name)
			.select(Docfield.fieldname)
			.where(
				(Doctype.issingle == 1)
				& (Docfield.parent == Doctype.name)
				& (Docfield.parenttype == "DocType")
				& (Docfield.fieldtype == "Link")
				& (Doctype.issingle == 1)
				& (Docfield.options.isin(["Employee", "User"]))
			)
		)

		# Get rows from tabSingles where doctype is Single and employee/user id of on leave employee is set 
		assigned_single_doctypes = (
			frappe.qb.from_(Singles)
			.select("*", )
			.where(
			Singles.field.isin(single_doctypes_query)
			& Singles.value.isin([self._employee_user_id, self.on_leave_employee])	
			)	
		)
		
		assigned_records = assigned_single_doctypes.run(as_dict=True)

		if len(assigned_records) > 0:
			for record in assigned_records:
				if validate_email_address(record.value):
					record.replaced_with = self._reliever_user_id
				else:
					record.replaced_with = self.reliever

				# Log data for reversal
				self.add_assigned_documents(record.doctype, "Docname", record, reference_docname=record.doctype)
				frappe.qb.update(Singles).set(
					Singles.value, record.replaced_with
				).where(
					Singles["field"] == record.field
				).where(
					Singles.doctype == record.doctype
				).run()


	def get_approval_doctypes(self):
		# For now, only Department Approver child table needs to be checked
		DepartmentApprover = DocType("Department Approver")
		approvers = (
			frappe.qb.from_(DepartmentApprover)
			.select(DepartmentApprover.name, DepartmentApprover.approver, DepartmentApprover.parent, DepartmentApprover.parentfield)
			.where(
				(DepartmentApprover.approver == self._employee_user_id)
			)
		).run(as_dict=True)

		if len(approvers) > 0:
			# Log data for reversal
			self.add_assigned_documents("Department Approver", "Docname", approvers, reference_docname="Department Approver")
			for approver in approvers: 
				frappe.qb.update(DepartmentApprover) 	\
				.set(DepartmentApprover.approver, self._reliever_user_id) \
				.set(DepartmentApprover.modified, now()) \
				.where(DepartmentApprover.name == approver.name).run()


def assign_responsibilities(leave_application):
	try:
		reliever_assignment = frappe.new_doc("Reliever Assignment")
		reliever_assignment.leave_application = leave_application
		reliever_assignment.save()
	except Exception:
		frappe.log_error(title = 'ERROR ASSIGNING RECORDS',message = frappe.get_traceback())


class ReassignRelieverAssignment(Document):
	def __init__(self,leave_application):
		self.leave_application = leave_application
		self.set_user_ids()

	def set_user_ids(self):
		self.parent_data = frappe.db.get_value("Reliever Assignment", self.leave_application, "*")	
		self.on_leave_employee = self.parent_data.on_leave_employee
		self.reliever = self.parent_data.reliever
		self.on_leave_employee_name = self.parent_data.on_leave_employee_name
		self.reliever_name = self.parent_data.reliever_name
		self._employee_user_id = get_employee_user_id(self.on_leave_employee)
		self._reliever_user_id = get_employee_user_id(self.reliever)

	def update_status(self, status):
		frappe.db.set_value("Reliever Assignment", self.leave_application, "status", status)
		frappe.db.commit()

	def reassign_todos(self,data):
		todos_in_doclist = [name.get('name')for name in json.loads(data.doclist)]
		ToDo = DocType(data.reference_doctype)
		frappe.qb.update(ToDo).set(
				ToDo.allocated_to, self._employee_user_id
			).where(
				 (ToDo.name.isin(todos_in_doclist)) 
   				 & (ToDo.status == "Open")
			).run()
		self.reassign_todo_references(data)
		
	def reassign_todo_references(self, data):
		reliever_assignment_settings = frappe.get_doc("Reliever Assignment Settings")
	
		# Config with fieldnames, fieldtype, statuses, and status_field of each allowed doctype
		config = frappe._dict({
				doc.reference_doctype: {
				"fieldnames": [fieldname.strip() for fieldname in doc.fieldnames.split(",")],
				"link_fieldtype": doc.link_fieldtype,
				"statuses_allowed": [status.strip() for status in doc.statuses.split(",")],
				"status_field": doc.status_field 
			} for doc in reliever_assignment_settings.documents
		})

		for todo in json.loads(data.doclist):
			if frappe.get_doc('ToDo',{"name":todo.get('name')}).status == 'Open':
				if todo.get('reference_type') in config:
					configuration = config[todo.get('reference_type')]
					status_to_check = configuration["statuses_allowed"]
					status_field = configuration["status_field"]
					replaced_with = self.on_leave_employee if configuration["link_fieldtype"] == "Employee" else self._employee_user_id
					value_to_replace = self.reliever if configuration["link_fieldtype"] == "Employee" else self._reliever_user_id
					fieldnames = configuration["fieldnames"]
					for fieldname in fieldnames:
						if "name" in fieldname:
							replaced_with = self.on_leave_employee_name
							value_to_replace = self.reliever_name
						ReferenceType = DocType(todo.get('reference_type'))
						for fieldname in fieldnames:
							frappe.qb.update(ReferenceType) \
								.set(ReferenceType[fieldname], replaced_with) \
								.set(ReferenceType.modified, now()) \
								.where(ReferenceType.name == todo.get('reference_name')) \
								.where(ReferenceType[fieldname] == value_to_replace) \
								.where(ReferenceType[status_field].isin(status_to_check)) \
							.run()
		
	def reassign_roles(self, data):
		doclist = json.loads(data.doclist)
		reliever_info = doclist.get("reliever", {})
		employee_info = doclist.get("employee_on_leave", {})
		reliever_roles = set(reliever_info.get("roles", []))
		employee_roles = set(employee_info.get("roles", []))
		roles_to_remove = employee_roles - reliever_roles
		if self._reliever_user_id:
			reliever_user = frappe.get_doc("User", self._reliever_user_id)
			if roles_to_remove:
				reliever_user.remove_roles(*roles_to_remove)
			if reliever_info.get("role_profile_name"):
				frappe.db.set_value("User", self._reliever_user_id, "role_profile_name", reliever_info["role_profile_name"])


	def reassign_reportees(self,data):
		Employee = DocType(data.reference_doctype)
		doclist_to_reassign = [name.get('name') for name in json.loads(data.doclist)]
		if doclist_to_reassign:
			(frappe.qb.update(Employee)
					.set(Employee.reports_to, self.on_leave_employee)\
					.where(Employee.name.isin(doclist_to_reassign))
				).run()

	def reassign_projects(self,data):
		Project = DocType(data.reference_doctype)
		doclist_to_reassign = [name.get('name')for name in json.loads(data.doclist)]
		if doclist_to_reassign:
			frappe.qb.update(Project).set(
					Project.account_manager, self.on_leave_employee).set(
					Project.manager_name, self.on_leave_employee_name).set(
					Project.modified, now()).where(
						(Project.name.isin(doclist_to_reassign)) &
						(Project.status == "Open")
					).run()
	
	def reassign_operations_site(self,data):
		OperationsSite = DocType(data.reference_doctype)
		doclist_to_reassign = [name.get('name')for name in json.loads(data.doclist)]
		if doclist_to_reassign:
			frappe.qb.update(OperationsSite).set(
					OperationsSite.account_supervisor, self.on_leave_employee).set(
					OperationsSite.account_supervisor_name, self.on_leave_employee_name).set(
					OperationsSite.modified, now()).where(
					OperationsSite.name.isin(doclist_to_reassign))\
						.where(OperationsSite.status == "Active").run()


	def reassign_department_approvals(self,data):
		DepartmentApprover = DocType(data.reference_doctype)
		doclist_to_reassign = [name.get('name')for name in json.loads(data.doclist)]
		if doclist_to_reassign:
			frappe.qb.update(DepartmentApprover) 	\
				.set(DepartmentApprover.approver, self._employee_user_id) \
				.set(DepartmentApprover.modified, now()) \
				.where(DepartmentApprover.name.isin(doclist_to_reassign)).run()
			
	
	def reassign_single_doctype(self,data):
		Singles = DocType("Singles")
		record_doc_type = json.loads(data.doclist).get('doctype')
		record_field = json.loads(data.doclist).get('field')
		(
		frappe.qb.update(Singles)
		.set(Singles.value, self._employee_user_id)
		.where((Singles.doctype == record_doc_type) & 
			   (Singles.field == record_field))
		).run()
		frappe.clear_cache(doctype=record_doc_type)

		
	def reassign_process_tasks(self,data):
		ProcessTask = DocType(data.reference_doctype)
		fieldname = data.fieldname
		doclist_to_reassign = [name.get('name')for name in json.loads(data.doclist)]

		if doclist_to_reassign and fieldname == "direct_report_reviewer":
			frappe.qb.update(ProcessTask ).set(
					ProcessTask.direct_report_reviewer, self.on_leave_employee).set(
					ProcessTask.direct_report_reviewer_name, self.on_leave_employee_name).set(
					ProcessTask.modified, now()).where(
					ProcessTask.name.isin(doclist_to_reassign)).run()
			

	def reassign(self):
		leave_application = frappe.get_value("Leave Application", self.leave_application, "name")
		datas = (frappe.qb.from_("Reliever Assignment Document")\
		.select('*')\
		.where(frappe.qb.Field('parent')==leave_application)\
		.where(frappe.qb.Field('parentfield')=='assigned_documents')).run(as_dict=1)
		
		for data in datas:
			if data.reference_doctype == "User":
				self.reassign_roles(data)
			elif data.reference_doctype == "Employee":
				self.reassign_reportees(data)
			elif data.reference_doctype == "ToDo":
				self.reassign_todos(data)
			elif data.reference_doctype == "Project":
				self.reassign_projects(data)
			elif data.reference_doctype == "Process Task":
				self.reassign_process_tasks(data)
			elif data.reference_doctype == "Operations Site":
				self.reassign_operations_site(data)
			elif data.reference_doctype == "Department Approver":
				self.reassign_department_approvals(data)
			else:
				self.reassign_single_doctype(data)
		self.reassign_todos_during_leave_period_of_leave_applicant(datas)
		self.update_status("Reverted")

	def reassign_todos_during_leave_period_of_leave_applicant(self,datas):
		start_date = self.parent_data.assignment_period_start
		end_date = self.parent_data.assignment_period_end
		ToDo = DocType("ToDo")
		relievers_todo = (
		frappe.qb.from_(ToDo)
          .select("*")
          .where(
              (ToDo.allocated_to == self._reliever_user_id)
              & (ToDo.creation >= start_date)
              & (ToDo.creation <= end_date)&(ToDo.status == "Open"))
			  ).run(as_dict=True)		
		for reference in relievers_todo:
			reference_type = reference["reference_type"]
			reference_name = reference["reference_name"]
			
			if reference_type and reference_name:
				todo_to_update = frappe.get_doc(reference_type, {'name': reference_name})
				if hasattr(todo_to_update, 'employee') and todo_to_update.employee:
					emp_details = frappe.get_doc('Employee',todo_to_update.employee)
					if emp_details.reports_to == self.on_leave_employee:
						if reference.allocated_to is not None:
							frappe.db.set_value(ToDo, reference.name, 'allocated_to', self._employee_user_id)
							self.reassign_docs_related_to_todos(reference_type,reference_name)


	def reassign_docs_related_to_todos(self, reference_type, reference_name):
		Doctype = frappe.get_doc('Reliever Assignment Settings', {'reference_doctype': reference_type})
		matching_docs_list = [doc for doc in Doctype.as_dict().documents if doc.get('reference_doctype') == reference_type]
		
		if not matching_docs_list:
			frappe.log_error(f"No matching documents found for reference_doctype: {reference_type}")
			return 
		
		matching_docs = matching_docs_list[0]
		
		status_to_check = (matching_docs.statuses).split(',')
		status_field = matching_docs.status_field
		replaced_with = self.on_leave_employee if matching_docs["link_fieldtype"] == "Employee" else self._employee_user_id
		value_to_replace = self.reliever if matching_docs["link_fieldtype"] == "Employee" else self._reliever_user_id
		fieldnames = matching_docs['fieldnames'].split(",")
		
		for fieldname in fieldnames:
			if "name" in fieldname:
				value_to_replace = self.reliever_name
				replaced_with = self.on_leave_employee_name 
			
			ReferenceType = DocType(reference_type)
			
			frappe.qb.update(ReferenceType) \
				.set(ReferenceType[fieldname], replaced_with) \
				.set(ReferenceType.modified, now()) \
				.where(ReferenceType.name == reference_name) \
				.where(ReferenceType[fieldname] == value_to_replace) \
				.where(ReferenceType[status_field].isin(status_to_check)).run()

def reassign_responsibilities(leave_application):
	try:
		reassign_responsiobility = ReassignRelieverAssignment(leave_application=leave_application)
		reassign_responsiobility.reassign()
	except Exception:
		frappe.log_error(title = "ERROR CREATING RELIEVER ASSIGNMENT",message = frappe.get_traceback())