import frappe
import json

@frappe.whitelist()
def get_profile():
    return frappe.get_doc("User", frappe.session.user)

@frappe.whitelist()
def get_defaults(args, todo, assigned_todos):
	
	args = json.loads(args)
	cond = ""
	for a in args:
		if args[a]:
			cond += "AND "+a+"='"+args[a]+"' "
	data = frappe._dict({})
	
	if todo == 'true':
		data.my_todos = frappe.db.sql(f"""
						SELECT * from `tabToDo`
						where allocated_to = '{frappe.session.user}'
						AND status = "Open"
						AND reference_type != 'Project'
						AND assigned_by != '{frappe.session.user}'
						{cond}
						""",as_dict=1)
	else:
		data.my_todos = frappe.db.sql(f"""
						SELECT * from `tabToDo`
						where allocated_to = '{frappe.session.user}'
						AND status = "Open"
						AND reference_type != 'Project'
						AND assigned_by != '{frappe.session.user}'
						""", as_dict=1)
	if assigned_todos == 'false':
		data.assigned_todos = frappe.db.sql(f"""
						SELECT * from `tabToDo`
						where assigned_by ='{frappe.session.user}'
						AND status = "Open"
						AND reference_type != 'Project'
						AND allocated_to != '{frappe.session.user}'
						{cond}
						""",as_dict=1)
	else:
		data.assigned_todos = frappe.db.sql(f"""
						SELECT * from `tabToDo`
						where assigned_by = '{frappe.session.user}'
						AND status = "Open"
						AND reference_type != 'Project'
						AND allocated_to != '{frappe.session.user}'
						""",as_dict=1)
	
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
