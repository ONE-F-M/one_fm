import frappe
from frappe import _
from frappe.utils import get_link_to_form

def validate_interview_overlap(self):
    interviewers = [entry.interviewer for entry in self.interview_details] or [""]

    query = """
        SELECT interview.name
        FROM `tabInterview` as interview
        INNER JOIN `tabInterview Detail` as detail
        WHERE
        interview.scheduled_on = %s and interview.name != %s and interview.docstatus != 2
        and (interview.job_applicant = %s and detail.interviewer IN %s) and
        ((from_time < %s and to_time > %s) or
        (from_time > %s and to_time < %s) or
        (from_time = %s))
    """

    overlaps = frappe.db.sql(
        query,
        (
        self.scheduled_on,
        self.name,
        self.job_applicant,
        interviewers,
        self.from_time,
        self.to_time,
        self.from_time,
        self.to_time,
        self.from_time,
        ),
    )

    if overlaps:
        overlapping_details = _("Interview overlaps with {0}").format(
            get_link_to_form("Interview", overlaps[0][0])
        )
        frappe.throw(overlapping_details, title=_("Overlap"))

def update_interview_rounds_in_job_applicant(doc, method):
    if doc.interview_round_child_ref:
        frappe.db.set_value('Job Applicant Interview Round', doc.interview_round_child_ref, 'interview', doc.name)
    if not doc.interview_details:
        doc.append('interview_details', {'interviewer': frappe.session.user})


def validate_job_applicant_mandatory(doc, method):

    if doc.status == "Cleared" and doc.docstatus == 1:

        job_applicant = frappe.get_doc("Job Applicant", doc.job_applicant)

        # Validate mandatory fields before saving
        mandatory_fields = [
            "one_fm_passport_type",
            "applicant_name",
            "status",
            "email_id",
            "one_fm_first_name",
            "one_fm_last_name",
        ]
        missing_fields = [field for field in mandatory_fields if not job_applicant.get(field)]

        if missing_fields:
            frappe.throw(
                _("Job Applicant Doctype is missing mandatory fields which may cause errors when updating it: {0}").format(
                    ", ".join(missing_fields)
                ),
                title=_("Job Applicant Validation"),
            )
