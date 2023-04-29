import frappe
from bs4 import BeautifulSoup

@frappe.whitelist()
def get_profile():
    return frappe.get_doc("User", frappe.session.user)

@frappe.whitelist()
def get_defaults():
	data = frappe._dict({})

	data.my_todos = frappe.db.get_list("ToDo", filters={
		'allocated_to':frappe.session.user,
		'status':'Open'
	}, fields="*", ignore_permissions=True)
	for each in data.my_todos:
		each.description = BeautifulSoup(each.description, "lxml").text
	data.assigned_todos = frappe.db.get_list("ToDo", filters={
		'assigned_by':frappe.session.user,
		'status':'Open'
	}, fields="*", ignore_permissions=True)
	for each in data.assigned_todos:
		each.description = BeautifulSoup(each.description, "lxml").text

	data.scrum_projects = get_to_do_linked_projects("SCRUM")

	data.personal_projects = get_to_do_linked_projects("Personal")
	
	return data

def get_to_do_linked_projects(type):
	query = '''
		select
			p.name as project, t.name as todo
		from
			`tabProject` p, `tabToDo` t
		where
			t.reference_type = "Project" and t.reference_name = p.name and p.project_type = '{0}'
			and allocated_to = '{1}'
	'''

	return frappe.db.sql(query.format(type, frappe.session.user), as_dict=True)
