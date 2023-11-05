from __future__ import unicode_literals

import frappe

def execute():
    doctype = ['Job Applicant-one_fm_interview_and_career_history_score', 'Job Applicant-one_fm_average_interview_score',
        'Job Applicant-one_fm_job_applicant_score', 'Job Applicant-one_fm_interview_schedules_section',
        'Job Applicant-one_fm_interview_schedules'
    ]

    for doc in doctype:
        frappe.delete_doc("Custom Field", doc)
