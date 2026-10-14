# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt
from datetime import date, timedelta

import frappe
from frappe.model.document import Document

from one_fm.api.v1.utils import response


class EmployeeWeeklyAction(Document):
    pass

def get_week_dates(offset=0):
    """Get dates from Sunday to Saturday for a given week offset.
    offset=0 → current week, offset=1 → next week, etc.
    """
    today = date.today()
    weekday = today.weekday()
    start_of_week = today - timedelta(days=weekday + 1 if weekday != 6 else 0) + timedelta(weeks=offset)
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week.strftime('%Y-%m-%d'), end_of_week.strftime('%Y-%m-%d')

@frappe.whitelist()
def fetch_todos(employee: str):
    try:
        allocated_to = frappe.db.get_value("Employee", employee, "user_id")
        if not allocated_to:
            return response("User Not Found", 404)

        week_todos = get_to_do_linked_projects(allocated_to)
        return response("Success", 200, week_todos)

    except Exception:
        frappe.log_error(
            title="Error fetching ToDo on employee weekly report",
            message=frappe.get_traceback()
        )
        return response("Error", 400)

def get_to_do_linked_projects(allocated_to):
    query = '''
        select
            p.name as project, t.name as todo, t.type, t.description, t.date, t.reference_name, t.reference_type
        from
            `tabProject` p, `tabToDo` t
        where
            t.reference_type = "Project" and t.reference_name = p.name and t.allocated_to = '{0}' and t.status='Open'
    '''
    return frappe.db.sql(query.format(allocated_to), as_dict=True)
