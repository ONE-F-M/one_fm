import frappe

# Task Type records to keep. "Process" is created if missing.
KEEP_TASK_TYPES = ["Action", "Process", "Project", "Routine"]

# Task Type records to delete. Every Task.type / Process Task.task_type row
# pointing at any of these is repointed to "Project" before the record is
# removed, per the reporter's confirmed mapping (Routine is kept as-is and
# is never touched here).
DELETED_TASK_TYPES = ["Active Repetitive", "develop", "Individual", "Repetitive"]
REPLACEMENT_TASK_TYPE = "Project"


def execute():
    """Reduce Task Type to exactly Action, Process, Project, Routine.

    Idempotent: safe to run multiple times. On a second run there is
    nothing left to repoint or delete, and "Process" already exists, so
    the patch is a no-op.
    """

    # 1. Make sure all four target Task Types exist (creates "Process" the
    # first time; no-op afterwards).
    for task_type in KEEP_TASK_TYPES:
        if not frappe.db.exists("Task Type", task_type):
            frappe.get_doc({
                "doctype": "Task Type",
                "name": task_type,
                "is_routine_task": 1 if task_type == "Routine" else 0,
            }).insert(ignore_permissions=True)

    # Make sure the replacement target exists before repointing anything at it.
    if not frappe.db.exists("Task Type", REPLACEMENT_TASK_TYPE):
        frappe.get_doc({
            "doctype": "Task Type",
            "name": REPLACEMENT_TASK_TYPE,
            "is_routine_task": 0,
        }).insert(ignore_permissions=True)

    existing_deleted_types = [
        t for t in DELETED_TASK_TYPES if frappe.db.exists("Task Type", t)
    ]

    if existing_deleted_types:
        # 2. Repoint Task.type rows away from the deleted types to "Project".
        frappe.db.sql(
            """
            UPDATE `tabTask`
            SET `type` = %s
            WHERE `type` IN ({placeholders})
            """.format(placeholders=", ".join(["%s"] * len(existing_deleted_types))),
            [REPLACEMENT_TASK_TYPE] + existing_deleted_types,
        )

        # 3. Repoint Process Task.task_type rows away from the deleted types
        # to "Project".
        frappe.db.sql(
            """
            UPDATE `tabProcess Task`
            SET `task_type` = %s
            WHERE `task_type` IN ({placeholders})
            """.format(placeholders=", ".join(["%s"] * len(existing_deleted_types))),
            [REPLACEMENT_TASK_TYPE] + existing_deleted_types,
        )

        # 4. Delete the now-unreferenced Task Type records.
        for task_type in existing_deleted_types:
            frappe.delete_doc(
                "Task Type",
                task_type,
                ignore_permissions=True,
                force=True,
            )

    frappe.db.commit()
