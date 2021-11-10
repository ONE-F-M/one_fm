# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import today, add_days, get_url, time_diff_in_hours
from frappe.integrations.offsite_backup_utils import get_latest_backup_file, send_email, validate_file_size, get_chunk_site
from one_fm.api.notification import create_notification_log
from frappe.utils.user import get_users_with_role
from erpnext.hr.utils import get_holidays_for_employee

@frappe.whitelist()
def employee_grade_validate(doc, method):
    if doc.default_salary_structure:
        exists_in_list = False
        if doc.salary_structures:
            for salary_structure in doc.salary_structures:
                if salary_structure.salary_structure == doc.default_salary_structure:
                    exists_in_list = True
        if not exists_in_list:
            salary_structures = doc.append('salary_structures')
            salary_structures.salary_structure = doc.default_salary_structure

@frappe.whitelist()
def get_salary_structure_list(doctype, txt, searchfield, start, page_len, filters):
    if filters.get('employee_grade'):
        query = """
            select
                ss.salary_structure
            from
                `tabEmployee Grade` eg, `tabEmployee Grade Salary Structure` ss
            where
                ss.parent=eg.name and eg.name=%(employee_grade)s and ss.salary_structure like %(txt)s
        """
        return frappe.db.sql(query,
            {
                'employee_grade': filters.get("employee_grade"),
                'start': start,
                'page_len': page_len,
                'txt': "%%%s%%" % txt
            }
        )
    else:
        return frappe.db.sql("""select name from `tabSalary Structure` where name like %(txt)s""",
            {
                'start': start,
                'page_len': page_len,
                'txt': "%%%s%%" % txt
            }
        )

@frappe.whitelist()
def send_notification_to_grd_or_recruiter(doc, method):
    if doc.one_fm_nationality != "Kuwaiti":
        if doc.one_fm_is_transferable == 'Yes' and doc.one_fm_cid_number and doc.one_fm_passport_number:
            notify_grd_to_check_applicant_documents(doc)

        if doc.one_fm_has_issue and doc.one_fm_notify_recruiter == 0:
            notify_recruiter_after_checking(doc)

def notify_grd_to_check_applicant_documents(doc):
    """
    This method is notifying operator with applicant's cid and passport to check on PAM,
    This method runs on update and it checkes notification log list.
    """
    if not doc.one_fm_grd_operator:
        doc.one_fm_grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_transfer")

    dt = frappe.get_doc('Job Applicant',doc.name)
    if dt:
        email = [doc.one_fm_grd_operator]
        page_link = get_url("/desk#List/Job Applicant/" + dt.name)
        message = "<p>Check If Transferable.<br>Civil id:{0} - Passport Number:{1}<a href='{2}'></a>.</p>".format(dt.one_fm_cid_number,dt.one_fm_passport_number,page_link)
        subject = 'Check If Transferable.<br>Civil id:{0} - Passport Number:{1}'.format(dt.one_fm_cid_number,dt.one_fm_passport_number)
        # send_email(dt, email, message, subject)

        if not frappe.db.exists("Notification Log",{'subject':subject,'document_type':"Job Applicant"}):
        #check if the notification have been sent before.
            create_notification_log(subject, message, email, dt)

# def deleteNotification():
#     docs = frappe.db.get_list('Notification Log')
#     for doc in docs:
#         frappe.delete_doc("Notification Log", doc.name, ignore_permissions=True)
#         print("Done")

def notify_recruiter_after_checking(doc):
    """
    This method is notifying all recruiters with applicant status once,
    and changing document status into Checked By GRD.
    """

    users = get_users_with_role('Recruiter')
    seniour_users = get_users_with_role('Senior Recruiter')
    users.extend(seniour_users)
    if users and len(users)>0:
        dt = frappe.get_doc('Job Applicant',doc.name)
        if dt:
            if dt.one_fm_has_issue == "Yes" and dt.one_fm_notify_recruiter == 0:
                email = users
                page_link = get_url("/desk#List/Job Applicant/" + dt.name)
                message="<p>Transfer for {0} has issue, but you can still print the paper<a href='{1}'></a>.</p>".format(dt.applicant_name,page_link)
                subject='Transfer for {0} has issue, but you can still print the paper'.format(dt.applicant_name)
                create_notification_log(subject,message,email,dt)#remove [email] to check if will fix hashable issue
                dt.db_set('one_fm_notify_recruiter', 1)
                dt.db_set('one_fm_applicant_status', "Checked By GRD")

            if dt.one_fm_has_issue == "No" and dt.one_fm_notify_recruiter == 0:
                email = users
                page_link = get_url("/desk#List/Job Applicant/" + dt.name)
                message="<p>Transfer for {0} has no issue<a href='{1}'></a>.</p>".format(dt.applicant_name,page_link)
                subject='Transfer for {0} has no issues'.format(dt.applicant_name)
                create_notification_log(subject,message,email,dt)#remove [email]
                dt.db_set('one_fm_notify_recruiter', 1)
                dt.db_set('one_fm_applicant_status', "Checked By GRD")
                notify_pam_authorized_signature(doc)#Inform Authorized signature

def notify_pam_authorized_signature(doc):
    user = frappe.db.get_value('PAM Authorized Signatory Table',{'authorized_signatory_name_arabic':doc.one_fm_signatory_name},['user'])
    page_link = get_url("/desk#Form/Job Applicant/" + doc.name)
    subject = _("Attention: Your E-Signature will be used for Transfer Paper")
    message = "<p>Please note that your E-Signature will be used on Transfer Paper: <a href='{0}'></a></p>.".format(page_link)
    create_notification_log(subject, message, [user], doc)


@frappe.whitelist()
def check_mendatory_fields_for_grd_and_recruiter(doc,method):
    """
    This Method is checking the roles accessing Job Applicant document
    and setting the mendatory fields for each role based upon their selections.

    """
    roles = frappe.get_roles(frappe.session.user)
    if "GRD Operator" in roles:
        if doc.one_fm_has_issue == "No":
            validate_mendatory_fields_for_grd(doc)

        if doc.one_fm_has_issue == "Yes":
            validate_mendatory_fields_for_grd(doc) # set mendatory fields by grd even if there is issue in transfer
            if not doc.one_fm_type_of_issues:
                frappe.throw("Set The Type of Transfer issue before saving")
    if "Recruiter" or "Senior Recruiter" in roles:
        if doc.one_fm_is_transferable == "Yes" and doc.one_fm_have_a_valid_visa_in_kuwait == 1:
            validate_mendatory_fields_for_recruiter(doc)
        if doc.one_fm_is_transferable == "Yes" and doc.one_fm_have_a_valid_visa_in_kuwait == 0:
            frappe.throw("Visa and Residency Details are required First.")



def validate_mendatory_fields_for_grd(doc):
    """
        Check all the mendatory fields are set by grd
    """
    field_list = [{'Trade Name in Arabic':'one_fm_previous_company_trade_name_in_arabic'},{'Signatory Name':'one_fm_signatory_name'}]

    mandatory_fields = []
    for fields in field_list:
        for field in fields:
            if not doc.get(fields[field]):
                mandatory_fields.append(field)

    if len(mandatory_fields) > 0:
        message = 'Mandatory fields required in Job Applicant<br><br><ul>'
        for mandatory_field in mandatory_fields:
            message += '<li>' + mandatory_field +'</li>'
        message += '</ul>'
        frappe.throw(message)


def validate_mendatory_fields_for_recruiter(doc):
    """
        Check all the mendatory fields are set by Recruiter if Applicant wants to transfer
    """
    visa = frappe.get_doc('Visa Type',doc.one_fm_visa_type)
    if visa.has_previous_job:
        field_list = [{'CIVIL ID':'one_fm_cid_number'}, {'Date of Birth':'one_fm_date_of_birth'},
            {'Gender':'one_fm_gender'}, {'Religion':'one_fm_religion'},
            {'Nationality':'one_fm_nationality'}, {'Previous Designation':'one_fm_previous_designation'},
            {'Passport Number':'one_fm_passport_number'}, {'What is Your Highest Educational Qualification':'one_fm_educational_qualification'},
            {'Marital Status':'one_fm_marital_status'}, {'Previous Work Permit Salary':'one_fm_work_permit_salary'}]

    if not visa.has_previous_job:
        field_list = [{'CIVIL ID':'one_fm_cid_number'}, {'Date of Birth':'one_fm_date_of_birth'},
            {'Gender':'one_fm_gender'}, {'Religion':'one_fm_religion'},
            {'Nationality':'one_fm_nationality'},{'Passport Number':'one_fm_passport_number'},
            {'What is Your Highest Educational Qualification':'one_fm_educational_qualification'},
            {'Marital Status':'one_fm_marital_status'}]

    mandatory_fields = []
    for fields in field_list:
        for field in fields:
            if not doc.get(fields[field]):
                mandatory_fields.append(field)

    if len(mandatory_fields) > 0:
        message = 'Mandatory fields required in Job Applicant<br><br><ul>'
        for mandatory_field in mandatory_fields:
            message += '<li>' + mandatory_field +'</li>'
        message += '</ul>'
        frappe.throw(message)

@frappe.whitelist()
def get_signatory_name(parent,name):
    """
    This method fetching all Autorized Signatory based on the New PAM file selection in job applicant
    """
    names=[]
    names.append(' ')
    if parent and name:
        doc = frappe.get_doc('PAM Authorized Signatory List',{'pam_file_name':parent})
        if doc:
            for pas in doc.authorized_signatory:
                if pas.authorized_signatory_name_arabic:
                    names.append(pas.authorized_signatory_name_arabic)
        elif not doc:
            frappe.throw("PAM File Number Has No PAM Authorized Signatory List")
    return names,doc.name

@frappe.whitelist()
def get_signatory_name_erf_file(parent,name):
    """
    This method fetching all Autorized Signatory based on the PAM file selection in erf
    """

    names=[]
    names.append(' ')
    if parent and name:
        doc = frappe.get_doc('PAM Authorized Signatory List',{'pam_file_number':parent})
        if doc:
            for pas in doc.authorized_signatory:
                if pas.authorized_signatory_name_arabic:
                    names.append(pas.authorized_signatory_name_arabic)
        elif not doc:
            frappe.throw("PAM File Number Has No PAM Authorized Signatory List")
    return names,doc.name

@frappe.whitelist()
def notify_supervisor_change_file_number(name):
    job_Applicant = frappe.get_doc('Job Applicant',name)
    grd_supervisor = frappe.db.get_single_value('GRD Settings','default_grd_supervisor')
    page_link = get_url("/desk#Form/Job Applicant/" + job_Applicant.name)
    subject = _("You Are Requested to Change/Approve New PAM File Number for Applicant with Civil ID:{0} ").format(job_Applicant.one_fm_cid_number)
    message = "<p>Kindly, you are requested to Change the PAM File Number for Job Applicant: {0}  <a href='{1}'></a></p>".format(job_Applicant.name,page_link)
    create_notification_log(subject, message, [grd_supervisor], job_Applicant)

@frappe.whitelist()
def notify_supervisor_change_pam_designation(name):
    job_Applicant = frappe.get_doc('Job Applicant',name)
    grd_supervisor = frappe.db.get_single_value('GRD Settings','default_grd_supervisor')
    page_link = get_url("/desk#Form/Job Applicant/" + job_Applicant.name)
    subject = _("You Are Requested to Change/Approve New PAM Designation for Applicant with Civil ID:{0} ").format(job_Applicant.one_fm_cid_number)
    message = "<p>Kindly, you are requested to Change the PAM Designation for Job Applicant: {0}  <a href='{1}'></a></p>".format(job_Applicant.name,page_link)
    create_notification_log(subject, message, [grd_supervisor], job_Applicant)

@frappe.whitelist()
def notify_operator_with_supervisor_response(name):
    """This method will notify GRD Operator with GRD supervisor response (Accept/Reject) on the PAM Number - PAM Desigantion changes for solving internal tp issues"""
    job_Applicant = frappe.get_doc('Job Applicant',name)
    grd_operator = frappe.db.get_single_value('GRD Settings','default_grd_operator_transfer')
    if job_Applicant.accept_changes == 1 and job_Applicant.reject_changes == 0:
        page_link = get_url("/desk#Form/Job Applicant/" + job_Applicant.name)
        subject = _("Supervisor Accepted Your Changes in Job Applicant")
        message = "<p>Kindly, you are requested to mark (no internal issues) box for Job Applicant: {0} and check if candidate has external issues while transfering  <a href='{1}'></a></p>".format(job_Applicant.name,page_link)
        create_notification_log(subject, message, [grd_operator], job_Applicant)
    if job_Applicant.accept_changes == 0 and job_Applicant.reject_changes == 1:
        page_link = get_url("/desk#Form/Job Applicant/" + job_Applicant.name)
        subject = _("Supervisor Rejected Your Changes in Job Applicant and Provide Suggested Changes")
        message = "<p>Kindly, you are requested to Check Suggestions box for Job Applicant: {0} and check if candidate has external issues while transfering  <a href='{1}'></a></p>".format(job_Applicant.name,page_link)
        create_notification_log(subject, message, [grd_operator], job_Applicant)

def attendance_on_submit(doc, method):
    from one_fm.api.tasks import update_shift_details_in_attendance
    update_shift_details_in_attendance(doc, method)
    manage_attendance_on_holiday(doc, method)

def attendance_on_cancel(doc, method):
    manage_attendance_on_holiday(doc, method)

def manage_attendance_on_holiday(doc, method):
    '''
        Method used to create compensatory leave request and additional salary for holiday attendance
        on_submit or on_cancel of attendance will trigger this method
        args:
            doc is attendance object
            method is the method from the hook (like on_submit)
        if method is "on_submit", then create and submit the compensatory leave request and additional salary
        if method is "on_cancel", then cancel the compensatory leave request and additional salary, that is created for the attendance
    '''

    # Get holiday list of dicts with `holiday_date` and `description`
    holidays = get_holidays_for_employee(doc.employee, doc.attendance_date, doc.attendance_date)

    # process compensatory leave request and additional salary if attendance status not equals "Absent" or "On Leave"
    if len(holidays) > 0 and doc.status not in ["Absent", "On Leave"]:

        # create and submit additional salary and compensatory leave request on attendance submit
        if method == 'on_submit':
            remark = _("Worked on {0}".format(holidays[0].description))
            create_additional_salary_from_attendance(doc, remark)
            create_compensatory_leave_request_from_attendance(doc, remark)

        # cancel additional salary and compensatory leave request on attendance cancel
        if method == "on_cancel":
            cancel_additional_salary_from_attendance(doc)
            cancel_compensatory_leave_request_from_attendance(doc)

def create_additional_salary_from_attendance(attendance, notes=None):
    additional_salary = frappe.new_doc('Additional Salary')
    additional_salary.employee = attendance.employee
    additional_salary.payroll_date = attendance.attendance_date
    additional_salary.salary_component = "Holiday Salary" # TODO: Configure salary component for "Holiday Salary"
    additional_salary.notes = notes
    additional_salary.overwrite_salary_structure_amount = False
    additional_salary.amount = get_amount_for_additional_salary_for_holiday(attendance)
    if additional_salary.amount > 0:
        additional_salary.insert(ignore_permissions=True)
        additional_salary.submit()

def get_amount_for_additional_salary_for_holiday(attendance):
    '''
        Method used to get calculated additional salary amount for holiday attendance
        args:
            attendance is attendance object
    '''
    # Calculate hours worked from the time in and time out recorded in attendance
    hours_worked = 0
    if attendance.in_time and attendance.out_time:
        hours_worked = time_diff_in_hours(attendance.out_time, attendance.in_time)

    # Get basic salary from the employee doctype
    basic_salary = frappe.db.get_value('Employee', attendance.employee, 'one_fm_basic_salary')

    # Calculate basic hourly wage
    basic_hourly_wage = 0
    shift_hours = 8 # Default 8 hour shift
    if attendance.shift:
        shift_hours = frappe.db.get_value('Shift Type', attendance.shift, 'duration')
    if basic_salary and basic_salary > 0 and shift_hours:
        basic_hourly_wage = basic_salary / (30 * shift_hours) # Assuming 30 days month

    return hours_worked * basic_hourly_wage * 1.5 * 2

def cancel_additional_salary_from_attendance(attendance):
    exist_additional_salary = frappe.db.exists('Additional Salary', {
        'employee': attendance.employee,
        'payroll_date': attendance.attendance_date,
        'salary_component': "Holiday Salary"
    })
    if exist_additional_salary:
        frappe.get_doc('Additional Salary', exist_additional_salary).cancel()

def create_compensatory_leave_request_from_attendance(attendance, reason):
    compensatory_leave_request = frappe.new_doc('Compensatory Leave Request')
    compensatory_leave_request.employee = attendance.employee
    compensatory_leave_request.work_from_date = attendance.attendance_date
    compensatory_leave_request.work_end_date = attendance.attendance_date
    if attendance.status == "Half Day":
        compensatory_leave_request.half_day = True
        compensatory_leave_request.half_day_date = attendance.attendance_date
    compensatory_leave_request.reason = reason
    compensatory_leave_request.leave_type = "Compensatory Off" # TODO: Configure leave type for "Compensatory Leave Request"
    compensatory_leave_request.insert(ignore_permissions=True)
    compensatory_leave_request.submit()

def cancel_compensatory_leave_request_from_attendance(attendance):
    exist_compensatory_leave_request = frappe.db.exists('Compensatory Leave Request', {
        'employee': attendance.employee,
        'work_from_date': attendance.attendance_date,
        'work_end_date': attendance.attendance_date
    })
    if exist_compensatory_leave_request:
        frappe.get_doc('Compensatory Leave Request', exist_compensatory_leave_request).cancel()
