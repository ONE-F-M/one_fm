# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today, getdate
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError
from frappe import _

class RoutineTask(Document):
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
		if assigne:
			try:
				add_assignment({
					'doctype': 'Task',
					'name': task,
					'assign_to': [assigne],
					'description': _(self.task)
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
			auto_repeat.start_date = today()
			auto_repeat.frequency = self.frequency
			if auto_repeat.frequency in ['Monthly', 'Quarterly', 'Half-yearly', 'Yearly']:
				day_in_frequency = day_of_the_frequency(auto_repeat.frequency)
				if day_in_frequency > 28 and auto_repeat.frequency == 'Monthly':
					day_in_frequency = 28
				auto_repeat.repeat_on_day = day_in_frequency
			if auto_repeat.frequency == 'Weekly':
				repeat_on_days = auto_repeat.append('repeat_on_days')
				repeat_on_days.day = day_of_the_frequency(auto_repeat.frequency)
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
			task.save(ignore_permissions=True)
			self.db_set('task_reference', task.name)
			return task.name
		return task_reference


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

def day_of_the_frequency(frequency, date=today()):
	week_map = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
	if frequency == 'Monthly':
		return getdate(date).strftime("%d")
	if frequency == 'Weekly':
		return week_map[getdate(today()).weekday()]
	return 1
