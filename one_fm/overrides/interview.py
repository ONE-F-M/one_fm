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
