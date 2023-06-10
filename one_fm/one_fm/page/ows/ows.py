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

    data.all_todos = frappe.db.sql(f"""
                        SELECT * from `tabToDo`
                        where allocated_to = '{frappe.session.user}'
                        OR assigned_by ='{frappe.session.user}'
                        AND status = "Open"
                        """,as_dict=1)
    data.my_todo_filters = frappe.db.sql(f"""
								SELECT  DISTINCT reference_type,  priority, assigned_by from `tabToDo`
								where allocated_to = '{frappe.session.user}'
								AND status = "Open"
								""",as_dict=1)

    data.assigned_todo_filters = frappe.db.sql(f"""
									SELECT DISTINCT reference_type, priority, allocated_to from `tabToDo`
									where assigned_by = '{frappe.session.user}'
									AND status = "Open"
									AND allocated_to != '{frappe.session.user}'
									""",as_dict=1)

    if bool(int(has_todo_filter)):
        data.my_todos = frappe.db.sql(f"""
                        SELECT * from `tabToDo`
                        where allocated_to = '{frappe.session.user}'
                        AND status = "Open"
                        {mytodo_cond}
                        """,as_dict=1)
    else:
        data.my_todos = frappe.db.sql(f"""
                        SELECT * from `tabToDo`
                        where allocated_to = '{frappe.session.user}'
                        AND status = "Open"
                        """, as_dict=1)

    if bool(int(has_assigned_filter)):
        data.assigned_todos = frappe.db.sql(f"""
                        SELECT * from `tabToDo`
                        where assigned_by ='{frappe.session.user}'
                        AND status = "Open"
                        AND allocated_to != '{frappe.session.user}'
                        {myassigned_cond}
                        """,as_dict=1)
    else:
        data.assigned_todos = frappe.db.sql(f"""
                        SELECT * from `tabToDo`
                        where assigned_by = '{frappe.session.user}'
                        AND status = "Open"
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

    data.okr_year = get_fiscal_year()
    return data

@frappe.whitelist()
def get_okr_details(okr_year, okr_quarter):
	data = frappe._dict({})
	data.company_objective = get_company_objective(okr_year=okr_year)
	data.company_objective_quarter = get_company_objective('Quarterly', okr_year, okr_quarter)
	data.my_objective = get_my_objective(okr_year, okr_quarter)
	data.company_goal = get_company_goal()
	return data

def get_fiscal_year():
	query = '''
		select
			name as id, name as text
		from
			`tabFiscal Year`
		where
			disabled != 1
	'''
	return frappe.db.sql(query, as_dict=True)

def get_company_objective(okr_for='Yearly', okr_year=False, okr_quarter=False):
	query = '''
		select
			name, okr_title, employee, description, year, quarter, okr_for, start_date, end_date
		from
			`tabObjective Key Result`
		where
			company_objective = 1
			and
			okr_for = '{0}'
	'''.format(okr_for)

	if okr_year:
		query += " and year = '{0}'".format(okr_year)
		if okr_quarter:
			query += " and quarter = '{0}'".format(okr_quarter)
	else:
		query += " and '{0}' between start_date and end_date".format(getdate(today()))

	results = frappe.db.sql(query, as_dict=True)
	if results:
		if okr_year or okr_for == 'Yearly':
			return results[0]
		elif okr_for == 'Quarterly':
			quarter = get_the_quarter(results[0].start_date, results[0].end_date)
			if quarter:
				for result in results:
					if result.quarter == quarter:
						return result

	return False

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
			name, okr_title, employee, description, year, quarter, okr_for, start_date, end_date
		from
			`tabObjective Key Result`
		where
			is_company_goal = 1
	'''
	result = frappe.db.sql(query, as_dict=True)
	if result:
		return result[0].name
	return ""

def get_my_objective(year=False, quarter=False):
	employee = frappe.db.get_value('Employee', {'user_id': frappe.session.user})
	if employee:
		query = '''
			select
				name, okr_title, employee, description, year, quarter, okr_for, start_date, end_date
			from
				`tabObjective Key Result`
			where
				employee = '{0}'
				and
				okr_for = "Quarterly"
		'''.format(employee)
		if year:
			query += " and year = '{0}'".format(year)
			if quarter:
				query += " and quarter = '{0}'".format(quarter)
			results = frappe.db.sql(query, as_dict=True)
			if results:
				return results[0]
		else:
			query += " and '{0}' between start_date and end_date".format(getdate(today()))
			results = frappe.db.sql(query, as_dict=True)
			if results:
				quarter = get_the_quarter(results[0].start_date, results[0].end_date)
				if quarter:
					for result in results:
						if result.quarter == quarter:
							return result

		return False

def get_to_do_linked_routine_task():
	query = '''
		select
			ta.name as task, t.name as todo
		from
			`tabTask` ta, `tabToDo` t
		where
			t.reference_type = "Task" and t.reference_name = ta.name and ta.is_routine_task = 1
			and t.allocated_to = '{0}'
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
            and t.allocated_to = '{1}'
    '''

    return frappe.db.sql(query.format(type, frappe.session.user), as_dict=True)

def get_reference_and_users():
    """
    Get the a list of doctypes for reference and users for assignment
    """

    doctypes = frappe.db.sql("select name as id,name as text from `tabDocType` where istable = '0'",as_dict=1)
    users=frappe.db.sql("select name as id,name as text from `tabUser` where enabled = '1'",as_dict=1)
    return [doctypes,users]
