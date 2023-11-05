from __future__ import unicode_literals

import frappe

def execute():
    doctype = ['Interview Result', 'Job Applicant Interview Schedule', 'Job Applicant Interview Sheet',
        'Interview Sheet General', 'Interview Sheet Attitude', 'Interview Sheet Technical', 'Interview Sheet Experience',
        'Interview Sheet Language', 'Interview Tool', 'Interview Security Awareness',
        'Interview Security Awareness Personal Skill', 'Interview Experience Note', 'Interview General',
        'Interview Technical', 'Interview Attitude', 'Interview Sheet Security Awareness Personal Skill',
        'Interview Sheet Security Awareness'
    ]

    for doc in doctype:
        frappe.delete_doc("DocType", doc)
