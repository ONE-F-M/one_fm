import frappe
from one_fm.operations.report.roster_projection_view.roster_projection_view import execute as report_execute
from one_fm.operations.doctype.operations_post.operations_post import create_post_schedule_for_operations_post


def execute():
    """
        Get the list of projects with 0 Post Schedules  from the roster projection view report and Create the post schedules for projects with 0 
    """
    filters = frappe._dict({
        'month':'06',
        'year':'2023'
    })
    result = report_execute(filters=filters)
    if result and len(result) > 1:
        project_set = set()
        for each in result[1]:
            if each.ps_qty in [0.0,0]:
                project_set.add(each.get('project'))
        update_ops_post(project_set)
    
    

def update_ops_post(projects):
    try:
        tuple_projects = tuple(projects)
        query = (f"Select name from `tabOperations Post` where project in {tuple_projects}")
        response = frappe.db.sql(query,as_dict=1)
        if response:
            posts = [i.name for i in response]
    except:
        frappe.log_error("Post Schedule Creation Error",frappe.get_traceback())
    
    try:
        for each in posts:
            print("CREATING FOR ",each)
            doc = frappe.get_doc("Operations Post",each)
            create_post_schedule_for_operations_post(doc)
    except:
        frappe.log_error("Error Creating Post Schedules",frappe.get_traceback())
    
    
    


            