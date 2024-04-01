# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError
from frappe import _
from one_fm.overrides.assignment_rule import get_assignment_rule_description

class RoutineTask(Document):
	def validate(self):
		self.validate_dates()

	def validate_dates(self):
		if self.end_date:
			self.validate_from_to_dates("start_date", "end_date")

		if self.end_date == self.start_date:
			frappe.throw(
				_("{0} should not be same as {1}").format(frappe.bold("End Date"), frappe.bold("Start Date"))
			)

	@frappe.whitelist()
	def set_task_and_auto_repeat(self):
		task = self.set_task_for_routine_task()
		if task:
			self.assign_employee_to_task(task)
			self.set_auto_repeat_for_task(task)

	@frappe.whitelist()
	def remove_task_and_auto_repeat(self):
		task_reference = self.task_reference
		auto_repeat_reference = self.auto_repeat_reference
		if self.auto_repeat_reference:
			self.db_set('auto_repeat_reference', '')
			frappe.delete_doc('Auto Repeat', auto_repeat_reference)

		if self.task_reference:
			self.db_set('task_reference', '')
			frappe.delete_doc('Task', task_reference)

		self.add_comment("Info", "Remove Task {0} and Auto Repeat {1}".format(task_reference, auto_repeat_reference))

	def assign_employee_to_task(self, task):
		assigne = frappe.get_value('Employee', self.employee, 'user_id')
		assigner = frappe.db.get_value("Employee", self.direct_report_reviewer, "user_id")
		if assigne:
			try:
				add_assignment({
					'doctype': 'Task',
					'name': task,
					'assign_to': [assigne],
					'description': _(self.task),
					"assigned_by": assigner if assigner else frappe.session.user
				})
				self.add_comment("Info", "Task {0} Assigned to {1}".format(task, assigne))
			except DuplicateToDoError:
				frappe.message_log.pop()
				pass

	def set_auto_repeat_for_task(self, task):
		if not self.auto_repeat_reference:
			auto_repeat = frappe.new_doc('Auto Repeat')
			auto_repeat.reference_doctype = "Task"
			auto_repeat.reference_document = task
			auto_repeat.start_date = self.start_date
			auto_repeat.frequency = self.frequency
			if self.end_date:
				auto_repeat.end_date = self.end_date
			if auto_repeat.frequency == 'Monthly':
				if self.repeat_on_last_day:
					auto_repeat.repeat_on_last_day = self.repeat_on_last_day
				elif self.repeat_on_day:
					auto_repeat.repeat_on_day = self.repeat_on_day
				else:
					day_in_frequency = int(day_of_the_frequency(auto_repeat.frequency, self.start_date))
					if day_in_frequency > 28 and auto_repeat.frequency == 'Monthly':
						day_in_frequency = 28
					auto_repeat.repeat_on_day = day_in_frequency
			if auto_repeat.frequency == 'Weekly':
				if self.repeat_on_days and len(self.repeat_on_days) > 0:
					for item in self.repeat_on_days:
						repeat_on_days = auto_repeat.append('repeat_on_days')
						repeat_on_days.day = item.day
				else:
					repeat_on_days = auto_repeat.append('repeat_on_days')
					repeat_on_days.day = day_of_the_frequency(auto_repeat.frequency, self.start_date)
			auto_repeat.save(ignore_permissions=True)
			self.db_set('auto_repeat_reference', auto_repeat.name)

	def set_task_for_routine_task(self):
		if self.task and not self.task_reference:
			task = frappe.new_doc('Task')
			task.subject = (self.task[slice(78)]+"...") if len(self.task) > 80 else self.task
			task.description = self.task
			task.type = self.task_type
			if self.remark:
				task.description += "<br/><br/><b>Remarks:</b><br/>" + self.remark
			task.expected_time = self.hours_per_frequency
			if self.erp_document:
				task.routine_erp_document = self.erp_document
			task.save(ignore_permissions=True)
			self.db_set('task_reference', task.name)
			return task.name
		return self.task_reference

	def on_update(self):
		self.update_assignment_rule_for_doc_in_process()

	def update_assignment_rule_for_doc_in_process(self):
		if self.is_erp_process and self.process_name and self.employee_user:
			# Get routine task process to get the documents linked with the routine task
			rt_process = frappe.get_doc('Routine Task Process', self.process_name)
			document_names = False
			common_assignment_rule_linked_docs = []
			# Iterate the documents list linked with the routine task process to update the assignment rule
			for erp_doc in rt_process.erp_document:
				'''
					Check if assignment rule exists without routine task link for the document,
					do not create the assignment rule linked with routine task for the document.
				'''
				if frappe.db.exists('Assignment Rule', {'document_type': erp_doc.routine_task_document, 'custom_routine_task': ['is', 'not set']}):
					common_assignment_rule_linked_docs.append(erp_doc.routine_task_document)
					continue

				if document_names:
					document_names += ", "+erp_doc.routine_task_document
				else:
					document_names = erp_doc.routine_task_document
				# Check if assignment rule exists for the routine task and the document
				assignment_rule_exists = frappe.db.exists('Assignment Rule', {'document_type': erp_doc.routine_task_document, 'custom_routine_task': self.name})
				assignment_rule = False
				'''
					If assignment rule exists with the filters and employee got changed in the routine task,
					then get the assignment rule object and set the users linked in assignment rule to null
				'''
				if assignment_rule_exists and self.has_value_changed("employee"):
					assignment_rule = frappe.get_doc('Assignment Rule', assignment_rule_exists)
					assignment_rule.users = []
				# If no assignment rule exists for the filters, create new assignment rule object
				else:
					assignment_rule = frappe.new_doc('Assignment Rule')
					assignment_rule.name = "{0}-{1}".format(self.name, erp_doc.routine_task_document)
					assignment_rule.document_type = erp_doc.routine_task_document
					assignment_rule.description = get_assignment_rule_description(erp_doc.routine_task_document)
					assignment_rule.assign_condition = 'docstatus == 0'
					assignment_rule.rule = 'Round Robin'
					assignment_rule.custom_routine_task = self.name

					days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
					for day in days:
						assignment_days = assignment_rule.append('assignment_days')
						assignment_days.day = day

				# If assignment rule object exists, set user of employee selected in the routine task as the users of assignment rule and save it.
				if assignment_rule:
					users = assignment_rule.append('users')
					users.user = self.employee_user
					assignment_rule.save(ignore_permissions=True)
					frappe.msgprint(_("Assignment rules are Updated for the document(s): {0}".format(document_names)), alert=True, indicator='green')

			# Notify the user by msg print about the assignment rule not linked with routine task
			if common_assignment_rule_linked_docs and len(common_assignment_rule_linked_docs) > 0:
				msg = _("No Assignment Rule created for the Rotine task for the lsited documents, since common Assignment Rule linked to these documents: {0}".format(", ".join(common_assignment_rule_linked_docs)))
				frappe.msgprint(msg, alert=True, indicator='orange')

@frappe.whitelist()
def filter_routine_document(doctype, txt, searchfield, start, page_len, filters):
	query = """
		select
			routine_task_document
		from
			`tabRoutine Task Document`
		where
			parenttype='Routine Task Process' and parent=%(parent)s and routine_task_document like %(txt)s
			limit %(start)s, %(page_len)s
	"""
	return frappe.db.sql(query,
		{
			'parent': filters.get("parent"),
			'start': start,
			'page_len': page_len,
			'txt': "%%%s%%" % txt
		}
	)

def day_of_the_frequency(frequency, date):
	week_map = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
	if frequency == 'Monthly':
		return getdate(date).strftime("%d")
	if frequency == 'Weekly':
		return week_map[getdate(date).weekday()]
	return 1
