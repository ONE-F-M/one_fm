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
from frappe.core.doctype.communication.email import make
# from PyPDF2 import PdfFileReader

# from pdfminer.pdfparser import PDFParser, PDFDocument  
class WorkPermit(Document):
    def on_update(self):
        self.update_work_permit_details_in_tp() # <In progress>
        self.check_required_document_for_workflow()

    def validate(self):
        self.set_grd_values()
        
    def set_grd_values(self):
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")
        if not self.grd_operator_transfer:
            self.grd_operator_transfer = frappe.db.get_single_value("GRD Settings", "default_grd_operator_transfer")

    def check_required_document_for_workflow(self):
        if self.workflow_state == "Apply Online by PRO":
            self.reload()

        if self.workflow_state == "Pending By Supervisor" and self.work_permit_type == "Cancellation":
            field_list = [{'PAM Reference Number':'reference_number_on_pam'}]
            message_detail = '<b style="color:red; text-align:center;">First, You Need to Apply for Work Permit Cancellation through <a href="{0}" target="_blank">PAM Website</a></b>'.format(self.pam_website)
            self.set_mendatory_fields(field_list,message_detail)

        if self.workflow_state == "Pending By Supervisor":
            if self.work_permit_type == "New Kuwaiti" or self.work_permit_type == "Local Transfer" or self.work_permit_type =="Renewal Kuwaiti" or self.work_permit_type =="Renewal Non Kuwaiti":
                field_list = [{'PAM Reference Number':'reference_number_on_pam_registration'}]
                message_detail = '<b style="color:red; text-align:center;">First, You Need to Apply for Work Permit Registration through <a href="{0}" target="_blank">PAM Website</a></b>'.format(self.pam_website)
                self.set_mendatory_fields(field_list,message_detail)
            self.reload()

        if self.workflow_state == "Pending By PAM":
            if self.work_permit_type == "Renewal Kuwaiti" or self.work_permit_type == "Renewal Non Kuwaiti" or self.work_permit_type == "New Kuwaiti":
                field_list = [{'Upload Payment Invoice':'attach_invoice'}]
                message_detail = '<b style="color:red; text-align:center;">First, You Need to Pay through <a href="{0}" target="_blank">PAM Website</a></b>'.format(self.pam_website)
                self.set_mendatory_fields(field_list,message_detail)
            self.reload()

            if self.work_permit_type == "Local Transfer":
                field_list = [{'Previous Company Status':'previous_company_status'}]
                message_detail = '<b style="color:red; text-align:center;">First, You Need to Inform Previous Company.<br>Second, Check Previous Company Response on <a href="{0}" target="_blank">PAM Website</a></b>'.format(self.pam_website)
                self.set_mendatory_fields(field_list,message_detail)
            self.reload()

        if self.workflow_state == "Pending By Operator":
            if self.work_permit_type == "Local Transfer":
                field_list = [{'Attach Payment Invoice':'attach_payment_invoice'}]
                message_detail = '<b style="color:red; text-align:center;">First, You Need to Pay through <a href="{0}" target="_blank">PAM Website</a></b>'.format(self.pam_website)
                self.set_mendatory_fields(field_list,message_detail)
            self.reload()


        if self.workflow_state == "Completed":
            if self.work_permit_type == "Renewal Non Kuwaiti" or self.work_permit_type == "Renewal Kuwaiti":
                field_list = [{'Upload Work Permit':'upload_work_permit'},{'Updated Work Permit Expiry Date':'new_work_permit_expiry_date'}]
                message_detail = '<b style="color:red; text-align:center;">First, You Need to Attch Work Permit taken from <a href="{0}" target="_blank">PAM Website</a></b>'.format(self.pam_website)
                self.set_mendatory_fields(field_list,message_detail)

            if self.work_permit_type == "Cancellation":
                field_list = [{'Work Permit Cancellation ':'work_permit_cancellation'}]
                message_detail = '<b style="color:red; text-align:center;">First, You Need to Attach the Work Permit Cancellation taken from <a href="{0}" target="_blank">PAM Website</a></b>'.format(self.pam_website)
                self.set_mendatory_fields(field_list,message_detail)

            if self.work_permit_type == "New Kuwaiti":
                field_list = [{'Work Permit Registration ':'work_permit_registration'}]
                message_detail = '<b style="color:red; text-align:center;">First, You Need to Attach the Work Permit Registration taken from <a href="{0}" target="_blank">PAM Website</a></b>'.format(self.pam_website)
                self.set_mendatory_fields(field_list,message_detail)
            
            if self.work_permit_type == "Local Transfer":
                field_list = [{'Work Permit Expiry Date':'work_permit_expiry_date'},{'Attach Work Permit ':'attach_work_permit'}]
                message_detail = '<b style="color:red; text-align:center;">First, You Need to Attach the Work Permit Registration taken from <a href="{0}" target="_blank">PAM Website</a></b>'.format(self.pam_website)
                self.set_mendatory_fields(field_list,message_detail)
        self.reload()

        if self.workflow_state == "Rejected":
            if self.work_permit_type == "Local Transfer":
                field_list = [{'Reason Of Rejection':'reason_of_rejection'},{'Details of Rejection':'details_of_rejection'}]
                message_detail = '<b style="color:red; text-align:center;">First, You Need to set the reason of Rejection Mentioned in <a href="{0}" target="_blank">PAM Website</a></b>'.format(self.pam_website)
                self.set_mendatory_fields(field_list,message_detail)
                self.update_work_permit_details_in_tp()# update the rejected record in the transfer paper child table
            self.reload()

    
    def set_mendatory_fields(self,field_list,message_detail=None):
        mandatory_fields = []
        for fields in field_list:
            for field in fields:
                if not self.get(fields[field]):
                    mandatory_fields.append(field)
        
        if len(mandatory_fields) > 0:
            if message_detail:
                message = message_detail
                message += '<br>Mandatory fields required in Work Permit form<br><br><ul>'
            else:
                message= 'Mandatory fields required in Work Permit form<br><br><ul>'
            for mandatory_field in mandatory_fields:
                message += '<li>' + mandatory_field +'</li>'
            message += '</ul>'
            frappe.throw(message)

    def update_work_permit_details_in_tp(self):
        """This method add all work permit trails records under same transfer paper into child table in Transfer Paper, 
        it checks if the work permit referance is already exist, it update the work permit status. 
        if not exist and it reaches end of the records, it add new row in the table"""

        if self.work_permit_type == "Local Transfer" and self.transfer_paper:
            tp = frappe.get_doc('Transfer Paper',self.transfer_paper)
            if tp:
                if tp.work_permit_records != []:
                    for wp_index, wp in enumerate(tp.work_permit_records):
                        if wp.work_permit_reference  == self.name and self.work_permit_status != "Completed":
                            wp.update({
                                "status": self.work_permit_status,
                                "reason_of_rejection": self.reason_of_rejection
                                })
                            wp.save()
                        if wp.work_permit_reference  != self.name and wp_index == len(tp.work_permit_records)-1:
                            tp.append("work_permit_records", {
                            "work_permit_reference": self.name,
                            "status": self.work_permit_status,
                            "reason_of_rejection": self.reason_of_rejection
                            })
                        if wp.work_permit_reference  != self.name and wp_index != len(tp.work_permit_records)-1:
                            continue
                elif tp.work_permit_records == []:
                    tp.append("work_permit_records", {
                    "work_permit_reference": self.name,
                    "status": self.work_permit_status,
                    "reason_of_rejection": self.reason_of_rejection
                    })
            tp.save()
            tp.reload()

    def on_submit(self):
        if self.work_permit_type != "Cancellation" and self.work_permit_type != "New Kuwaiti" and self.work_permit_type != "Local Transfer" and self.workflow_state != "Rejected":
            if "Completed" in self.workflow_state and self.upload_work_permit and self.attach_invoice and self.new_work_permit_expiry_date:
                self.db_set('work_permit_status', 'Completed')
                # self.clean_old_wp_record_in_employee_doctype()
                self.set_work_permit_attachment_in_employee_doctype(self.upload_work_permit,self.new_work_permit_expiry_date)
            else:
                frappe.throw(_("Upload The Required Documents To Submit"))

        if self.work_permit_type == "Cancellation":
            self.db_set('work_permit_status', 'Completed')

        if self.workflow_state == "Completed":
            if self.work_permit_type == "Local Transfer":
                self.db_set('work_permit_status', 'Completed')
                self.update_wp_child_table_in_transfer_paper()
                self.recall_create_medical_insurance_transfer()
                self.set_work_permit_attachment_in_employee_doctype(self.attach_work_permit,self.work_permit_expiry_date)
                self.notify_grd_transfer_mi_record()

    def update_wp_child_table_in_transfer_paper(self):
        """This method to update work permit status if completed in transfer paper, close the transfer paper, and submit it """
        tp = frappe.get_doc('Transfer Paper',self.transfer_paper)
        if tp:
            for wp in tp.work_permit_records:
                if wp.work_permit_reference  == self.name and self.work_permit_status == "Completed":
                    wp.update({
                        "status": self.work_permit_status,
                        "reason_of_rejection": self.reason_of_rejection
                        })
                    wp.save()
            tp.workflow_state = "Completed"
            tp.save()
            tp.reload()


    def recall_create_medical_insurance_transfer(self):
        medical_insurance.creat_medical_insurance_for_transfer(self.employee)

    def notify_grd_transfer_mi_record(self):
        transfer_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_transfer")
        mi = frappe.db.get_value("Medical Insurance",{'employee':self.employee,'insurance_status':'Local Transfer'},['name'])
        if mi:
            mi_record = frappe.get_doc('Medical Insurance', mi)
            page_link = get_url("/desk#Form/Medical Insurance/" + mi_record.name)
            subject = ("Apply for Medical Insurance Online")
            message = "<p>Please Apply for Medical Insurance for employee:  <a href='{0}'></a>.</p>".format(mi_record.civil_id,page_link)
            create_notification_log(subject, message, [transfer_operator], mi_record)
     
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
                if document.document_name == "Work Permit":
                    to_remove.append(document)
            [document.delete(document) for document in to_remove]

    def set_work_permit_attachment_in_employee_doctype(self,work_permit_attachment,new_expiry_date):
        """This method to sort records of employee documents upon document name;
           First, get the employee document child table. second, find index of the document. Third, set the new document.
           After that, clear the child table and append the new order"""

        today = date.today()
        Find = False
        employee = frappe.get_doc('Employee', self.employee)
        document_dic = frappe.get_list('Employee Document',fields={'attach','document_name','issued_on','valid_till'},filters={'parent':self.employee})
        for index,document in enumerate(document_dic):
            if document.document_name == "Work Permit":
                Find = True
                break
        if Find:
            document_dic.insert(index,{
                "attach": work_permit_attachment,
                "document_name": "Work Permit",
                "issued_on":today,
                "valid_till": new_expiry_date
            })
            employee.set('one_fm_employee_documents',[]) #clear the child table
            for document in document_dic:                # append new arrangements
                employee.append('one_fm_employee_documents',document)

        if not Find:
            employee.append("one_fm_employee_documents", {
            "attach": work_permit_attachment,
            "document_name": "Work Permit",
            "issued_on":today,
            "valid_till":new_expiry_date
            })
        employee.work_permit_expiry_date = new_expiry_date
        employee.save()   
        
    @frappe.whitelist()
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

# Create Work Permit Record for new Kuwaiti
def create_work_permit_new_kuwaiti(pifss_name,employee):
    pifss103_form = frappe.get_doc('PIFSS Form 103',pifss_name)
    if pifss103_form:
        employee_in_pifss103_form = frappe.get_doc('Employee',employee)
        if employee_in_pifss103_form:
            create_wp_kuwaiti(frappe.get_doc('Employee',employee_in_pifss103_form.employee),"New Kuwaiti",pifss_name)

# Create Work Permit Record for Transfer
@frappe.whitelist()
def create_work_permit_transfer(tp_name,employee):
    tp = frappe.get_doc('Transfer Paper',tp_name)
    if tp:
        employee_in_tp = frappe.get_doc('Employee',employee)
        if employee_in_tp:
            create_wp_transfer(frappe.get_doc('Employee',employee_in_tp.employee),"Local Transfer",tp_name)#check if you need to do it this way create_wp_transfer(employee_in_tp,"Local Transfer",tp_name)
            

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

############################################################################# Reminder Notification 
def system_remind_renewal_operator_to_apply():# cron job at 4pm
    """This is a cron method runs every day at 4pm. It gets Draft renewal work permit list and reminds operator to apply on pam website"""
    supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
    renewal_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")
    work_permit_list = frappe.db.get_list('Work Permit',
    {'date_of_application':['<=',date.today()],'workflow_state':['in',('Draft','Apply Online by PRO')],'work_permit_type':['in',('Renewal Non Kuwaiti','Renewal Kuwaiti')]},['civil_id','name','reminded_grd_operator','reminded_grd_operator_again'])
    notification_reminder(work_permit_list,supervisor,renewal_operator,"Renewal")

def system_remind_transfer_operator_to_apply():# cron job at 4pm
    """This is a cron method runs every day at 4pm. It gets Draft transfer work permit list and reminds operator to apply on pam website"""
    supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
    transfer_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_transfer")
    work_permit_list = frappe.db.get_list('Work Permit',
    {'date_of_application':['<=',date.today()],'workflow_state':['in',('Draft','Apply Online by PRO')],'work_permit_type':['=',('Local Transfer')]},['civil_id','name','reminded_grd_operator','reminded_grd_operator_again'])
    notification_reminder(work_permit_list,supervisor,transfer_operator,"Local Transfer")


def notification_reminder(work_permit_list,supervisor,operator,type):
    """This method sends first, second, reminders and then send third one and cc supervisor in the email"""
    first_reminder_list=[] 
    second_reminder_list=[] 
    penality_reminder_list=[] 
    if work_permit_list and len(work_permit_list) > 0:
        for wp in work_permit_list:
            if wp.reminded_grd_operator_again:
                penality_reminder_list.append(wp)
            elif wp.reminded_grd_operator and not wp.reminded_grd_operator_again:
                second_reminder_list.append(wp)
            elif not wp.reminded_grd_operator:
                first_reminder_list.append(wp)

    if penality_reminder_list and len(penality_reminder_list)>0:
        email_notification_reminder(operator,penality_reminder_list,"Third Reminder","Apply for",type,supervisor)
    elif second_reminder_list and len(second_reminder_list)>0:
        email_notification_reminder(operator,second_reminder_list,"Second Reminder","Apply for",type)
        for wp in second_reminder_list:
            frappe.db.set_value('Work Permit',wp.name,'reminded_grd_operator_again',1)
    elif first_reminder_list and len(first_reminder_list)>0:
        email_notification_reminder(operator,first_reminder_list,"First Reminder","Apply for",type)
        for wp in first_reminder_list:
            frappe.db.set_value('Work Permit',wp.name,'reminded_grd_operator',1)
        
def email_notification_reminder(grd_user,work_permit_list,reminder_number, action,type, cc=[]):
    """This method send email to the required operator with the list of work permit for applying"""
    message_list=[]
    for work_permit in work_permit_list:
        page_link = get_url("/desk#Form/Work Permit/"+work_permit.name)
        message = "<a href='{0}'>{1}</a>".format(page_link, work_permit.civil_id)
        message_list.append(message)

    if message_list:
        message = "<p>{0}: Please {1} {2} Work Permit listed below</p><ol>".format(reminder_number,action,type)
        for msg in message_list:
            message += "<li>"+msg+"</li>"
        message += "<ol>"
        make(
            subject=_('{0}: {1} {2} Work Permit'.format(reminder_number,action,type)),
            content=message,
            recipients=[grd_user],
            cc=cc,
            send_email=True,
        )

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

# @frappe.whitelist()#allow_guest=True)
# def import_pdf_wp_file(file_url):
#     url = frappe.get_site_path() + file_url
#     pdfReader = PyPDF2.PdfFileReader(open(url,'rb'))
#     pages = pdfReader.numPages
#     pageObj = pdfReader.getPage(0)
#     return pageObj.documentInfo 