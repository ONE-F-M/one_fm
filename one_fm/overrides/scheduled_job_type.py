import frappe

def update_scheduled_job_type_from_process_task():
    process_tasks = frappe.get_all(
        "Process Task",
        filters={
        "is_active": True,
        "task_type": "Routine",
        "is_erp_task": True,
        "method": ["is", "set"]
        },
        pluck="name"
    )

    if not process_tasks:
        return

    exists_scheduled_job_types = frappe.get_all(
        "Scheduled Job Type",
        filters={"process_task": ["in", process_tasks]},
        pluck="process_task"
    )

    existing_jobs_set = set(exists_scheduled_job_types)

    for process_task in process_tasks:
        if process_task not in existing_jobs_set:
            print("Re creating scheduled job type for process task {0}".format(process_task))
            process_task_obj = frappe.get_doc("Process Task", process_task)
            print("Creating scheduled job type for method {0}".format(process_task_obj.method))
            process_task_obj.setup_scheduler_events()
            print("Scheduled execution for the method {0} has updated".format(process_task_obj.method))
            print("-----------")
