import frappe
from frappe import _
from frappe.modules import scrub
from frappe.model.mapper import get_mapped_doc
from frappe.utils import (
    cint, flt, get_link_to_form, get_url, nowdate
)
from hrms.hr.doctype.job_offer.job_offer import JobOffer
from one_fm.utils import validate_mandatory_fields
from one_fm.api.notification import create_notification_log
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError, close_all_assignments
from one_fm.qr_code_generator import get_qr_code


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
        self.one_fm_erf = job_applicant.one_fm_erf
        validate_mandatory_fields(job_applicant)
        self.job_offer_validate_attendance_by_timesheet()
        self.validate_job_offer_mandatory_fields()
        # Set url qr code
        self.url_qr_code = get_qr_code(get_url(self.get_url()))
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
        # update terms and consitions
        if self.docstatus==0:
            # set job offer terms according to designation (if not set)
            if not self.job_offer_term_template:
                target_offer_template = frappe.db.get_value('Job Offer Templates',{ "name": self.designation }, "name")
                if target_offer_template:
                    self.job_offer_term_template = target_offer_template
                    # Clear existing offer_terms
                    self.set("offer_terms", [])
                    # Add new offer_terms
                    offer_terms = frappe.get_all("Job Offer Term", filters={"parent": target_offer_template}, fields=['offer_term', 'value'])
                    for item in offer_terms:
                        self.append("offer_terms", {
                            "offer_term": item.offer_term,
                            "value": item.value,
                        })

            # Set terms according to default terms and conditions (if not set)
            if not self.select_terms:
                default_terms = frappe.db.get_single_value('Hiring Settings', 'default_terms_and_conditions') or 'Job Offer Acceptance'
                self.select_terms = default_terms
            terms = frappe.db.get_value("Terms and Conditions", self.select_terms, "terms")
            self.terms = frappe.render_template(terms, {
                'applicant_name':self.applicant_name, 'designation':self.designation, 'company':self.company}
            )

    def on_update_after_submit(self):
        self.validate_job_offer_mandatory_fields()
        if self.workflow_state == 'Submit to Onboarding Officer':
            msg = "Please select {0} to Accept the Offer and Process Onboard"
            if not self.estimated_date_of_joining and not self.onboarding_officer:
                frappe.throw(_(msg.format("<b>Estimated Date of Joining</b> and <b>Onboarding Officer</b>")))
            elif not self.estimated_date_of_joining:
                frappe.throw(_(msg.format("<b>Estimated Date of Joining</b>")))
            elif not self.onboarding_officer:
                frappe.throw(_(msg.format("<b>Onboarding Officer</b>")))
            assign_to_onboarding_officer(self)
        if self.workflow_state == 'Accepted' and self.get_onload('onboard_employee'):
            close_all_assignments(self.doctype, self.name)
        # Set offer accepted date
        if self.workflow_state == 'Submit to Onboarding Officer' and not self.one_fm_offer_accepted_date:
            self.one_fm_offer_accepted_date = nowdate()
            self.save(ignore_permissions=True)

    def validate_job_offer_mandatory_fields(self):
        if self.workflow_state == 'Submit for Candidate Response':
            mandatory_field_required = False
            fields = ['Project', 'Base', 'Salary Structure'] if not self.attendance_by_timesheet else ['Base', 'Salary Structure']
            if not self.shift_working and not self.reports_to:
                fields.append("Reports to")
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

    def before_cancel(self):
        employee = self.get_onload('employee')
        if employee:
            frappe.throw(_("Not Allowed to Reject the Job Offer, it is linked with Employee {0}".format(employee)))

def assign_to_onboarding_officer(self):
	try:
		description = f'''
			<p>Here is to inform you that the following { self.doctype }({ self.name }) requires your attention/action.
			<br>
			The details of the request are as follows:<br>
			</p>
			<table border="1" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
				<thead>
					<tr>
						<th style="padding: 10px; text-align: left; background-color: #f2f2f2;">Label</th>
						<th style="padding: 10px; text-align: left; background-color: #f2f2f2;">Value</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td style="padding: 10px;">Job Applicant</td>
						<td style="padding: 10px;">{self.job_applicant}</td>
					</tr>
					<tr>
						<td style="padding: 10px;">Applicant Name</td>
						<td style="padding: 10px;">{self.applicant_name}</td>
					</tr>
					<tr>
						<td style="padding: 10px;">Offer Date</td>
						<td style="padding: 10px;">{self.offer_date}</td>
					</tr>
					<tr>
						<td style="padding: 10px;">Designation</td>
						<td style="padding: 10px;">{self.designation}</td>
					</tr>
					<tr>
						<td style="padding: 10px;">Reports To</td>
						<td style="padding: 10px;">{self.reports_to}</td>
					</tr>
				</tbody>
			</table>
		'''
		add_assignment({
			'doctype': self.doctype,
			'name': self.name,
			'assign_to': [self.onboarding_officer],
			'description': _(description)
		})
		self.add_comment("Comment", _("Assign to Onboarding Officer {0} to process the request".format(self.onboarding_officer)))
	except DuplicateToDoError:
		frappe.message_log.pop()
		pass
