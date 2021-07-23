# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today, add_days, get_url, date_diff
from frappe import _
from one_fm.api.notification import create_notification_log
from frappe.permissions import has_permission
from frappe.utils.user import get_users_with_role
from datetime import date, timedelta
import calendar
from datetime import date
from dateutil.relativedelta import relativedelta
from frappe.utils import get_datetime, add_to_date, getdate, get_link_to_form, now_datetime, nowdate, cstr
from email import policy
from one_fm.grd.doctype.fingerprint_appointment import fingerprint_appointment
from one_fm.grd.doctype.medical_insurance import medical_insurance
from PyPDF2 import PdfFileReader

# from pdfminer.pdfparser import PDFParser, PDFDocument  
class WorkPermit(Document):
    def validate(self):
        self.set_grd_values()
        # self.check_workflow_status()
        if self.work_permit_type == "Local Transfer":
            self.check_inform_previous_company()
            if self.work_permit_approved == "Yes":
                self.recall_create_fingerprint_appointment_transfer()
                self.notify_grd_transfer_fp_record()
    def set_grd_values(self):
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")

    def check_workflow_status(self):
        if self.work_permit_status == "Draft":
            page_link = get_url("/desk#Form/Work Permit/" + self.name)
            message = "<p>Apply Online for Work Permit<a href='{0}'>{1}</a>.</p>".format(page_link, self.name)
            subject = '{0} Apply Online for Work Permit'.format(self.grd_operator)
            self.notify_grd(page_link,message,subject,"GRD Operator")

        if self.work_permit_status == "Pending by Supervisor":
            page_link = get_url("/desk#Form/Work Permit/" + self.name)
            message = "<p>Check Work Permit for Acceptance<a href='{0}'>{1}</a>.</p>".format(page_link, self.name)
            subject = 'Check Work Permit for Acceptance for {0}'.format(self.first_name)
            self.notify_grd(page_link,message,subject,"GRD Supervisor")

        if self.work_permit_status == "Pending by Operator":
            if not self.upload_work_permit and not self.attach_invoice and not self.new_work_permit_expiry_date:
                if not self.notify_to_upload:
                    page_link = get_url("/desk#Form/Work Permit/" + self.name)
                    message = "<p>Upload Required Documents for Work Permit<a href='{0}'>{1}</a>.</p>".format(page_link, self.name)
                    subject = '{0} Upload Required Documents for Work Permit'.format(self.grd_operator)
                    self.notify_grd(page_link,message,subject,"GRD Operator")
                    self.notify_to_upload = 1

    def check_inform_previous_company(self):
         # 3 days with in the applied days so 2
        if date_diff(today(),self.date_of_application) == 2 and self.approve_previous_company == "No":
            self.work_permit_status = "Rejected"
            self.save()

    def on_submit(self):
        if "Completed" in self.workflow_state and self.upload_work_permit and self.attach_invoice and self.new_work_permit_expiry_date:
            self.db_set('work_permit_status', 'Completed')
            self.clean_old_wp_record_in_employee_doctype()
            self.set_work_permit_attachment_in_employee_doctype()
        else:
            frappe.throw(_("Upload The Required Documents To Submit"))
        
    def recall_create_fingerprint_appointment_transfer(self):
        fingerprint_appointment.create_fp_record_for_transfer(frappe.get_doc('Employee',self.employee))

    def notify_grd_transfer_fp_record(self):
        fp = frappe.db.get_value("Fingerprint Appointment",{'employee':self.employee,'fingerprint_appointment_type':'Local Transfer'})
        print(fp)#printing wp name
        if fp:
            fp_record = frappe.get_doc('Fingerprint Appointment', fp)
            page_link = get_url("/desk#Form/Fingerprint Appointment/" + fp_record.name)
            subject = ("Apply for Transfer Fingerprint Appointment Online")
            message = "<p>Please Apply for Transfer Fingerprint Appointment Online for <a href='{0}'></a>.</p>".format(fp_record.employee)
            create_notification_log(subject, message, [self.grd_operator], fp_record)
            
    def validate_mandatory_fields_for_grd_operator_again(self):
        users = frappe.utils.user.get_users_with_role('GRD Operator')
        filtered_users = []
        for user in users:
            if has_permission(doctype=self.doctype, user=user):
                filtered_users.append(user)
            if filtered_users and len(filtered_users) > 0: 
                if "Pending By PAM" in self.workflow_state and not self.upload_work_permit and not self.attach_invoice:
                    frappe.throw(_("Upload Required Documents To Submit"))

    def notify_grd(self,page_link,message,subject,user):
        if user == "GRD Operator":
            send_email(self, [self.grd_operator], message, subject)
            create_notification_log(subject, message, [self.grd_operator], self)
        if user == "GRD Supervisor":
            send_email(self, [self.grd_supervisor], message, subject)
            create_notification_log(subject, message, [self.grd_supervisor], self)

    def clean_old_wp_record_in_employee_doctype(self):
        """ Clean old wp records in employee """
        to_remove = []
        employee = frappe.get_doc('Employee', self.employee)
        if employee.one_fm_employee_documents:
            for document in employee.one_fm_employee_documents:
                print(document.document_name)
                if document.document_name == "Work Permit Attachment":
                    to_remove.append(document)
            [document.delete(document) for document in to_remove]

    def set_work_permit_attachment_in_employee_doctype(self):
        today = date.today()
        employee = frappe.get_doc('Employee', self.employee)
        filters= {"document_name":['=',"Work Permit Attachment"]}
        employee_wp_document = frappe.db.get_list('Employee Document',filters, ['document_name','attach','issued_on','valid_till'])
        employee.append("one_fm_employee_documents", {
            "attach": self.upload_work_permit,
            "document_name": "Work Permit Attachment",
            "issued_on":today,
            "valid_till":self.new_work_permit_expiry_date
        })
        employee.work_permit = self.name # add the latest work permit link
        employee.work_permit_expiry_date = self.new_work_permit_expiry_date # add the latest work permit link
        employee.save()
        
    def get_required_documents(self):
        set_required_documents(self)

def set_required_documents(doc):
    if frappe.db.exists('Work Permit Required Documents Template', {'work_permit_type':doc.work_permit_type}):
        #getting the required documents template based on the wp type
        document_list_template = frappe.get_doc('Work Permit Required Documents Template', {'work_permit_type':doc.work_permit_type})
        employee = frappe.get_doc('Employee', doc.employee)#getting employee info.
        if document_list_template and document_list_template.work_permit_document:####### Don't get 
            for wpd in document_list_template.work_permit_document:
                documents_required = doc.append('documents_required')#in work permit doctype points to Work Permit Required Documents
                documents_required.required_document = wpd.required_document
                if employee.one_fm_employee_documents:# from employee dt
                    for ed in employee.one_fm_employee_documents:
                        if wpd.required_document == ed.document_name and ed.attach:#check if both documents are equal
                            documents_required.attach = ed.attach#add the attach document from (Employee Document)dt to (Work permit Required Document) attch field
            frappe.db.commit()


# will craete a list of work permit based on employee renewals
@frappe.whitelist()
def get_employee_data_for_work_permit(employee_name):
    work_permit_exist = frappe.db.exists('Work Permit', {'employee': employee_name, 'docstatus': 1})
    return work_permit_exist

# @frappe.whitelist()#allow_guest=True)
# def import_pdf_wp_file(file_url):
#     url = frappe.get_site_path() + file_url
#     pdfReader = PyPDF2.PdfFileReader(open(url,'rb'))
#     pages = pdfReader.numPages
#     pageObj = pdfReader.getPage(0)
#     return pageObj.documentInfo

# Create Work Permit Record for new Kuwaiti
def create_work_permit_new_kuwaiti(pifss_name,employee):
    pifss103_form = frappe.get_doc('PIFSS Form 103',pifss_name)
    if pifss103_form:
        employee_in_pifss103_form = frappe.get_doc('Employee',employee)
        if employee_in_pifss103_form:
            create_wp_kuwaiti(frappe.get_doc('Employee',employee_in_pifss103_form.employee),"New Kuwaiti",pifss_name)

# Create Work Permit Record for Transfer
def create_work_permit_transfer(tp_name,employee):
    tp = frappe.get_doc('Transfer Paper',tp_name)
    if tp:
        employee_in_tp = frappe.get_doc('Employee',employee)
        if employee_in_tp:
            name = create_wp_transfer(frappe.get_doc('Employee',employee_in_tp.employee),"Local Transfer",tp_name)
            return name

# Create Work Permit record once a month for renewals list  
def create_work_permit_renewal(preparation_name):
#Get employees of the choosen preparation record
    employee_in_preparation = frappe.get_doc('Preparation',preparation_name)
    if employee_in_preparation.preparation_record:
        for employee in employee_in_preparation.preparation_record:
            if employee.renewal_or_extend == 'Renewal':
                create_wp_renewal(frappe.get_doc('Employee',employee.employee),employee.renewal_or_extend,preparation_name)
      

#FOR RENEWAL
def create_wp_renewal(employee,status,name):
    if status and status == "Renewal":
        start_day = add_days(employee.residency_expiry_date, -14)
        Doctype = "Preparation"
        preparation_name = name
    # setting type of renewal work permit
        if employee.one_fm_nationality == "Kuwaiti":
            work_permit_type = "Renewal Kuwaiti"
        if employee.one_fm_nationality != "Kuwaiti":
            work_permit_type = "Renewal Non Kuwaiti"
    if employee.one_fm_work_permit:
        # Renew Work Permit: 1. Renew Kuwaiti Work Permit, 2. Renew Overseas Work Permit
        work_permit = frappe.get_doc('Work Permit', employee.one_fm_work_permit)
        new_work_permit = frappe.copy_doc(work_permit)
        new_work_permit.employee = employee.name
        new_work_permit.preparation = preparation_name
        new_work_permit.work_permit_type = work_permit_type
        new_work_permit.date_of_application = start_day
        new_work_permit.transfer_paper = None
        new_work_permit.ref_doctype = Doctype
        new_work_permit.ref_name = name
        new_work_permit.insert()  
    else:
        # Create New Work Permit: 1. New Overseas, 2. New Kuwaiti, 3. Work Transfer
        work_permit = frappe.new_doc('Work Permit')
        work_permit.employee = employee.name
        work_permit.preparation = preparation_name
        work_permit.work_permit_type = work_permit_type
        work_permit.date_of_application = start_day
        work_permit.ref_doctype = Doctype
        work_permit.ref_name = name
        work_permit.transfer_paper = None
        work_permit.save()

#FOR Transfer
def create_wp_transfer(employee,status,name):
    if status == "Local Transfer":
            start_day = today()
            Doctype = "Transfer Paper"
            work_permit_type = "Local Transfer"
            preparation_name = None
    if employee.one_fm_work_permit:
        # Renew Work Permit: 1. Renew Kuwaiti Work Permit, 2. Renew Overseas Work Permit
        work_permit = frappe.get_doc('Work Permit', employee.one_fm_work_permit)
        new_work_permit = frappe.copy_doc(work_permit)
        new_work_permit.employee = employee.name
        new_work_permit.preparation = None
        new_work_permit.work_permit_type = work_permit_type
        new_work_permit.date_of_application = start_day
        new_work_permit.ref_doctype = Doctype
        new_work_permit.ref_name = name
        new_work_permit.transfer_paper = name
        new_work_permit.insert()  
        return new_work_permit.name          
    else:
        # Create New Work Permit: 1. New Overseas, 2. New Kuwaiti, 3. Work Transfer
        work_permit = frappe.new_doc('Work Permit')
        work_permit.employee = employee.name
        work_permit.preparation = None
        work_permit.work_permit_type = work_permit_type
        work_permit.date_of_application = start_day
        work_permit.ref_doctype = Doctype
        work_permit.ref_name = name
        work_permit.transfer_paper = name
        work_permit.save()
        return work_permit.name  
    

#For New Kuwaiti New Kuwaiti
def create_wp_kuwaiti(employee,status,name):
    if status == "New Kuwaiti":
        start_day = today()
        Doctype = "PIFSS Form 103"
        work_permit_type = "New Kuwaiti"
    if employee.one_fm_work_permit:
        # Renew Work Permit: 1. Renew Kuwaiti Work Permit, 2. Renew Overseas Work Permit
        work_permit = frappe.get_doc('Work Permit', employee.one_fm_work_permit)
        new_work_permit = frappe.copy_doc(work_permit)
        new_work_permit.employee = employee.name
        new_work_permit.preparation = None
        new_work_permit.work_permit_type = work_permit_type
        new_work_permit.date_of_application = start_day
        new_work_permit.ref_doctype = Doctype
        new_work_permit.ref_name = name
        new_work_permit.transfer_paper = None
        new_work_permit.insert()         
    else:
        # Create New Work Permit: 1. New Overseas, 2. New Kuwaiti, 3. Work Transfer
        work_permit = frappe.new_doc('Work Permit')
        work_permit.employee = employee.name
        work_permit.preparation = None
        work_permit.work_permit_type = work_permit_type
        work_permit.date_of_application = start_day
        work_permit.ref_doctype = Doctype
        work_permit.ref_name = name
        work_permit.transfer_paper = None
        work_permit.save()

#System check at 4pm if grd operator submit the application online (cron)
def system_checks_grd_operator_submit_application_online():
    """ Notify GRD Operator to apply for wp renewal System checks at 4pm """
    work_permit_notify_first_grd_operator() # 9am

# Notify GRD Operator at 9:00 am (cron)
def work_permit_notify_first_grd_operator():
    work_permit_notify_grd_operator('yellow')

# Notify GRD Operator at 9:30 am (cron)
def work_permit_notify_again_grd_operator():
    work_permit_notify_grd_operator('red')

# Notify GRD Supervisor at  4pm  to approve and check online submit (cron)
def work_permit_notify_grd_supervisor_to_approve():
    """ Notify GRD supervisor to complete wp System checks at 4pm """
    work_permit_list = frappe.db.get_list('Work Permit',{'workflow_state':'Pending By Supervisor'},['name','grd_supervisor'])
    if len(work_permit_list) > 0:
        print(work_permit_list)
        email_notification_to_grd_user('grd_supervisor', work_permit_list, 'yellow', 'Check')
    

#System check at 4pm if grd operator accept the application online (cron)
def system_checks_grd_operator_complete_application():
    """ Notify GRD Operator to complete wp System checks at 4pm """
    today = date.today()
    work_permit_list = frappe.db.get_list('Work Permit',{'workflow_state':'Pending By PAM','date_of_application':today},['name', 'grd_operator'])
    if len(work_permit_list) > 0:
        email_notification_to_grd_user('grd_operator', work_permit_list, 'red', 'Complete')

# Notify GRD Operator at 9 am (check approval of wp) (cron)
def work_permit_notify_grd_operator_check_approval(): #work_permit_notify_grd_supervisor_check_approval
    work_permit_notify_grd_operator_to_check_and_complete('yellow') 

def work_permit_notify_grd_operator_to_check_and_complete(reminder_indicator):
    """ Notify GRD Operator to complete wp System checks at 4pm """
    # Get work permit list
    filters = {'work_permit_approved': 'No','work_permit_status': 'Pending By Supervisor'}
    work_permit_list = frappe.db.get_list('Work Permit', filters, ['name', 'grd_operator'])
    email_notification_to_grd_user('grd_operator', work_permit_list, reminder_indicator, 'Check Approval status of WP and Complete')

def work_permit_notify_grd_operator(reminder_indicator):
    """ Notify GRD Operator first and second time to remind applying online for WP """
    # Get work permit list
    today = date.today()
    filters = {'docstatus': 0,                                                                
    'reminded_grd_operator': 0, 'reminded_grd_operator_again':0,'date_of_application': ['=',today]}
    if reminder_indicator == 'red':
        filters['reminded_grd_operator'] = 1
        filters['reminded_grd_operator_again'] = 0
                                                            
    work_permit_list = frappe.db.get_list('Work Permit', filters, ['name', 'grd_operator', 'grd_supervisor'])
    cc = [work_permit_list[0].grd_supervisor] if reminder_indicator == 'red' else []
    email_notification_to_grd_user('grd_operator', work_permit_list, reminder_indicator, 'Apply On ASHAL', cc)

    # Update reminded grd operator to 1
    if reminder_indicator == 'red':
        field = 'reminded_grd_operator_again'
    elif reminder_indicator == 'yellow':
        field = 'reminded_grd_operator'

    frappe.db.set_value("Work Permit", filters, field, 1)

def work_permit_notify_grd_supervisor(reminder_indicator): # at 9am checks grd supervisor approval on online application
    """ Notify GRD Supervisor to remind accepting WP on ASHAL application """
    # Get work permit list
    if reminder_indicator == 'yellow':
        filters = {'docstatus': 0, 
        'date_of_application':['>=',today()],
        'grd_supervisor_check_and_approval_wp_online':['=','No']}

    work_permit_list = frappe.db.get_list('Work Permit', filters, ['name', 'grd_supervisor'])
    email_notification_to_grd_user('grd_supervisor', work_permit_list, reminder_indicator, 'Check and Accept')

def email_notification_to_grd_user(grd_user, work_permit_list, reminder_indicator, action, cc=[]):
    recipients = {}

    for work_permit in work_permit_list:
        page_link = get_url("/desk#Form/Work Permit/"+work_permit.name)
        message = "<a href='{0}'>{1}</a>".format(page_link, work_permit.name)
        if work_permit[grd_user] in recipients:
            recipients[work_permit[grd_user]].append(message)#add the message in the empty list
        else:
            recipients[work_permit[grd_user]]=[message]

    if recipients:
        for recipient in recipients:
            subject = 'Work Permit {0}'.format(work_permit.name)#added
            message = "<p>Please {0} Work Permit listed below</p><ol>".format(action)
            for msg in recipients[recipient]:
                message += "<li>"+msg+"</li>"
            message += "<ol>"
            frappe.sendmail(
                recipients=[recipient],
                cc=cc,
                subject=_('{0} Work Permit'.format(action)),
                message=message,
                header=['Work Permit Reminder', reminder_indicator],
            )
            to_do_to_grd_users(_('{0} Work Permit'.format(action)), message, recipient)

def to_do_to_grd_users(subject, description, user):
    frappe.get_doc({
        "doctype": "ToDo",
        "subject": subject,
        "description": description,
        "owner": user,
        "date": today()
    }).insert(ignore_permissions=True)

def send_email(doc, recipients, message, subject):
	frappe.sendmail(
		recipients= recipients,
		subject=subject,
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name
	)
def create_notification_log(subject, message, for_users, reference_doc):
    for user in for_users:
        doc = frappe.new_doc('Notification Log')
        doc.subject = subject
        doc.email_content = message
        doc.for_user = user
        doc.document_type = reference_doc.doctype
        doc.document_name = reference_doc.name
        doc.from_user = reference_doc.modified_by
