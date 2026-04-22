"""
Patch: Setup Interview Console Custom Fields

Comprehensive patch that adds ALL custom fields needed by:
  - Interview Console page
  - Interview override (interview.py)
  - Interview Feedback override (interview_feedback.py)
  - Hiring utils (hiring/utils.py)

Covers three hrms doctypes:
  - Interview Round  (interview_question table, one_fm_nationality)
  - Interview        (total_interview_score, interview_summary_render,
                      custom_hiring_method, career_history, interview_round_child_ref)
  - Interview Feedback (custom_evaluation_criteria, custom_remarks,
                        interview_question_assessment, career_history)

Safe to re-run — uses create_custom_fields(update=True).
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    # ─── Interview Round ──────────────────────────────────────────────
    # Console reads round_doc.interview_question (child table of
    # "Interview Questions") and filters by one_fm_nationality + designation.
    from one_fm.custom.custom_field.interview_round import get_interview_round_custom_fields
    create_custom_fields(get_interview_round_custom_fields(), update=True)

    # ─── Interview ────────────────────────────────────────────────────
    # Console: total_interview_score, interview_summary_render
    # interview.py override: custom_hiring_method, career_history, interview_round_child_ref
    create_custom_fields({
        "Interview": [
            {
                "fieldname": "interview_summary_render",
                "fieldtype": "HTML",
                "label": "Interview Summary",
                "insert_after": "interview_details",
            },
            {
                "fieldname": "total_interview_score",
                "fieldtype": "Float",
                "label": "Total Score",
                "insert_after": "average_rating",
            },
            {
                "fieldname": "custom_hiring_method",
                "fieldtype": "Data",
                "label": "Hiring Method",
                "insert_after": "job_applicant",
                "fetch_from": "job_applicant.one_fm_hiring_method",
                "read_only": 1,
                "translatable": 1,
            },
            {
                "fieldname": "career_history",
                "fieldtype": "Link",
                "label": "Career History",
                "options": "Career History",
                "insert_after": "custom_hiring_method",
                "read_only": 1,
            },
            {
                "fieldname": "interview_round_child_ref",
                "fieldtype": "Link",
                "label": "Interview Round Child Ref",
                "options": "Job Applicant Interview Round",
                "insert_after": "career_history",
                "hidden": 1,
            },
        ]
    }, update=True)

    # ─── Interview Feedback ───────────────────────────────────────────
    from one_fm.custom.custom_field.interview_feedback import get_interview_feedback_custom_fields
    create_custom_fields(get_interview_feedback_custom_fields(), update=True)
