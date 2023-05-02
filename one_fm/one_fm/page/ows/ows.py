import frappe
import json
from bs4 import BeautifulSoup
from frappe.utils import get_date_str, getdate, today, month_diff, add_months

@frappe.whitelist()
def get_profile():
    return frappe.get_doc("User", frappe.session.user)


def generate_cond(dict_):
    cond = ""
    for each in dict_:
        if dict_.get(each):
            if each == 'date':
                dateformat = get_date_str(dict_.get(each))
                cond += f" AND {each} = '{dateformat}' "
            elif each == 'name':
                cond += f" AND {each} LIKE '%{dict_.get(each)}%' "
            else:
                cond += f" AND {each} = '{dict_.get(each)}' "
    return cond


@frappe.whitelist()
def get_defaults(args=None, has_todo_filter=0, has_assigned_filter=0):
    if args:
        args = json.loads(args)

        mytodo_cond = generate_cond(args[0]) if int(has_todo_filter) else ""
        myassigned_cond = generate_cond(args[1]) if int(has_assigned_filter) else ""


    data = frappe._dict({})
    data.reset_filters  = 0
    if bool(int(has_todo_filter)):
        data.my_todos = frappe.db.sql(f"""
                        SELECT * from `tabToDo`
                        where allocated_to = '{frappe.session.user}'
                        AND status = "Open"
                        AND reference_type != 'Project'
                        {mytodo_cond}
                        """,as_dict=1)
    else:
        data.my_todos = frappe.db.sql(f"""
                        SELECT * from `tabToDo`
                        where allocated_to = '{frappe.session.user}'
                        AND status = "Open"
                        AND reference_type != 'Project'
                        """, as_dict=1)

    if bool(int(has_assigned_filter)):
        data.assigned_todos = frappe.db.sql(f"""
                        SELECT * from `tabToDo`
                        where assigned_by ='{frappe.session.user}'
                        AND status = "Open"
                        AND reference_type != 'Project'
                        AND allocated_to != '{frappe.session.user}'
                        {myassigned_cond}
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
    data.active_repetitive_projects = get_to_do_linked_projects("Active Repetitive")

    data.routine_tasks = get_to_do_linked_routine_task()

    data.company_objective = get_company_objective()
    data.company_objective_quarter = get_company_objective('Quarterly')
    data.my_objective = get_my_objective()
    data.company_goal = get_company_goal()

    for each in data.my_todos:
        each.description= BeautifulSoup(each.description, "lxml").text
    for one in data.assigned_todos:
        one.description= BeautifulSoup(one.description, "lxml").text
    data.filter_references = get_reference_and_users()
    if not any([bool(mytodo_cond),bool(myassigned_cond)]):
        data.reset_filters = 1
    return data

def get_company_objective(okr_for='Yearly'):
	query = '''
		select
			*
		from
			`tabObjective Key Result`
		where
			'{0}' between start_date and end_date
			and
			company_objective = 1
			and
			okr_for = '{1}'
	'''
	result = frappe.db.sql(query.format(getdate(today()), okr_for), as_dict=True)
	if result:
		if okr_for == 'Yearly':
			return result[0].name
		elif okr_for == 'Quarterly':
			quarter = get_the_quarter(result[0].start_date, result[0].end_date)
			if quarter:
				for res in result:
					if res.quarter == quarter:
						return res.name
	return ''

def get_the_quarter(start_date, end_date, date=today()):
	months_in_qtr = month_diff(end_date, start_date)/4
	if getdate(start_date) <= getdate(date) <= add_months(start_date, months_in_qtr-1):
		return "Q1"
	if add_months(start_date, months_in_qtr) <= getdate(date) <= add_months(start_date, (2*months_in_qtr)-1):
		return "Q2"
	if add_months(start_date, (2*months_in_qtr)) <= getdate(date) <= add_months(start_date, (3*months_in_qtr)-1):
		return "Q3"
	if add_months(start_date, (3*months_in_qtr)) <= getdate(date) <= add_months(start_date, (4*months_in_qtr)-1):
		return "Q4"
	return False

def get_company_goal():
	query = '''
		select
			*
		from
			`tabObjective Key Result`
		where
			is_company_goal = 1
	'''
	result = frappe.db.sql(query, as_dict=True)
	if result:
		return result[0].name
	return ""

def get_my_objective():
	employee = frappe.db.get_value('Employee', {'user_id': frappe.session.user})
	if employee:
		query = '''
			select
				*
			from
				`tabObjective Key Result`
			where
				'{0}' between start_date and end_date
				and
				employee = '{1}'
				and
				okr_for = "Yearly"
		'''
		result = frappe.db.sql(query.format(getdate(today()), employee), as_dict=True)
		if result:
			return result[0].name
	return ''

def get_to_do_linked_routine_task():
	query = '''
		select
			ta.name as task, t.name as todo
		from
			`tabTask` ta, `tabToDo` t
		where
			t.reference_type = "Task" and t.reference_name = ta.name and ta.is_routine_task = 1
			and allocated_to = '{0}'
	'''

	return frappe.db.sql(query.format(frappe.session.user), as_dict=True)

def get_to_do_linked_projects(type):
    query = '''
        select
            p.name as project, t.name as todo
        from
            `tabProject` p, `tabToDo` t
        where
            t.reference_type = "Project" and t.reference_name = p.name and p.type = '{0}'
            and allocated_to = '{1}'
    '''

    return frappe.db.sql(query.format(type, frappe.session.user), as_dict=True)

def get_reference_and_users():
    """
    Get the a list of doctypes for reference and users for assignment
    """

    doctypes = frappe.db.sql("select name as id,name as text from `tabDocType` where istable = '0'",as_dict=1)
    users=frappe.db.sql("select name as id,name as text from `tabUser` where enabled = '1'",as_dict=1)
    return [doctypes,users]
