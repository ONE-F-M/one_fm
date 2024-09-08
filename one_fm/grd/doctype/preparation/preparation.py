# class Preparation(Document):
# 	pass
# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import (
    today,
    add_months,
    get_url,
    nowdate,
    getdate,
    now_datetime,
    get_first_day,
    get_last_day
)
import datetime
from one_fm.grd.doctype.work_permit import work_permit
from one_fm.grd.doctype.medical_insurance import medical_insurance
from one_fm.grd.doctype.residency_payment_request import residency_payment_request
from one_fm.grd.doctype.moi_residency_jawazat import moi_residency_jawazat
from one_fm.grd.doctype.paci import paci
from one_fm.grd.doctype.fingerprint_appointment import fingerprint_appointment
from one_fm.processor import sendemail

class Preparation(Document):
    def update_total_amount(self):
        doc_total = sum(i.total_amount for i in self.preparation_record)
        # self.total_payment = doc_total
        frappe.db.set_value(self.doctype,self.name,'total_payment',doc_total)
                     
    def on_update_after_submit(self):
        self.compare_preparation_record()
        self.update_total_amount()
    
    def compare_preparation_record(self):
        """Compare the data of preparation record child table before it was saved with the most updated version
        and flag changes
        """
        old_preparation_record = {}
        new_preparation_record = {}
        old_doc = self.get_doc_before_save()
        for each in old_doc.preparation_record: 
            old_preparation_record[each.name] =  each
        old_row_ids = [i.name for i in old_doc.preparation_record ]
        for one in self.preparation_record:
            new_preparation_record[one.name] =  one
        new_row_ids = [i.name for i in self.preparation_record ]
        
        for ind in old_row_ids: #Find Removed rows 
            if ind not in new_row_ids:
                # self.fetch_linked_records(existing_preparation_record.get(ind)) # Delete for this employee
                cancel_delete_doc("PACI",self.name,old_preparation_record.get(ind))
                cancel_delete_doc("Work Permit",self.name,old_preparation_record.get(ind))
                cancel_delete_doc("MOI Residency Jawazat",self.name,old_preparation_record.get(ind))
                cancel_delete_doc("Medical Insurance",self.name,old_preparation_record.get(ind))
            else:
                if old_preparation_record.get(ind).get('renewal_or_extend')!=new_preparation_record.get(ind).get('renewal_or_extend'):
                    handle_renewal_changes(old_preparation_record.get(ind),new_preparation_record.get(ind),self.name) #Create or Delete based on choices
        for each in new_row_ids: #Find New rows added
            if each not in old_row_ids:
                handle_creation_of_grd_docs(new_preparation_record.get(each),self.name)
                 
            
        
            
    
    
    
    def validate(self):
        self.set_grd_values()
        self.set_hr_values()

    def set_grd_values(self):
        """
		runs: `validate`
		param: preparation object
		This method is fetching values of grd supervisor or operator for renewal from GRD settings
		"""
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")

    def set_hr_values(self):
        """
		runs: `validate`
		param: preparation object
		This method is fetching values of hr user
		"""
        if not self.hr_user:
            self.hr_user = frappe.db.get_single_value("Hiring Settings","default_hr_user")

    def on_submit(self):
        self.validate_mandatory_fields_on_submit()

        self.db_set('submitted_by', frappe.session.user)
        self.db_set('submitted_on', now_datetime())
        self.recall_create_work_permit_renewal() ## create work permit record for renewals
        self.recall_create_medical_insurance_renewal() # create medical insurance record for renewals
        self.recall_create_moi_renewal_and_extend() # create moi record for all employee
        self.recall_create_paci() # create paci record for all
        # self.recall_create_fp()# create fp record for all
        self.send_notifications()

    def validate_mandatory_fields_on_submit(self):
        mandatory_fields = []
        mandatory_fields_reqd = False
        for item in self.preparation_record:#each item in the preparation_record row
            if not item.renewal_or_extend:#column not filled
                mandatory_fields_reqd = True
                mandatory_fields.append(item.idx)
        if len(mandatory_fields) > 0:
            message = 'Mandatory fields required in Preparation to Submit<br><br><ul>'
            for mandatory_field in mandatory_fields:
                message += '<li>' +'<p> fill the renewal or extend field for row number {0}</p>''</li>'.format(mandatory_field)
            message += '</ul>'
            frappe.throw(message)

        if self.hr_approval == "No":
            frappe.throw("Must Be Approved By HR ")

    def recall_create_work_permit_renewal(self):
        work_permit.create_work_permit_renewal(self.name)

    def recall_create_medical_insurance_renewal(self):
        medical_insurance.valid_work_permit_exists(self.name)

    def recall_create_moi_renewal_and_extend(self):
        moi_residency_jawazat.set_employee_list_for_moi(self.name)

    def recall_create_paci(self):
        paci.create_PACI_renewal(self.name)

    def recall_create_fp(self):
        fingerprint_appointment.creat_fp_record(self.name)

    def send_notifications(self):
        """
            runs: `on_submit`
            This method will notifiy operator to apply for the wp, mi, moi, paci, fp that are created for all employees in the list
        """
        if self.grd_operator:
            page_link = get_url(self.get_url())
            message = "<p>Records are created<a href='{0}'>{1}</a>.</p>".format(page_link, self.name)
            subject = 'Records are created for WP, MI, MOI, PACI, and FP'
            create_notification_log(subject, message, [self.grd_operator], self)

        inform_the_costing_to = frappe.db.get_single_value('GRD Settings', 'inform_the_costing_to')
        if inform_the_costing_to:
            page_link = get_url(self.get_url())
            message = "<p>Records are created<a href='{0}'>{1}</a>.</p>".format(page_link, self.name)
            subject = 'Details of the Preparation Cost for WP, MI, MOI, PACI, and FP'
            print_format = frappe.db.get_single_value('GRD Settings', 'costing_print_format')
            if not print_format:
                print_format = 'Standard'
            attachments = [frappe.attach_print(self.doctype, self.name, file_name=self.name, print_format=print_format)]
            send_email(self, [inform_the_costing_to], message, subject, attachments)

    def after_insert(self):
        self.update_last_preparation_details_to_grd_settings()

    def update_last_preparation_details_to_grd_settings(self):
        frappe.db.set_value("GRD Settings", None, "last_preparation_record_created_on", self.creation)
        frappe.db.set_value("GRD Settings", None, "last_preparation_record_created_by", self.owner)

    @frappe.whitelist()
    def set_renewal_for_all_preparation_record(self, renew_all):
        # Get costing of renewal for an year
        costing  = get_grd_renewal_extension_cost("Renewal", "1 Year")
        # Set the costing of renewal for an year in preparation record
        for preparation in self.preparation_record:
            preparation.renewal_or_extend = "Renewal" if renew_all else ""
            preparation.no_of_years = "1 Year" if renew_all else ""
            preparation.work_permit_amount = costing.work_permit_amount if renew_all else ""
            preparation.medical_insurance_amount = costing.medical_insurance_amount if renew_all else ""
            preparation.residency_stamp_amount = costing.residency_stamp_amount if renew_all else ""
            preparation.civil_id_amount = costing.civil_id_amount if renew_all else ""
            preparation.total_amount = costing.total_amount if renew_all else ""

# Calculate the date of the next month (First & Last) (monthly cron in hooks)
def auto_create_preparation_record():
    """
    runs: at the Preparation Record Creation Day configured in the GRD Settings
    This method will create preparation record that contain list of all employees that their residency expiry date will be between the first and the last date of the next month
    This record will go to HR user to set value for each employee either renewal or extend and on the submit of this record it will ask for hr permission and approval.
    Then, it will create wp, mi, moi, and paci records for all employees in the list.
    """
    preparation_record_creation_day = frappe.db.get_single_value("GRD Settings", "preparation_record_creation_day")
    if preparation_record_creation_day and preparation_record_creation_day > 0:
        preparation_record_creation_day_date = datetime.date.today().replace(day=preparation_record_creation_day)
        if getdate(preparation_record_creation_day_date) == getdate(today()):
            create_preparation_record()

@frappe.whitelist()
def create_preparation_record():
    """
        This method will create preparation record for next month from the date of execution.
        The record contain list of all employees that their residency expiry date will be between the first and the last date of the next month
        This record will go to HR user to set value for each employee either renewal or extend and on the submit of this record it will ask for hr permission and approval.
    """
    doc = frappe.new_doc('Preparation')
    doc.posting_date = nowdate()
    first_day = get_first_day(add_months(getdate(today()), 1))
    last_day = get_last_day(getdate(first_day))
    employee_entries = frappe.db.get_list('Employee',
        fields=("residency_expiry_date", "name"),
        filters={
            'residency_expiry_date': ['between', (first_day, last_day)],
            'status': 'Active',
            'under_company_residency':['=', 1]
        }
    )
    employee_entries.sort(key=sort)
    for employee in employee_entries:
        doc.append("preparation_record", {
            "employee": employee.name
        })
    doc.save()
    notify_hr(doc)

# sort list based on residency expriy date to be displaied in the table based on their `residency_expiry_date`
def sort(r):
    return r['residency_expiry_date']

def notify_hr(doc):
    page_link = get_url(doc.get_url())
    subject = ("Preparation Record has been created")
    message = "<p>Kindly, Check and Fill The Renewal and Extend Field for Employees whose Residency Will Expire in the Following month <a href='{0}'></a></p>".format(page_link)
    create_notification_log(subject, message, [doc.hr_user], doc)

def notify_request_for_renewal_or_extend():# Notify finance
    filters = {'docstatus': 1, 'hr_approval': ['=', "Yes"]}
    preparation_list = frappe.get_doc('Preparation', filters,['name', 'notify_finance_user'])
    page_link = get_url(preparation_list.get_url())
    message = "<p>Please Review the Renewal and Extend List of employee {0}<a href='{1}'></a></p>".format(page_link,preparation_list.name)
    subject = '{0} Renewal and Extend list approved'.format("Prepare Payments")
    send_email(preparation_list, [preparation_list.notify_finance_user], message, subject)
    create_notification_log(subject, message, [preparation_list.notify_finance_user], preparation_list)

def send_email(doc, recipients, message, subject, attachments=None):
    sendemail(
        recipients= recipients,
        subject=subject,
        message=message,
        reference_doctype=doc.doctype,
        reference_name=doc.name,
        attachments=attachments
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
        doc.insert(ignore_permissions=True)

@frappe.whitelist()
def get_grd_renewal_extension_cost(renewal_or_extend, no_of_years=False):
	if renewal_or_extend == 'Renewal' and not no_of_years:
		return False
	else:
		query = """
			select
				*
			from
				`tabGRD Renewal Extension Cost`
			where
				parent = 'GRD Settings'
				and
				renewal_or_extend = '{0}'
		""".format(renewal_or_extend)
		if renewal_or_extend == 'Renewal':
			query += " and no_of_years = '{0}'".format(no_of_years)
		result = frappe.db.sql(query, as_dict=True)
		if result and len(result) > 0:
			return result[0]

def handle_creation_of_grd_docs(row,source):
    """
            Handle the creation of grd documents for  new rows just added after the submission of a preparation  document
    Args:
        row (dict): dict containing employee information
    """
    try:
        employee_doc = frappe.get_doc("Employee",row.employee)
        work_permit.create_wp_renewal(employee_doc,row.renewal_or_extend,source)
        frappe.db.commit() #because Medical Insurance depends on the work permit
        medical_insurance.create_mi_record(frappe.get_doc('Work Permit',{'preparation':source,'employee':employee_doc.employee}))
        moi_residency_jawazat.create_moi_record(employee_doc,row.renewal_or_extend,preparation_name=source)
        paci.create_PACI(employee_doc,row.renewal_or_extend,source)   
    except:
        frappe.log_error(title=f"Error Creating New GRD documents  for {row.employee} </b>",message=frappe.get_traceback()) 
    
    
def handle_renewal_changes(old_,new_,source):
    """
    Handle the changes in  renewal field of a row in the preparation record table 
    Args:
        old (dict): a dict containing details of the old row
        new (dict): a dict containing details of the new row
    """
    if old_.renewal_or_extend == "Renewal" and new_.renewal_or_extend in ['Extend 1 month','Extend 2 months','Extend 3 months']:
        cancel_delete_doc("PACI",source,new_)
        cancel_delete_doc("Medical Insurance",source,new_)
        cancel_delete_doc("Work Permit",source,new_)
    elif new_.renewal_or_extend == "Cancellation":
        cancel_delete_doc("MOI Residency Jawazat",source,new_)
        cancel_delete_doc("PACI",source,new_)
        cancel_delete_doc("Medical Insurance",source,new_)
        cancel_delete_doc("Work Permit",source,new_)
    elif new_.renewal_or_extend == "Renewal" and old_.renewal_or_extend != "Renewal":
        handle_creation_of_grd_docs(new_,source)
        #Create for all
        
            

def cancel_delete_doc(doctype,source,row):
    """
    Loop through a list of records, cancel and delete them
    Args:
        doctype (str): a doctype
        records (dict): a dict of records
    """
    records = frappe.get_all(doctype,{'preparation':source,'employee':row.employee},['docstatus','name'])
    
    for each in records:
        try:
            doc = frappe.get_doc(doctype,each.name)
            doc.flags.ignore_links = 1
            doc.flags.ignore_permissions = 1
            doc.save()
            if each.docstatus == 1:  
                doc.cancel()
            frappe.delete_doc(doctype,each.name,force= True)
        except:
            frappe.log_error(title=f"Error Cancelling and Deleting <b>{doctype} {each.name} </b>",message=frappe.get_traceback())
            
            continue