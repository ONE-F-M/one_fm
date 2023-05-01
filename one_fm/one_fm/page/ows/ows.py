import frappe
import json
from bs4 import BeautifulSoup
from frappe.utils import get_date_str

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

    for each in data.my_todos:
        each.description= BeautifulSoup(each.description, "lxml").text
    for one in data.assigned_todos:
        one.description= BeautifulSoup(one.description, "lxml").text
    data.filter_references = get_reference_and_users()
    if not any([bool(mytodo_cond),bool(myassigned_cond)]):
        data.reset_filters = 1
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




def get_reference_and_users():
    """
    Get the a list of doctypes for reference and users for assignment
    """
    
    doctypes = frappe.db.sql("select name as id,name as text from `tabDocType` where istable = '0'",as_dict=1)
    users=frappe.db.sql("select name as id,name as text from `tabUser` where enabled = '1'",as_dict=1)
    return [doctypes,users]
    
