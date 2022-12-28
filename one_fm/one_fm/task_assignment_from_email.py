import frappe
from frappe import _
import re
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError

def assign_task_to_user_from_communication_content(doc, method):
	# Check if task reference exist in the communication
	if doc.reference_doctype == 'Task' and doc.reference_name:
		# Check if Do we needs to assign rask to the users mentioned in the email
		assign_task_from_email = frappe.db.get_single_value('Project Additional Settings', 'assign_task_from_email')
		if assign_task_from_email:
			# Get assignees(email) from communicaion content
			assignees = get_assignees_from_communication_content(doc, assign_task_from_email)
			# Check user exist for the assignees and assign to the task
			for assigne in assignees:
				if frappe.db.exists('User', {'email': assigne}):
					try:
						add_assignment({
							'doctype': doc.reference_doctype,
							'name': doc.reference_name,
							'assign_to': [assigne],
							'description': _('')
						})
						doc.add_comment("Info", "Task {0} Assigned to {1}".format(doc.reference_name, assigne))
					except DuplicateToDoError:
						frappe.message_log.pop()
						pass
				else:
					doc.add_comment("Info", "There is no user exist for the email {0} in the ERP".format(assigne))


def get_assignees_from_communication_content(doc, assign_task_from_email):
	start = end = False
	differentiate_assignment_from_email_content_by = frappe.db.get_single_value('Project Additional Settings', 'differentiate_assignment_from_email_content_by')
	if differentiate_assignment_from_email_content_by in ['Start and End Tag', 'Start and End Tag or Mail to Tag']:
		start = frappe.db.get_single_value('Project Additional Settings', 'start_tag')
	if start:
		return get_assignment_from_start_and_end_tag(doc, start.lower(), differentiate_assignment_from_email_content_by)
	if differentiate_assignment_from_email_content_by == 'Mail to Tag':
		# Looking for mailto tag
		return get_assignment_from_mailto_tag(doc)
	return False

def get_assignment_from_start_and_end_tag(doc, start, differentiate_assignment_from_email_content_by):
	assign_start = doc.content.lower().split(start)
	'''
		If length of assign_start equal to or less than 1, then there is no Assign tag, So there is no assignment
		If length of assign_start greater than 1, then there is Assign tag, So there are assignments
	'''
	assignment_tag_found = False
	if assign_start and len(assign_start) > 1:
		end = frappe.db.get_single_value('Project Additional Settings', 'end_tag')
		if not end:
			end = 'end assign'
		if end:
			assign_end = assign_start[1].split(end.lower())
		else:
			assign_end = assign_start[1]
		'''
			If length of assign_end equal to or less than 1, then there is no Assign End tag
			If length of assign_end greater than 1, then there is Assign End tag

			assign_end[0], The first element of assign_end will be the content which is having the assigned users
		'''
		if assign_end and len(assign_end) > 0:
			if len(assign_end) == 0:
				doc.add_comment("Info", "There is no assignment tag 'End Assign' found in message content!")
			assignment_tag_found = True
			assignment = re.findall(r"[A-Za-z0-9._%+-]+"
				r"@[A-Za-z0-9.-]+"
				r"\.[A-Za-z]{2,4}", assign_end[0])
			# Remove duplicate items from list
			return remove_duplicate_assignees(doc, assignment)
	if not assignment_tag_found:
		doc.add_comment("Info", "There is no assignment tag 'Assign' 'End Assign' found in message content!")
		if differentiate_assignment_from_email_content_by == 'Start and End Tag or Mail to Tag':
			# Looking for mailto tag
			return get_assignment_from_mailto_tag(doc)
	return False

def get_assignment_from_mailto_tag(doc):
	assign = doc.content.split('mailto')
	if assign and len(assign) > 0:
		assignment = []
		for mailto in assign:
			assignment += re.findall(r"[A-Za-z0-9._%+-]+"
				r"@[A-Za-z0-9.-]+"
				r"\.[A-Za-z]{2,4}", mailto)
		# Remove duplicate items from list
		assignment = remove_duplicate_assignees(doc, assignment)
		if len(assignment) <= 0:
			doc.add_comment("Info", "There is no mailto(@) tag found in message content!")
		return assignment
	return False

def remove_duplicate_assignees(doc, assignment):
	# Remove duplicate items from list
	assignment = [*set(assignment)]
	if doc.sender in assignment:
		assignment.remove(doc.sender)
	return assignment
