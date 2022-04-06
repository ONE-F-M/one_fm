# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe, json
from frappe.utils import (
    get_url, fmt_money, month_diff, add_days, add_years, getdate, flt, get_link_to_form
)
from frappe.model.mapper import get_mapped_doc
from one_fm.api.notification import create_notification_log
from frappe.modules import scrub
from frappe import _
from frappe.desk.form import assign_to
from one_fm.processor import sendemail
from one_fm.templates.pages.career_history import send_career_history_magic_link
from one_fm.templates.pages.applicant_docs import send_applicant_doc_magic_link
from one_fm.one_fm.doctype.erf.erf import (
    set_description_by_performance_profile, set_erf_skills_in_job_opening, set_erf_language_in_job_opening
)


@frappe.whitelist()
def get_performance_profile_resource():
    file_path = frappe.db.get_value('Hiring Settings', None, 'performance_profile_resource')
    if file_path:
        return get_url(file_path)

@frappe.whitelist()
def get_performance_profile_guid():
    file_path = frappe.db.get_value('Hiring Settings', None, 'performance_profile_guid')
    if file_path:
        return get_url(file_path)

def validate_job_offer(doc, method):
    validate_job_offer_mandatory_fields(doc)
    # Validate day off
    if not doc.number_of_days_off:
        frappe.throw(_("Please set the number of days off."))
    if doc.day_off_category == "Weekly":
        if frappe.utils.cint(doc.number_of_days_off) > 7:
            frappe.throw(_("Number of days off cannot be more than a week."))
    elif doc.day_off_category == "Monthly":
        if frappe.utils.cint(doc.number_of_days_off) > 30:
            frappe.throw(_("Number of days off cannot be more than a month."))
    salary_per_person_from_erf = 0
    if doc.one_fm_erf and not doc.one_fm_salary_structure:
        erf_salary_structure = frappe.db.get_value('ERF', doc.one_fm_erf, 'salary_structure')
        if erf_salary_structure:
            doc.one_fm_salary_structure = erf_salary_structure
        if not doc.base:
            salary_per_person = frappe.db.get_value('ERF', doc.one_fm_erf, 'salary_per_person')
            salary_per_person_from_erf = salary_per_person if salary_per_person else 0
    if doc.one_fm_salary_structure:
        salary_structure = frappe.get_doc('Salary Structure', doc.one_fm_salary_structure)
        total_amount = 0
        doc.set('one_fm_salary_details', [])
        base = doc.base if doc.base else salary_per_person_from_erf
        for salary in salary_structure.earnings:
            if salary.amount_based_on_formula and salary.formula:
                formula = salary.formula
                percent = formula.split("*")[1]
                amount = int(base)*float(percent)
                total_amount += amount
                if amount!=0:
                    salary_details = doc.append('one_fm_salary_details')
                    salary_details.salary_component = salary.salary_component
                    salary_details.amount = amount
                    doc.one_fm_job_offer_total_salary = total_amount
            else:
                total_amount += salary.amount
                if salary.amount!=0:
                    salary_details = doc.append('one_fm_salary_details')
                    salary_details.salary_component = salary.salary_component
                    salary_details.amount = salary.amount
        doc.one_fm_job_offer_total_salary = total_amount
    elif doc.one_fm_salary_details:
        total_amount = 0
        for salary in doc.one_fm_salary_details:
            total_amount += salary.amount if salary.amount else 0
        doc.one_fm_job_offer_total_salary = total_amount
    if frappe.db.exists('Letter Head', 'ONE FM - Job Offer') and not doc.letter_head:
        doc.letter_head = 'ONE FM - Job Offer'

def validate_job_offer_mandatory_fields(job_offer):
    if job_offer.workflow_state == 'Submit for Candidate Response':
        mandatory_field_required = False
        fields = ['Reports To', 'Project', 'Operations Site', 'Operations Shift']
        msg = "Mandatory fields required to Submit Job Offer<br/><br/><ul>"
        for field in fields:
            if not job_offer.get(scrub(field)):
                mandatory_field_required = True
                msg += '<li>' + field +'</li>'
        if mandatory_field_required:
            frappe.throw(msg + '</ul>')

def after_insert_job_applicant(doc, method):
    notify_recruiter_and_requester_from_job_applicant(doc, method)

def notify_recruiter_and_requester_from_job_applicant(doc, method):
    if doc.one_fm_erf:
        recipients = []
        erf_details = frappe.db.get_values('ERF', filters={'name': doc.one_fm_erf},
        fieldname=["erf_requested_by", "recruiter_assigned", "secondary_recruiter_assigned"], as_dict=True)
        if erf_details and len(erf_details) == 1:
            if erf_details[0].erf_requested_by and erf_details[0].erf_requested_by != 'Administrator':
                recipients.append(erf_details[0].erf_requested_by)
            if erf_details[0].recruiter_assigned:
                recipients.append(erf_details[0].recruiter_assigned)
            if erf_details[0].secondary_recruiter_assigned:
                recipients.append(erf_details[0].secondary_recruiter_assigned)
        designation = frappe.db.get_value('Job Opening', doc.job_title, 'designation')
        page_link = get_url("/desk#Form/Job Applicant/" + doc.name)
        message = "<p>There is a Job Application created for the position {2} <a href='{0}'>{1}</a></p>".format(page_link, doc.name, designation)

        if recipients:
            sendemail(
                recipients= recipients,
                subject='Job Application created for {0}'.format(designation),
                message=message,
                reference_doctype=doc.doctype,
                reference_name=doc.name
            )

@frappe.whitelist()
def make_employee(source_name, target_doc=None):
    def set_missing_values(source, target):
        set_map_job_applicant_details(target, source.name, source)

    doc = get_mapped_doc("Job Applicant", source_name, {
        "Job Applicant": {
            "doctype": "Employee",
            "field_map": {
                "applicant_name": "employee_name",
            }
        }
    }, target_doc, set_missing_values)
    return doc

@frappe.whitelist()
def make_employee_from_job_offer(source_name, target_doc=None):
    def set_missing_values(source, target):
        if source.one_fm_salary_structure:
            target.one_fm_salary_type = frappe.db.get_value('Salary Structure', source.one_fm_salary_structure, 'payroll_frequency')
            salary_structure = frappe.get_doc('Salary Structure', source.one_fm_salary_structure)
            if salary_structure.earnings:
                for earning in salary_structure.earnings:
                    if earning.salary_component == 'Basic':
                        target.one_fm_basic_salary = earning.amount
            if source.base:
                target.one_fm_basic_salary = source.base
            target.salary_mode = salary_structure.mode_of_payment
        set_map_job_applicant_details(target, source.job_applicant)
    doc = get_mapped_doc("Job Offer", source_name, {
        "Job Offer": {
            "doctype": "Employee",
            "field_map": {
                "applicant_name": "employee_name",
                "name": "job_offer",
                "one_fm_salary_structure": "job_offer_salary_structure",
                "estimated_date_of_joining": "date_of_joining",
                "operations_site": "site",
                "operations_shift": "shift"
            }
        }
    }, target_doc, set_missing_values)
    return doc

def set_map_job_applicant_details(target, job_applicant_id, job_applicant=False):
    if not job_applicant:
        job_applicant = frappe.get_doc('Job Applicant', job_applicant_id)
        target.nationality_no = job_applicant.nationality_no
        target.nationality_subject = job_applicant.nationality_subject
        target.date_of_naturalization = job_applicant.date_of_naturalization

    fields_map = {'personal_email': 'email_id', 'middle_name': 'one_fm_second_name',
        'one_fm_civil_id': 'one_fm_cid_number', 'cell_number': 'one_fm_contact_number',
        'date_of_issue': 'one_fm_passport_issued', 'valid_upto': 'one_fm_passport_expire',
        'place_of_issue': 'one_fm_passport_holder_of',
        'one_fm__highest_educational_qualification': 'one_fm_educational_qualification'}
    for field in fields_map:
        target.set(field, job_applicant.get(fields_map[field]))

    one_fm_prefix_fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'passport_number', 'marital_status']
    for field in one_fm_prefix_fields:
        target.set(field, job_applicant.get('one_fm_'+field))

    target.department, target.designation, target.grade, target.project = frappe.db.get_value("ERF", \
		job_applicant.one_fm_erf, ["department", "designation", "grade", "project"])

    target.status = 'Active'
    if target.department:
        dept_code = frappe.db.get_value('Department', target.department, 'department_code')
        target.department_code = dept_code if dept_code else ''

    external_work_history = target.append('external_work_history')
    external_work_history.company_name = job_applicant.one_fm_current_employer
    external_work_history.designation = job_applicant.one_fm_current_job_title
    external_work_history.salary = job_applicant.one_fm_current_salary
    exp_in_month = month_diff(job_applicant.one_fm_employment_end_date, job_applicant.one_fm_employment_start_date)
    if exp_in_month:
        external_work_history.total_experience = exp_in_month / 12

def employee_after_insert(doc, method):
    create_salary_structure_assignment(doc, method)
    update_erf_close_with(doc)
    create_wp_for_transferable_employee(doc)
    create_leave_policy_assignment(doc)

def create_leave_policy_assignment(doc):
    '''
        Method to create Leave Policy Assignment for an Employee, if employee have a Leave Policy
        Create Leave Policy based on Joining Date
        args:
            doc: Employee Object
    '''
    if doc.leave_policy:
        assignment = frappe.new_doc("Leave Policy Assignment")
        assignment.employee = doc.name
        assignment.assignment_based_on = 'Joining Date'
        assignment.leave_policy = doc.leave_policy
        assignment.effective_from = doc.date_of_joining
        assignment.effective_to = add_years(doc.date_of_joining, 1)
        assignment.carry_forward = True
        assignment.leaves_allocated = True # Since Leaves will be allocated from ONE FM Scheduler
        assignment.save()
        assignment.submit()

@frappe.whitelist()
def grant_leave_alloc_for_employee(doc):
    if not doc.leaves_allocated:
        from erpnext.hr.doctype.leave_policy_assignment.leave_policy_assignment import get_leave_type_details
        leave_allocations = {}
        leave_type_details = get_leave_type_details()

        leave_policy = frappe.get_doc("Leave Policy", doc.leave_policy)
        date_of_joining = frappe.db.get_value("Employee", doc.employee, "date_of_joining")

        for leave_policy_detail in leave_policy.leave_policy_details:
            if not leave_type_details.get(leave_policy_detail.leave_type).is_lwp:
                leave_allocation, new_leaves_allocated = doc.create_leave_allocation(
                    leave_policy_detail.leave_type, leave_policy_detail.annual_allocation,
                    leave_type_details, date_of_joining
                )

                leave_allocations[leave_policy_detail.leave_type] = {"name": leave_allocation, "leaves": new_leaves_allocated}

        doc.db_set("leaves_allocated", 1)
        return leave_allocations

def create_wp_for_transferable_employee(doc):
    """
    This method create work permit record for transferable employee after employee got created in the onboarding process in transfer paper. then, notify operator
    """
    tp_list = frappe.db.get_list('Transfer Paper',{'workflow_state':'Under Process','civil_id':doc.one_fm_civil_id},['name','civil_id'])
    if tp_list and len(tp_list)>0:
        for tp in tp_list:
            if not frappe.db.exists("Work Permit", {"transfer_paper":tp.name}):#employee is created work permit not yet created
                employee = frappe.db.get_value("Employee", {"one_fm_civil_id":tp.civil_id})
                if employee:
                    from one_fm.grd.doctype.work_permit import work_permit
                    work_permit.create_work_permit_transfer(tp.name,employee)#create wp for local transfer
                    notify_grd_operator_for_transfer_wp_record(tp)

def notify_grd_operator_for_transfer_wp_record(tp):
    operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_transfer")
    wp = frappe.db.get_value("Work Permit",{'transfer_paper':tp.name,'work_permit_status':'Draft'})
    if wp:
        wp_record = frappe.get_doc('Work Permit', wp)
        page_link = get_url("/desk#Form/Work Permit/" + wp_record.name)
        subject = ("Apply for Transfer Work Permit Online")
        message = "<p>Please Apply for Transfer Work Permit Online for employee civil ID: <a href='{0}'>{1}</a>.</p>".format(page_link, wp_record.civil_id)
        create_notification_log(subject, message, [operator], wp_record)

def update_erf_close_with(doc):
    if doc.one_fm_erf:
        erf = frappe.get_doc('ERF', doc.one_fm_erf)
        employees = erf.append('erf_employee')
        employees.employee = doc.name
        erf.save(ignore_permissions=True)

@frappe.whitelist()
def create_salary_structure_assignment(doc, method):
    if doc.job_offer_salary_structure:
        assignment = frappe.new_doc("Salary Structure Assignment")
        assignment.employee = doc.name
        assignment.salary_structure = doc.job_offer_salary_structure
        assignment.company = doc.company
        assignment.from_date = doc.date_of_joining
        assignment.base = doc.one_fm_basic_salary
        assignment.save(ignore_permissions = True)

@frappe.whitelist()
def update_job_offer_from_applicant(jo, status):
    job_offer = frappe.get_doc('Job Offer', jo)
    job_offer.status = status
    job_offer.save()

@frappe.whitelist()
def update_applicant_status(names, status_field, status, reason_for_rejection=False):
    names = json.loads(names)
    for name in names:
        job_applicant = frappe.get_doc("Job Applicant", name)
        job_applicant.set(status_field, status)
        job_applicant.one_fm_reason_for_rejection = reason_for_rejection if reason_for_rejection else ''
        job_applicant.save()

@frappe.whitelist()
def send_magic_link_to_selected_applicants(names, magic_link):
    names = json.loads(names)
    for name in names:
        applicant_data = frappe.db.get_values("Job Applicant", name, ["applicant_name", "designation"], as_dict=True)
        if applicant_data and len(applicant_data) > 0:
            if magic_link == 'Career History':
                send_career_history_magic_link(name, applicant_data[0].applicant_name, applicant_data[0].designation)
            elif magic_link == 'Applicant Doc':
                send_applicant_doc_magic_link(name, applicant_data[0].applicant_name, applicant_data[0].designation)

@frappe.whitelist()
def add_remove_salary_advance(names, dialog):
    names = json.loads(names)
    job_offer_list = []
    for name in names:
        job_offer = frappe.get_doc("Job Offer", name)
        if not job_offer.one_fm_notified_finance_department:
            args = json.loads(dialog)
            job_offer.one_fm_provide_salary_advance = args['one_fm_provide_salary_advance']
            if job_offer.one_fm_provide_salary_advance:
                job_offer.one_fm_salary_advance_amount = args['one_fm_salary_advance_amount']
            job_offer.save(ignore_permissions=True)
            if args['notify_finance_department']:
                job_offer_list.append(job_offer)

    if job_offer_list and len(job_offer_list) > 0:
        notify_finance_job_offer_salary_advance(job_offer_list=job_offer_list)

# Notify Daily
@frappe.whitelist()
def notify_finance_job_offer_salary_advance(job_offer_id=None, job_offer_list=None):
    if not job_offer_list:
        if job_offer_id:
            filters = {'name': job_offer_id}
        else:
            filters = {
                'one_fm_provide_salary_advance': 1, 'one_fm_salary_advance_paid': 0,
                'one_fm_salary_advance_amount': ['>', 0], 'one_fm_notified_finance_department': 0
            }
        job_offer_list = frappe.db.get_list('Job Offer', filters, ['name', 'one_fm_salary_advance_amount'])
    recipient = frappe.db.get_value('Hiring Settings', None, 'notify_finance_department_for_job_offer_salary_advance')

    if recipient and job_offer_list and len(job_offer_list)>0:
        message = "<p>Job Offer listed below needs Advance Salary</p><ol>"
        for job_offer in job_offer_list:
            doc = frappe.get_doc('Job Offer', job_offer.name)
            frappe.db.set_value('Job Offer', job_offer.name, 'one_fm_notified_finance_department', True)
            page_link = get_url("/desk#Form/Job Offer/"+job_offer.name)
            message += "<li><a href='{0}'>{1}</a>: {2}</li>".format(page_link, job_offer.name,
                fmt_money(abs(job_offer.one_fm_salary_advance_amount), 3, 'KWD'))
        message += "<ol>"
        sendemail(
            recipients=[recipient],
            subject=_('Advance Salary for Job Offer'),
            message=message,
            header=['Payment Request for Job Offer Advance Salary', 'yellow'],
        )

@frappe.whitelist()
def get_onboarding_details(parent, parenttype):
	return frappe.get_all("Onboard Employee Activity",
		fields=["action", "role", "user", "required_for_employee_creation", "description"],
		filters={"parent": parent, "parenttype": parenttype},
		order_by= "idx")

@frappe.whitelist()
def make_transfer_paper_from_job_offer(source_name, target_doc=None):
    offer_record = frappe.get_doc('Job Offer',source_name)
    applicant = frappe.get_doc('Job Applicant',offer_record.job_applicant)
    if not frappe.db.exists("Transfer Paper", {'applicant': offer_record.job_applicant}):
        if applicant.one_fm_notify_recruiter:
            doc = get_mapped_doc("Job Applicant", offer_record.job_applicant, {
                "Job Applicant": {
                    "doctype": "Transfer Paper",
                    "field_map": {
                        "one_fm_previous_company_trade_name_in_arabic": "previous_company_trade_name_arabic",
                        "one_fm__previous_company_authorized_signatory_name_arabic":"previous_company_authorized_signatory_name_arabic",
                        "one_fm_previous_company_contract_file_number":"previous_company_contract_file_number",
                        "one_fm_previous_company_issuer_number":"previous_company_issuer_number",
                        "one_fm_previous_company_pam_file_number":"previous_company_pam_file_number",
                        "one_fm_work_permit_salary":"previous_company_work_permit_salary",
                        "one_fm_work_permit_number":"work_permit_number",
                        "one_fm_last_working_date":"end_work_date",
                        "one_fm_duration_of_work_permit":"previous_company_duration_of_work_permit",
                        "name":"applicant"
                    }
                }
            }, target_doc)
        elif not applicant.one_fm_notify_recruiter:
            doc = frappe.msgprint(_("Please Wait for GRD Response Regarding Transfer Checking"))
    return doc

def update_onboarding_doc(doc, is_trash=False, cancel_oe=False):
    if frappe.get_meta(doc.doctype).has_field("onboard_employee") and doc.onboard_employee:
        onboard_employee = frappe.get_doc('Onboard Employee', doc.onboard_employee)
        doc_field_prefix = scrub(doc.doctype)
        if frappe.get_meta('Onboard Employee').has_field(doc_field_prefix+"_status"):
            if is_trash:
                onboard_employee.set(doc_field_prefix+"_status", '')
            else:
                onboard_employee.set(doc_field_prefix+"_status", doc.workflow_state)
        if frappe.get_meta('Onboard Employee').has_field(doc_field_prefix):
            if is_trash or cancel_oe:
                onboard_employee.set(doc_field_prefix, '')
                if frappe.get_meta('Onboard Employee').has_field(doc_field_prefix+"_name"):
                    onboard_employee.set(doc_field_prefix+"_name", doc.name)
            else:
                onboard_employee.set(doc_field_prefix, doc.name)
        if frappe.get_meta('Onboard Employee').has_field(doc_field_prefix+"_docstatus"):
            if is_trash:
                onboard_employee.set(doc_field_prefix+"_docstatus", '')
            else:
                onboard_employee.set(doc_field_prefix+"_docstatus", doc.docstatus)
        if frappe.get_meta('Onboard Employee').has_field(doc_field_prefix+"_progress"):
            if is_trash:
                onboard_employee.set(doc_field_prefix+"_progress", 0)
            else:
                onboard_employee.set(doc_field_prefix+"_progress", doc.progress)
        onboard_employee.save(ignore_permissions=True);
        if cancel_oe:
            onboard_employee.reload()
            onboard_employee.cancel()

def job_offer_on_update_after_submit(doc, method):
    validate_job_offer_mandatory_fields(doc)
    if doc.workflow_state == 'Submit to Onboarding Officer':
        if not doc.estimated_date_of_joining:
            frappe.throw(_('Please Select Estimated Date of Joining to Accept Offer'))
        if not doc.onboarding_officer:
            frappe.throw(_("Please Select Onboarding Officer to Process Onboard"))
        # Send Notification to Assined Officer to accept the Onboarding Task
        notify_onboarding_officer(doc)
    if doc.workflow_state == 'Onboarding Officer Rejected':
        # Notify Recruiter
        notify_recruiter(doc)
    if doc.workflow_state == 'Accepted':
        # Notify Recruiter
        notify_recruiter(doc)

def notify_onboarding_officer(job_offer):
    page_link = get_url("/desk#Form/Job Offer/" + job_offer.name)
    subject = ("Job Offer {0} is assigned to you for Onboard Employee").format(job_offer.name)
    message = ("Job Offer <a href='{1}'>{0}</a> is assigned to you for Onboard Employee. Please respond immediatly!").format(job_offer.name, page_link)
    create_notification_log(subject, message, [job_offer.onboarding_officer], job_offer)

def notify_recruiter(job_offer):
    recruiter = frappe.db.get_value('ERF', job_offer.one_fm_erf, ['recruiter_assigned'])
    if recruiter:
        user_name = frappe.get_value("User", job_offer.onboarding_officer, "full_name")
        page_link = get_url("/desk#Form/Job Offer/" + job_offer.name)
        subject = ("Job Offer {0} is {1} by Onboard Officer {2}").format(job_offer.name, job_offer.workflow_state, user_name)
        message = ("Job Offer <a href='{1}'>{0}</a> is {2} by Onboard Officer {3}").format(job_offer.name, page_link, job_offer.workflow_state, user_name)
        create_notification_log(subject, message, [recruiter], job_offer)

@frappe.whitelist()
def btn_create_onboarding_from_job_offer(job_offer):
    if frappe.db.exists('Job Offer', {'name': job_offer}):
        create_onboarding_from_job_offer(frappe.get_doc('Job Offer', job_offer))
    else:
        frappe.throw(_('There is no job offer {0} exists').format(job_offer))

# Method to create Onboard Employee doctype from Job Offer
def create_onboarding_from_job_offer(job_offer):
    # Onboard Employee document can create for Candidate Accepted Job Offer
    if job_offer.status == 'Accepted':
        # Onboard Employee document can create only if Job Offer is assigned to an Onboarding Officer
        if not job_offer.onboarding_officer:
            frappe.msgprint(_("Please Select Onboarding Officer to Create Onboard Employee"))
        # Onboard Employee document can create only if there is no Onboard Employee document is linke with this Job Offer
        elif not frappe.db.exists('Onboard Employee', {'job_offer': job_offer.name}):
            # Fields in the job offer
            fields = ['employee_grade', 'job_applicant', 'is_g2g_fees_needed', 'is_residency_fine_needed',
                'g2g_fee_amount', 'is_residency_fine_needed']
            # Custom Fields in the Job Offer
            one_fm_fields = ['salary_structure', 'job_offer_total_salary', 'provide_salary_advance', 'salary_advance_amount',
                'provide_accommodation_by_company', 'provide_transportation_by_company']

            # Start to Create Onboard Employee Document
            o_employee = frappe.new_doc('Onboard Employee')
            o_employee.job_offer = job_offer.name
            o_employee.reports_to = job_offer.reports_to
            o_employee.date_of_joining = job_offer.estimated_date_of_joining
            for d in fields:
                o_employee.set(d, job_offer.get(d))
            for od in one_fm_fields:
                o_employee.set(od, job_offer.get('one_fm_'+od))
            if job_offer.one_fm_salary_details:
                o_employee_salary_details = o_employee.append('salary_details')
                for salary_detail in job_offer.one_fm_salary_details:
                    o_employee_salary_details.salary_component = salary_detail.salary_component
                    o_employee_salary_details.amount = salary_detail.amount

            # Get Job Applicant document linked with the Job Offer and Set details in Job Applicant to Onboard Employee document
            if job_offer.job_applicant:
                # Fields in Job Applicant
                fields = ['email_id', 'department', 'project', 'source', 'nationality_no', 'nationality_subject',
                    'date_of_naturalization']

                # Custom Fields in Job Applicant
                one_fm_fields = ['applicant_is_overseas_or_local', 'is_transferable', 'designation', 'agency', 'gender', 'religion',
                    'date_of_birth', 'erf', 'height', 'place_of_birth', 'marital_status', 'nationality', 'contact_number',
                    'secondary_contact_number', 'passport_number', 'passport_holder_of', 'passport_issued', 'passport_expire',
                    'passport_type', 'visa_type', 'civil_id', 'cid_expire', 'is_uniform_needed_for_this_job', 'shoulder_width',
                    'waist_size', 'shoe_size']

                job_applicant = frappe.get_doc('Job Applicant', job_offer.job_applicant)
                for d in fields:
                    o_employee.set(d, job_applicant.get(d))
                for od in one_fm_fields:
                    if od == 'civil_id':
                        o_employee.set(od, job_applicant.get('one_fm_cid_number'))
                    else:
                        o_employee.set(od, job_applicant.get('one_fm_'+od))

                # Set Documents attached in the Job Applicant to Onboard Employee document
                for applicant_document in job_applicant.one_fm_documents_required:
                    doc_required = o_employee.append('applicant_documents')
                    fields = ['document_required', 'attach', 'required_when', 'or_required_when', 'type_of_copy', 'or_type_of_copy', 'not_mandatory']
                    for field in fields:
                        doc_required.set(field, applicant_document.get(field))

            # Get ERF details (tools needed for work) linked with the Job Offer and set to Onboard Employee document
            if job_offer.one_fm_erf:
                tools_needed_for_work = False
                if frappe.db.exists('ERF Tool Request Item', {'parent': job_offer.one_fm_erf}):
                    tools_needed_for_work = True
                o_employee.tools_needed_for_work = tools_needed_for_work

            o_employee.save(ignore_permissions=True)

            # Create an assignment to this Onboard Employee document for the Onboarding Officer selected in the Job Offer
            args = {
                'assign_to': [job_offer.onboarding_officer],
                'doctype': o_employee.doctype,
                'name': o_employee.name,
                'description': _('Employee Onboarding'),
            }
            assign_to.add(args)

def job_offer_onload(doc, method):
    o_employee = frappe.db.get_value("Onboard Employee", {"job_offer": doc.name}, "name") or ""
    doc.set_onload("onboard_employee", o_employee)


@frappe.whitelist()
def set_mandatory_feilds_in_employee_for_Kuwaiti(doc,method):
    """
    runs: `on_update` of employee doctype record
    Args:
        doc: employee object
        method: on_update
    """
    if doc.one_fm_nationality == "Kuwaiti":
        field_list = [{'Nationality No':'nationality_no'},{'Nationality Subject':'nationality_subject'},{'Date of Naturalization':'date_of_naturalization'}]
        mandatory_fields = []
        for fields in field_list:
            for field in fields:
                if not doc.get(fields[field]):
                    mandatory_fields.append(field)

        if len(mandatory_fields) > 0:
            message = 'Mandatory fields required in PIFSS 103 form<br><br><ul>'
            for mandatory_field in mandatory_fields:
                message += '<li>' + mandatory_field +'</li>'
            message += '</ul>'
            frappe.throw(message)

@frappe.whitelist()
def set_employee_name(doc,method):
    """
    runs: `validate` of employee record
    doc: employee object
    method: validate
    This method for getting the arabic full name and fetching children details from job applicant to employee record
    """
    doc.employee_name_in_arabic = ' '.join(filter(lambda x: x, [doc.one_fm_first_name_in_arabic, doc.one_fm_second_name_in_arabic,doc.one_fm_third_name_in_arabic,doc.one_fm_forth_name_in_arabic,doc.one_fm_last_name_in_arabic]))

    if doc.job_applicant:
        applicant = frappe.get_doc('Job Applicant',doc.job_applicant) # Fetching the children table from job applicant to Employee doctype
        if applicant.one_fm_number_of_kids > 0:
            for child in applicant.one_fm_kids_details:
                children = doc.append('children_details',{})
                children.child_name = child.child_name
                children.child_name_in_arabic = child.child_name_in_arabic
                children.age = child.age
                children.work_status = child.work_status
                children.married = child.married
                children.health_status = child.health_status
            frappe.db.commit()

@frappe.whitelist()# old wp was rejected
def create_new_work_permit(work_permit):
    """
    This Method If Work Permit got rejected and it is called from wp.js file using `set_restart_application`
    """
    doc = frappe.get_doc('Work Permit',work_permit)
    wp = frappe.new_doc('Work Permit')
    wp.employee = doc.employee
    wp.work_permit_type = doc.work_permit_type
    wp.date_of_application = doc.date_of_application
    wp.insert()
    wp.workflow_state = 'Draft'
    wp.save(ignore_permissions=True)
    wp.workflow_state = 'Apply Online by PRO'
    if doc.work_permit_type == "Local Transfer":
        wp.transfer_paper = doc.transfer_paper
    if doc.work_permit_type == "Renewal Non Kuwaiti" or doc.work_permit_type == "Renewal Kuwaiti":
        wp.preparation = doc.preparation
    wp.save(ignore_permissions=True)
    return wp

def update_leave_policy_assignments_expires_today():
    '''
        Method to create Leave Policy Assignment when existing one expires today
    '''
    # Get Active Leave Policy Assignment List thats ends today
    leave_policy_assignments = frappe.db.get_list('Leave Policy Assignment', {'effective_to': getdate(today())})
    for policy_assignment in leave_policy_assignments:
        doc = frappe.get_doc('Leave Policy Assignment', policy_assignment.name)
        # Check if the employee status not Left
        if frappe.db.get_value('Employee', doc.employee, 'status') not in ['Left']:
            leave_policy_assignment = frappe.new_doc('Leave Policy Assignment')
            leave_policy_assignment.employee = doc.employee
            leave_policy_assignment.effective_from = add_days(getdate(doc.effective_to), 1)
            leave_policy_assignment.effective_to = add_years(getdate(leave_policy_assignment.effective_from), 1)
            leave_policy_assignment.leave_policy = doc.leave_policy
            leave_policy_assignment.carry_forward = doc.carry_forward
            leave_policy_assignment.leaves_allocated = True
            leave_policy_assignment.save(ignore_permissions=True)
            leave_policy_assignment.submit()

def update_onboarding_doc_workflow_sate(doc):
    onboard_employee_id = False
    if doc.doctype == 'Employee':
        onboard_employee_id = frappe.db.exists('Onboard Employee', {'employee': doc.name, 'docstatus': 1})
    elif frappe.get_meta(doc.doctype).has_field("onboard_employee") and doc.onboard_employee:
        onboard_employee_id = doc.onboard_employee
    if onboard_employee_id:
        onboard_employee = frappe.get_doc('Onboard Employee', onboard_employee_id)
        if doc.doctype == 'Work Contract':
            onboard_employee.workflow_state = 'Work Contract'
        if doc.doctype == 'Electronic Signature Declaration':
            onboard_employee.workflow_state = 'Declaration of Electronic Signature'
        if doc.doctype == 'Duty Commencement' and onboard_employee.workflow_state == 'Declaration of Electronic Signature':
            onboard_employee.workflow_state = 'Duty Commencement'
        if doc.doctype == 'Employee' and onboard_employee.workflow_state == 'Bank Account' and doc.enrolled:
            onboard_employee.workflow_state = 'Mobile App Enrolment'
        onboard_employee.save(ignore_permissions=True)

@frappe.whitelist()
def get_interview_question_set(interview_round):
	return frappe.get_all('Interview Questions', filters ={'parent': interview_round}, fields=['questions', 'answer', 'weight'])

@frappe.whitelist()
def get_interview_skill_and_question_set(interview_round):
    question = frappe.get_all('Interview Questions', filters ={'parent': interview_round}, fields=['questions', 'answer', 'weight'])
    skill = frappe.get_all('Expected Skill Set', filters ={'parent': interview_round}, fields=['skill'])
    return question, skill

@frappe.whitelist()
def create_interview_feedback(data, interview_name, interviewer, job_applicant):
    import json

    from six import string_types

    if isinstance(data, string_types):
        data = frappe._dict(json.loads(data))

    if frappe.session.user != interviewer:
        frappe.throw(_('Only Interviewer Are allowed to submit Interview Feedback'))

    interview_feedback = frappe.new_doc('Interview Feedback')
    interview_feedback.interview = interview_name
    interview_feedback.interviewer = interviewer
    interview_feedback.job_applicant = job_applicant

    for d in data.skill_set:
        d = frappe._dict(d)
        interview_feedback.append('skill_assessment', {'skill': d.skill, 'rating': d.rating})

    for dq in data.questions:
        dq = frappe._dict(dq)
        interview_feedback.append('interview_question_assessment', {'questions': dq.questions, 'answer': dq.answer,
            'weight': dq.weight, 'applicant_answer': dq.applicant_answer, 'score': dq.score})

    interview_feedback.feedback = data.feedback
    interview_feedback.result = data.result

    interview_feedback.save()
    interview_feedback.submit()

    frappe.msgprint(_('Interview Feedback {0} submitted successfully').format(
    get_link_to_form('Interview Feedback', interview_feedback.name)))

def calculate_interview_feedback_average_rating(doc, method):
    total_skill_rating = doc.average_rating if doc.average_rating else 0
    total_score = 0
    total_questions = 0
    for d in doc.interview_question_assessment:
        if d.weight > 0 and d.score:
            total_score += get_score_out_of_five(d.score, d.weight)
            total_questions += 1

    average_score = flt(total_score / total_questions if total_questions else 0)
    if total_score > 0:
        if total_skill_rating > 0:
            doc.average_rating = flt((total_skill_rating + average_score) / 2)
        else:
            doc.average_rating = flt(average_score)

def get_score_out_of_five(score, weight):
    return (score * 5) / weight

def set_job_opening_erf_missing_values(doc, method):
    if doc.one_fm_erf:
        erf = frappe.get_doc('ERF', doc.one_fm_erf)
        doc.designation = erf.designation
        doc.department = erf.department
        employee = frappe.db.exists("Employee", {"user_id": erf.owner})
        doc.one_fm_hiring_manager = employee if employee else ''
        doc.one_fm_no_of_positions_by_erf = erf.number_of_candidates_required
        doc.one_fm_job_opening_created = today()
        doc.one_fm_minimum_experience_required = erf.minimum_experience_required
        doc.one_fm_performance_profile = erf.performance_profile
        if not doc.description:
            description = set_description_by_performance_profile(doc, erf)
            if description:
                doc.description = description
        if not doc.one_fm_designation_skill:
            set_erf_skills_in_job_opening(doc, erf)
        if not doc.one_fm_languages:
            set_erf_language_in_job_opening(doc, erf)
