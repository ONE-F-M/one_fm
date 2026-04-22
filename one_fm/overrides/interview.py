import frappe
from frappe import _
import json
from frappe.utils import get_link_to_form
from hrms.hr.doctype.interview.interview import Interview
from one_fm.templates.pages.applicant_docs import send_applicant_doc_magic_link

def validate_interview_overlap(self):
    interviewers = [entry.interviewer for entry in self.interview_details] or [""]

    Interview = frappe.qb.DocType("Interview")
    Detail = frappe.qb.DocType("Interview Detail")

    query = (
        frappe.qb.from_(Interview)
        .join(Detail).on(Detail.parent == Interview.name)
        .select(Interview.name)
        .where(Interview.scheduled_on == self.scheduled_on)
        .where(Interview.name != self.name)
        .where(Interview.docstatus != 2)
        .where(Interview.job_applicant == self.job_applicant)
        .where(Detail.interviewer.isin(interviewers))
        .where(
            ((Interview.from_time < self.from_time) & (Interview.to_time > self.to_time))
            | ((Interview.from_time > self.from_time) & (Interview.to_time < self.to_time))
            | (Interview.from_time == self.from_time)
        )
    )

    overlaps = query.run()

    if overlaps:
        overlapping_details = _("Interview overlaps with {0}").format(
            get_link_to_form("Interview", overlaps[0][0])
        )
        frappe.throw(overlapping_details, title=_("Overlap"))

def update_interview_rounds_in_job_applicant(doc, method):
    if doc.get('interview_round_child_ref'):
        frappe.db.set_value('Job Applicant Interview Round', doc.get('interview_round_child_ref'), 'interview', doc.name)
    if not doc.interview_details:
        doc.append('interview_details', {'interviewer': frappe.session.user})


class InterviewOverride(Interview):

    def show_job_applicant_update_dialog(self):
        job_applicant_status = self.get_job_applicant_status()
        if not job_applicant_status:
            return
        job_application_name = frappe.db.get_value("Job Applicant", self.job_applicant, "applicant_name")

        if job_applicant_status == "Accepted":
            frappe.publish_realtime(
                event = 'show_job_applicant_update_dialog',
                message = {
                    'job_application_name': job_application_name,
                    'job_applicant_status': job_applicant_status,
                    'job_applicant': self.job_applicant
                },
                user = frappe.session.user
            )
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
    frappe.only_for(["HR Manager", "HR User", "Recruiter", "Senior Recruiter"])
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

        if job_applicant.status == "Accepted":
            send_applicant_doc_magic_link(job_applicant.name, job_applicant.applicant_name, job_applicant.one_fm_designation)
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

def update_from_to_date_null(doc, method):
    if doc.get("custom_hiring_method") == "A la carte Recruitment":
        doc.from_time = None
        doc.to_time = None