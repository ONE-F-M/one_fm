from one_fm.utils import create_process_task


def execute():
    create_process_task(
        "Leave Management",  # process_name
        "Leave Application",  # erp_document
        "Assign/unassign returning shift workers to HelpDesk User",  # task_description
        method="one_fm.overrides.leave_application.manage_helpdesk_leave_assignments",
        frequency="Cron",
        cron_format="30 8 * * *",
        process_owner=None,
        business_analyst=None,
        task_type="Routine",
        is_routine_task=1,
        is_automated=1
    )
