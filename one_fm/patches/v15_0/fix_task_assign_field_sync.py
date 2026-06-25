import frappe
from frappe.desk.form.assign_to import add as add_assignment


def execute():
    """
    Fix out-of-sync _assign field on Task doctype.

    When tasks moved to 'Pending Review', ToDos for assignees were cancelled,
    which removed them from the _assign field. This patch re-creates missing
    ToDo assignments for all tasks where custom_assigned_to has users not
    reflected in _assign.
    """
    task_assignments = frappe.db.sql("""
        SELECT ta.parent as task_name, ta.user
        FROM `tabTask Assignment` ta
        JOIN `tabTask` t ON t.name = ta.parent
        WHERE (t._assign IS NULL
               OR t._assign = ''
               OR t._assign NOT LIKE CONCAT('%%', ta.user, '%%'))
        AND ta.user IS NOT NULL
        AND ta.user != ''
    """, as_dict=True)

    if not task_assignments:
        return

    frappe.log_error(
        message=f"Fixing {len(task_assignments)} out-of-sync Task assignments",
        title="Patch: fix_task_assign_field_sync"
    )

    for row in task_assignments:
        try:
            add_assignment({
                'assign_to': [row.user],
                'doctype': 'Task',
                'name': row.task_name,
                'description': frappe.db.get_value('Task', row.task_name, 'subject'),
            })
        except Exception:
            frappe.log_error(
                message=f"Failed to fix assignment for {row.task_name} → {row.user}",
                title="Patch: fix_task_assign_field_sync"
            )
