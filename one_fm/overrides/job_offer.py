import frappe
from frappe import _
from frappe.modules import scrub
from frappe.model.mapper import get_mapped_doc
from frappe.utils import (
    cint, flt, get_link_to_form, get_url
)
from hrms.hr.doctype.job_offer.job_offer import JobOffer
from one_fm.utils import validate_mandatory_fields
from one_fm.api.notification import create_notification_log


class JobOfferOverride(JobOffer):
    """
        Inherit Job offer and extended the methods
    """
    def onload(self):
        super(JobOfferOverride, self).onload()
        o_employee = frappe.db.get_value("Onboard Employee", {"job_offer": self.name}, "name") or ""
        self.set_onload("onboard_employee", o_employee)


    def validate(self):
        super(JobOfferOverride, self).validate()
        job_applicant = frappe.get_doc("Job Applicant", self.job_applicant)
        validate_mandatory_fields(job_applicant)
        self.job_offer_validate_attendance_by_timesheet()
        self.validate_job_offer_mandatory_fields()
        # Validate day off
        if not self.number_of_days_off:
            frappe.throw(_("Please set the number of days off."))
        if self.day_off_category == "Weekly":
            if frappe.utils.cint(self.number_of_days_off) > 7:
                frappe.throw(_("Number of days off cannot be more than a week."))
        elif self.day_off_category == "Monthly":
            if frappe.utils.cint(self.number_of_days_off) > 30:
                frappe.throw(_("Number of days off cannot be more than a month."))
        salary_per_person_from_erf = 0
        if self.one_fm_erf and not self.one_fm_salary_structure:
            erf_salary_structure = frappe.db.get_value('ERF', self.one_fm_erf, 'salary_structure')
            if erf_salary_structure:
                self.one_fm_salary_structure = erf_salary_structure
            if not self.base:
                salary_per_person = frappe.db.get_value('ERF', self.one_fm_erf, 'salary_per_person')
                salary_per_person_from_erf = salary_per_person if salary_per_person else 0
        if self.one_fm_salary_structure:
            salary_structure = frappe.get_doc('Salary Structure', self.one_fm_salary_structure)
            total_amount = 0
            self.set('one_fm_salary_details', [])
            base = self.base if self.base else salary_per_person_from_erf
            for salary in salary_structure.earnings:
                if salary.amount_based_on_formula and salary.formula:
                    formula = salary.formula
                    percent = formula.split("*")[1]
                    amount = int(base)*float(percent)
                    total_amount += amount
                    if amount!=0:
                        salary_details = self.append('one_fm_salary_details')
                        salary_details.salary_component = salary.salary_component
                        salary_details.amount = amount
                        self.one_fm_job_offer_total_salary = total_amount
                else:
                    total_amount += salary.amount
                    if salary.amount!=0:
                        salary_details = self.append('one_fm_salary_details')
                        salary_details.salary_component = salary.salary_component
                        salary_details.amount = salary.amount
            self.one_fm_job_offer_total_salary = total_amount
        elif self.one_fm_salary_details:
            total_amount = 0
            for salary in self.one_fm_salary_details:
                total_amount += salary.amount if salary.amount else 0
            self.one_fm_job_offer_total_salary = total_amount
        if frappe.db.exists('Letter Head', 'ONE FM - Job Offer') and not self.letter_head:
            self.letter_head = 'ONE FM - Job Offer'

    def on_update_after_submit(self):
        self.validate_job_offer_mandatory_fields(self)
        if self.workflow_state == 'Submit to Onboarding Officer':
            msg = "Please select {0} to Accept the Offer and Process Onboard"
            if not self.estimated_date_of_joining and not self.onboarding_officer:
                frappe.throw(_(msg.format("<b>Estimated Date of Joining</b> and <b>Onboarding Officer</b>")))
            elif not self.estimated_date_of_joining:
                frappe.throw(_(msg.format("<b>Estimated Date of Joining</b>")))
            elif not self.onboarding_officer:
                frappe.throw(_(msg.format("<b>Onboarding Officer</b>")))
        # Send Notification to Assined Officer to accept the Onboarding Task
        self.notify_onboarding_officer()
        if self.workflow_state in ['Onboarding Officer Rejected', 'Accepted']:
            # Notify Recruiter
            self.notify_recruiter()

    def validate_job_offer_mandatory_fields(self):
        if self.workflow_state == 'Submit for Candidate Response':
            mandatory_field_required = False
            fields = ['Reports To', 'Project', 'Base', 'Salary Structure', 'Project']
            if not self.attendance_by_timesheet:
                fields.append('Operations Shift')
                if self.shift_working:
                    fields.append('Operations Site')
            msg = "Mandatory fields required to Submit Job Offer<br/><br/><ul>"
            for field in fields:
                if field == 'Salary Structure':
                    if not self.get('one_fm_salary_structure'):
                        mandatory_field_required = True
                        msg += '<li>' + field +'</li>'
                elif not self.get(scrub(field)):
                    mandatory_field_required = True
                    msg += '<li>' + field +'</li>'
            if mandatory_field_required:
                frappe.throw(msg + '</ul>')

    def job_offer_validate_attendance_by_timesheet(self):
        if self.attendance_by_timesheet:
            self.shift_working = False
            self.operations_shift = ''
            self.default_shift = ''
            self.operation_site = ''

    def notify_onboarding_officer(self):
        page_link = get_url(self.get_url())
        subject = ("Job Offer {0} is assigned to you for Onboard Employee").format(self.name)
        message = ("Job Offer <a href='{1}'>{0}</a> is assigned to you for Onboard Employee. Please respond immediatly!").format(self.name, page_link)
        create_notification_log(subject, message, [self.onboarding_officer], self)
