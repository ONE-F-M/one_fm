import frappe
from frappe import _
import json
from frappe.utils import get_link_to_form
from hrms.hr.doctype.interview.interview import Interview

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


class InterviewOverride(Interview):
    
    def show_job_applicant_update_dialog(self):
        job_applicant_status = self.get_job_applicant_status()
        if not job_applicant_status:
            return
        job_application_name = frappe.db.get_value("Job Applicant", self.job_applicant, "applicant_name")

        if job_applicant_status == "Accepted":
            frappe.publish_realtime('show_job_applicant_update_dialog', {
            'job_application_name': job_application_name,
            'job_applicant_status': job_applicant_status,
            'job_applicant': self.job_applicant
            })
        elif job_applicant_status == "Rejected":
            frappe.msgprint(
            _("Do you want to update the Job Applicant {0} as {1} based on this interview result?").format(
                frappe.bold(job_application_name), frappe.bold(job_applicant_status)
            ),
            title=_("Update Job Applicant"),
            primary_action={
                "label": _("Mark as {0}").format(job_applicant_status),
                "server_action": "one_fm.overrides.interview.update_job_applicant_status",
                "args": {"job_applicant": self.job_applicant, "status": job_applicant_status},
            },
        )


@frappe.whitelist()
def update_job_applicant_status(args):
    try:
        if isinstance(args, str):
            args = json.loads(args)
        if not args.get("job_applicant"):
            frappe.throw(_("Please specify the job applicant to be updated."))
        job_applicant = frappe.get_doc("Job Applicant", args["job_applicant"])
        if args["status"] == "Shortlisted":
             job_applicant.one_fm_applicant_status = args["status"]
        else:
            job_applicant.status = args["status"]
        job_applicant.save()
        
        frappe.msgprint(
			_("Updated the Job Applicant status to {0}").format(job_applicant.status),
			alert=True,
			indicator="green",
		)
    except Exception:
        job_applicant.log_error("Failed to update Job Applicant status")
        frappe.msgprint(
			_("Failed to update the Job Applicant status"),
			alert=True,
			indicator="red",
		)
