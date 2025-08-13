import frappe

def execute():
    erfs = {
        # "ERF-2025-00024": [
        #     "HR-APP-2025-03052",
        #     "HR-APP-2025-03049",
        #     "HR-APP-2025-03024",
        #     "HR-APP-2025-03026",
        #     "HR-APP-2025-03033",
        #     "HR-APP-2025-03046",
        #     "HR-APP-2025-03054",
        #     "HR-APP-2025-03037",
        #     "HR-APP-2025-03034",
        #     "HR-APP-2025-03058"
        # ],
        # "ERF-2024-00059": [
        #     "HR-APP-2025-01332",
        #     "HR-APP-2025-01654"
        # ],
        "ERF-2024-00014":[
            "HR-APP-2025-02565"
        ]
    }

    for erf in erfs:
        for job_applicant in erfs[erf]:
            change_applicant_erf(job_applicant, erf)

def change_applicant_erf(job_applicant, new_erf):
    if not frappe.db.exists("Job Applicant", job_applicant):
        return
    if frappe.db.exists("ERF", new_erf):
        job_applicant_obj = frappe.get_doc("Job Applicant", job_applicant)
        new_erf_obj = frappe.get_doc("ERF", new_erf)
        job_applicant_obj.one_fm_erf = new_erf
        job_applicant_obj.job_title = frappe.db.get_value("Job Opening", {'one_fm_erf': new_erf})
        job_applicant_obj.designation = frappe.db.get_value("Job Opening", job_applicant_obj.job_title, "designation")
        job_applicant_obj.department = new_erf_obj.department
        job_applicant_obj.project = new_erf_obj.project
        job_applicant_obj.one_fm_hiring_method = new_erf_obj.hiring_method
        job_applicant_obj.interview_round = new_erf_obj.interview_round
        job_applicant_obj.flags.ignore_mandatory = True
        job_applicant_obj.save(ignore_permissions=True)
        job_offer = frappe.db.exists('Job Offer', {'job_applicant': job_applicant, 'docstatus': ['<', 2]})
        if job_offer:
            update_job_offer_with_erf_change(job_offer, job_applicant_obj, new_erf_obj, new_erf)

def update_job_offer_with_erf_change(job_offer, job_applicant_obj, new_erf_obj, new_erf):
            operations_shift = {"project": "", "shift_type": "", "site": ""}
            if new_erf_obj.operations_shift:
                operations_shift = frappe.db.get_value(
                    "Operations Shift",
                    new_erf_obj.operations_shift,
                    ["project", "shift_type", "site"],
                    as_dict=1
                )

            frappe.db.sql("""
                UPDATE
                    `tabJob Offer`
                SET
                    employment_type = %s,
                    applicant_name = %s,
                    day_off_category = %s,
                    number_of_days_off = %s,
                    designation = %s,
                    department = %s,
                    one_fm_erf = %s,
                    shift_working = %s,
                    operations_shift = %s,
                    project = %s,
                    default_shift = %s,
                    operations_site = %s
                WHERE
                    name = %s
            """, (
                job_applicant_obj.employment_type,
                job_applicant_obj.applicant_name,
                job_applicant_obj.day_off_category,
                job_applicant_obj.number_of_days_off,
                job_applicant_obj.designation,
                job_applicant_obj.department,
                new_erf,
                new_erf_obj.shift_working,
                new_erf_obj.operations_shift,
                operations_shift["project"],
                operations_shift["shift_type"],
                operations_shift["site"],
                job_offer
            ))
