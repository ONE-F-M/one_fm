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
    create_custom_fields({
        "Interview Round": [
            {
                "fieldname": "interview_questions_sb",
                "fieldtype": "Section Break",
                "label": "Interview Questions",
                "insert_after": "expected_skill_set",
                "module": "one_fm",
            },
            {
                "fieldname": "interview_question",
                "fieldtype": "Table",
                "label": "Interview Question",
                "options": "Interview Questions",
                "insert_after": "interview_questions_sb",
                "module": "one_fm",
            },
            {
                "fieldname": "one_fm_nationality",
                "fieldtype": "Link",
                "label": "Nationality",
                "options": "Nationality",
                "insert_after": "designation",
                "description": "Used by Interview Console to match applicant nationality to the correct round.",
                "module": "one_fm",
            },
        ]
    }, update=True)

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
    # Console: custom_evaluation_criteria (Interview Evaluation Detail), custom_remarks
    # interview_feedback.py override + hiring/utils.py: interview_question_assessment (Interview Question Result)
    create_custom_fields({
        "Interview Feedback": [
            {
                "fieldname": "custom_evaluation_criteria",
                "fieldtype": "Table",
                "label": "Evaluation Criteria",
                "options": "Interview Evaluation Detail",
                "insert_after": "feedback",
                "read_only": 1,
            },
            {
                "fieldname": "custom_remarks",
                "fieldtype": "Small Text",
                "label": "Remarks",
                "insert_after": "custom_evaluation_criteria",
            },
            {
                "fieldname": "interview_question_assessment_sb",
                "fieldtype": "Section Break",
                "insert_after": "skill_assessment",
            },
            {
                "fieldname": "interview_question_assessment",
                "fieldtype": "Table",
                "label": "Interview Question Assessment",
                "options": "Interview Question Result",
                "insert_after": "interview_question_assessment_sb",
            },
            {
                "fieldname": "career_history",
                "fieldtype": "Link",
                "label": "Career History",
                "options": "Career History",
                "insert_after": "interview_round",
                "read_only": 1,
            },
        ]
    }, update=True)

    frappe.db.commit()
    print("✅ All interview custom fields installed on Interview Round, Interview, and Interview Feedback!")
