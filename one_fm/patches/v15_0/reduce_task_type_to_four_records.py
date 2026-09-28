import frappe

KEPT_TASK_TYPES = ["Action", "Process", "Project", "Routine"]
RETIRED_TASK_TYPES = ["Active Repetitive", "develop", "Individual", "Repetitive"]
REPLACEMENT_TASK_TYPE = "Project"


def execute():
    """Leave Task Type holding only Action, Process, Project and Routine."""
    for task_type in KEPT_TASK_TYPES:
        if not frappe.db.exists("Task Type", task_type):
            frappe.get_doc({
                "doctype": "Task Type",
                "name": task_type,
                "is_routine_task": 1 if task_type == "Routine" else 0,
            }).insert(ignore_permissions=True)

    retired = [t for t in RETIRED_TASK_TYPES if frappe.db.exists("Task Type", t)]
    if not retired:
        return

    frappe.db.set_value(
        "Task", {"type": ["in", retired]}, "type", REPLACEMENT_TASK_TYPE, update_modified=False
    )
    frappe.db.set_value(
        "Process Task",
        {"task_type": ["in", retired]},
        "task_type",
        REPLACEMENT_TASK_TYPE,
        update_modified=False,
    )

    for task_type in retired:
        frappe.delete_doc("Task Type", task_type, ignore_permissions=True, force=True)
