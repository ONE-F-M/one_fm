import frappe
from frappe import _
from frappe.desk.form.utils import add_comment
from one_fm.api.mobile.roster import get_current_user_details
from frappe.desk.form.assign_to import add as assign_to
from frappe.utils.html_utils import clean_html

@frappe.whitelist()
def get_tasks():
	try:
		user, user_roles, user_employee = get_current_user_details()
		print(user, user_employee)
		tasks = frappe.db.sql("""
			SELECT
				name, subject, project, description, status
			FROM `tabTask`
			WHERE
				name IN
			(SELECT
				reference_name FROM `tabToDo`
			WHERE
				reference_type="Task" AND owner="{0}" AND status<>"Cancelled")
			""".format(user), as_dict=1)
		
		print(tasks)
		return tasks
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)

@frappe.whitelist()
def add_task(subject, project, site, shift, description):
	try:
		task = frappe.new_doc("Task")
		task.subject = subject
		task.project = project
		task.description = description
		task.site = site
		task.shift = shift
		task.save()
		return task
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)

@frappe.whitelist()
def complete_task(task_name):
	try:
		task = frappe.get_doc("Task", task_name)
		task.status = "Completed"
		task.save()
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)

@frappe.whitelist()
def reopen_task(task_name):
	try:
		task = frappe.get_doc("Task", task_name)
		task.status = "Open"
		task.progress = 0
		task.save()
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)

@frappe.whitelist()
def add_task_comment(task_name, content):
	try:
		user, user_roles, user_employee = get_current_user_details()
		print(task_name, content, user)
		add_comment("Task", task_name, content, user)
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)

@frappe.whitelist()
def get_task_comments(task_name):
	try:
		user, user_roles, user_employee = get_current_user_details()
		print(task_name, user)
		comments = frappe.get_list("Comment", {"reference_doctype": "Task", "reference_name": task_name, "comment_type": "Comment"}, "*")
		print(comments)
		return comments
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)



@frappe.whitelist()
def assign_task(task_name, employee):
	try:
		employee_user = frappe.get_value("Employee", employee, "user_id")
		assign_to({
			"assign_to": employee_user,
			"doctype": "Task",
			"name": task_name,
		})
		return {"message": _("Successful")} 
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)
	

@frappe.whitelist()
def edit_task(task_name, description):
	try:
		if not frappe.has_permission("Task", "edit", task_name):
			return frappe.utils.response.report_error(417)
		task = frappe.get_doc("Task", task_name)
		task.description = description
		task.save()
		frappe.db.commit()
		return {"message": _("Successful")} 
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist()
def delete_task(task_name):
	try:
		if not frappe.has_permission("Task", "delete", task_name):
			return frappe.utils.response.report_error(417)
		frappe.delete_doc("Task", task_name)
		return {"message": "Task: {name} deleted successfully.".format(name=task_name)}
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)

