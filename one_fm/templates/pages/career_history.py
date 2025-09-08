from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, getdate, today
from one_fm.one_fm.doctype.magic_link.magic_link import authorize_magic_link, send_magic_link
from one_fm.utils import set_expire_magic_link

def get_context(context):
    context.title = _("Career History")

    # Authorize Magic Link
    magic_link = authorize_magic_link(frappe.form_dict.magic_link, 'Job Applicant', 'Career History')
    if magic_link:
        # Find Job Applicant from the magic link
        context.job_applicant = frappe.get_doc('Job Applicant', frappe.db.get_value('Magic Link', magic_link, 'reference_docname'))

    # Get Country List to the context to show in the portal
    context.country_list = frappe.get_all('Country', fields=['name'])
    context.employment_type_list = frappe.db.get_all("Employment Type", pluck="name")





@frappe.whitelist(allow_guest=True)
def create_recruitment_documents(job_applicant, career_history_details, best_references, interest_reason,rank_and_factors):
    '''
        Method to create Recruitment Documents
        Best References
        Career History
        args:
            job_applicant: Job Applicant ID
            career_history_details: Career History details as json
            best_references: Best References details as json
    '''
    create_career_history_from_portal(job_applicant, career_history_details, interest_reason,rank_and_factors)
    create_best_references_from_portal(job_applicant, best_references)


def create_best_references_from_portal(job_applicant, best_references):
    '''
        Method to create Best References from Portal
        args:
            job_applicant: str
                The ID of the Job Applicant
            best_references: str 
                JSON string containing reference details with fields:
                - best_boss_name: Name of best boss reference
                - best_boss_email: Email of best boss
                - best_boss_phone: Phone number of best boss
                - why_best_boss: Reason for being best boss
                - best_colleague_name: Name of best colleague reference  
                - best_colleague_email: Email of best colleague
                - best_colleague_phone: Phone number of best colleague
                - why_best_colleague: Reason for being best colleague
    '''
    # Create Best References
    best_references_details = json.loads(best_references)
    
    reference_types = {
        'Best Boss': {
            'name_field': 'best_boss_name',
            'email_field': 'best_boss_email',
            'phone_field': 'best_boss_phone',
            'why_field': 'why_best_boss'
        },
        'Best Colleague': {
            'name_field': 'best_colleague_name',
            'email_field': 'best_colleague_email',
            'phone_field': 'best_colleague_phone',
            'why_field': 'why_best_colleague'
        }
    }
    
    for reference in best_references_details:
        for ref_type, fields in reference_types.items():
            try:
                # Only create document if the name field exists
                if reference.get(fields['name_field']):
                    ref_doc = frappe.new_doc('Best Reference')
                    ref_doc.job_applicant = job_applicant
                    ref_doc.reference = ref_type
                    ref_doc.name_of_person = reference.get(fields['name_field'])
                    ref_doc.email = reference.get(fields['email_field'])
                    ref_doc.contact_number = reference.get(fields['phone_field'])
                    ref_doc.why_he = reference.get(fields['why_field'])
                    ref_doc.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(
                    message=f"Error creating {ref_type} reference: {str(e)}", 
                    title=f"Error in creating {ref_type} Reference"
                )

@frappe.whitelist(allow_guest=True)
def create_career_history_from_portal(job_applicant, career_history_details, interest_reason,rank_and_factors):
    '''
        Method to create Career History from Portal
        args:
            job_applicant: Job Applicant ID
            career_history_details: Career History details as json
        Return Boolean
    '''
    # Create Career History
    if isinstance(rank_and_factors, str):
        rank_and_factors = json.loads(rank_and_factors)
    career_history = frappe.new_doc('Career History')
    career_history.job_applicant = job_applicant
    career_history.about_the_opportunity = interest_reason
    career_history.rank_and_factors = [] 
    for item in rank_and_factors:
        # Only set valid links for factors and description
        factor_name = None
        description_name = None
        if item.get("factor"):
            factor_name = frappe.db.get_value("Career Move Factors", {"factors": item.get("factor")}, "name")
        if item.get("description"):
            description_name = frappe.db.get_value("Career Move Factors", {"description": item.get("description")}, "name")
        # Only append if both are valid (or adjust as needed)
        if factor_name and description_name:
            career_history.append("rank_and_factors", {
                "rank": item.get("rank"),
                "factors": factor_name,
                "description": description_name
            })
    
    career_histories = json.loads(career_history_details)

    factors_expected_in_new_job = career_histories[-1] if career_histories else {}
    career_history.what_are_the_factors_you_are_looking_for_in_a_new_job = factors_expected_in_new_job.get("factors_in_new_job")

    for history in career_histories:
        career_history_fields = ['company_name', 'country_of_employment', 'start_date', 'responsibility_one',
           'job_title', "employment_type", 'monthly_salary_in_kwd', 'first_contact_name',
            'first_contact_email', 'first_contact_phone', 'first_contact_designation', 'second_contact_name',
            'second_contact_email', 'second_contact_phone', 'second_contact_designation']

        company = career_history.append('career_history_company')
        for field in career_history_fields:
            company.set(field, history.get(field))
        
        promotions = [p for p in history.get('promotions', []) if p.get('start_date')]
        if promotions and promotions[0].get("start_date"):
            company.end_date = getdate(promotions[0].get("start_date"))

        last_job_title = history.get('job_title')
        last_employment_type = history.get("employment_type")
        last_salary = history.get('monthly_salary_in_kwd')
        last_job_responsibility = history.get("responsibility_one")

        for idx, promotion in enumerate(promotions):
            company = career_history.append('career_history_company')
            company.company_name = history.get('company_name')
            company.job_title = last_job_title

            company.employment_type = last_employment_type
            company.responsibility_one = last_job_responsibility
            
            if promotion.get('job_title'):
                company.job_title = promotion.get('job_title')
                last_job_title = promotion.get('job_title')
            company.monthly_salary_in_kwd = last_salary
            if promotion.get('monthly_salary_in_kwd'):
                company.monthly_salary_in_kwd = promotion.get('monthly_salary_in_kwd')
                last_salary = promotion.get('monthly_salary_in_kwd')
            company.start_date = getdate(promotion.get('start_date'))
            if idx < len(promotions) - 1:
                next_start_date = promotions[idx + 1].get('start_date')
                if next_start_date:
                    company.end_date = getdate(next_start_date)
        if history.get('left_the_company'):
            company.end_date = history.get('left_the_company')
        if history.get('reason_for_leaving_job'):
            company.end_date = today()
            company.why_do_you_plan_to_leave_the_job = history.get('reason_for_leaving_job')

    career_history.save(ignore_permissions=True)
    set_expire_magic_link('Job Applicant', job_applicant, 'Career History')
    return True

@frappe.whitelist()
def send_career_history_magic_link(job_applicant, applicant_name, designation):
    '''
        Method used to send the magic Link for Career History to the Job Applicant
        args:
            job_applicant: ID of the Job Applicant
            applicant_name: Name of the applicant
            designation: Designation applied
    '''
    applicant_email = frappe.db.get_value('Job Applicant', job_applicant, 'one_fm_email_id')
    # Check applicant have an email id or not
    if applicant_email:
        # Email Magic Link to the Applicant
        subject = "Fill your Career History Sheet"
        url_prefix = "/career_history?magic_link="
        msg = "<b>Fill your Career History Sheet by visiting the magic link below</b>\
            <br/>Applicant ID: {0}<br/>Applicant Name: {1}<br/>Designation: {2}</br>".format(job_applicant, applicant_name, designation)
        send_magic_link('Job Applicant', job_applicant, 'Career History', [applicant_email], url_prefix, msg, subject)
    else:
        frappe.throw(_("No Email ID found for the Job Applicant"))
