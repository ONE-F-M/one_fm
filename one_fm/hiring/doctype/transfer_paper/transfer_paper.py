
# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from one_fm.api.notification import create_notification_log
from frappe.model.document import Document
from frappe.utils import today, add_days, get_url
from one_fm.grd.doctype.work_permit import work_permit
from one_fm.api.notification import create_notification_log


class TransferPaper(Document):

    def validate(self):
        self.set_salary_from_job_offer()
        self.set_grd_values()
        self.set_electronic_signatory()

    def set_salary_from_job_offer(self):
        salary = frappe.db.get_value('Job Offer',{'job_applicant':self.applicant},['one_fm_job_offer_total_salary'])
        self.db_set('salary', salary) 

    def set_grd_values(self):
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_transfer")

    def set_electronic_signatory(self):
        doc = frappe.get_doc('Job Applicant',self.applicant)
        if doc.one_fm_signatory_name and doc.one_fm_authorized_signatory:
            # print(doc.one_fm_signatory_name)
            authorized_list = frappe.get_doc('PAM Authorized Signatory List',doc.one_fm_authorized_signatory)
            for authorized in authorized_list.authorized_signatory:
                if doc.one_fm_signatory_name == authorized.authorized_signatory_name_arabic:
                    self.db_set('authorized_signature', authorized.signature)

   

    def on_update(self):
        self.check_signed_workContract_employee_completed()

    def check_signed_workContract_employee_completed(self):
        if self.signed == "Yes" and "Completed" in self.workflow_state and frappe.db.exists("Employee", {"one_fm_civil_id":self.civil_id}):#employee is created <NEED TO CHECK THE EMPLOYEE LIST ALL TIME>
            employee = frappe.db.get_value("Employee", {"one_fm_civil_id":self.civil_id})
            if employee:
                self.recall_create_transfer_work_permit(employee)#create wp
                self.get_wp_status()
                self.notify_grd_transfer_wp_record()

    def notify_grd_transfer_wp_record(self):
        # Getting the wp record the one not rejected and linked to the TP
        wp = frappe.db.get_value("Work Permit",{'transfer_paper':self.name,'work_permit_status':'Draft'})
        if wp:
            wp_record = frappe.get_doc('Work Permit', wp)
            page_link = get_url("/desk#Form/Work Permit/" + wp_record.name)
            subject = ("Apply for Transfer Work Permit Online")
            message = "<p>Please Apply for Transfer WP Online for <a href='{0}'></a>.</p>".format(page_link, wp_record.employee)
            create_notification_log(subject, message, [self.grd_operator], wp_record)

    def resend_new_wp_record(self):
        if self.tp_status == "Re-send":
            self.set_previous_wp_record_rejected()
            self.check_signed_workContract_employee_completed()

    def set_previous_wp_record_rejected(self):
        wp = frappe.db.get_value("Work Permit",{'transfer_paper':self.name})
        if wp:
            wp_record = frappe.get_doc('Work Permit', wp)
            wp_record.work_permit_status = "Rejected"
            wp_record.save()
            
    def recall_create_transfer_work_permit(self,employee):
        work_permit.create_work_permit_transfer(self.name,employee)

    def get_wp_status(self):
        wp = frappe.db.get_value("Work Permit",{'transfer_paper':self.name})
        print(wp)
        if wp:
            wp_record = frappe.get_doc("Work Permit",wp)
            self.work_permit_status = wp_record.work_permit_status
        self.save()#to set the value of the wp status in th tp dt


@frappe.whitelist()
def resend_new_wp_record(doc_name):
    wp = frappe.db.get_value("Work Permit",{'transfer_paper':doc_name})
    if wp:
        wp_record = frappe.get_doc('Work Permit', wp)
        wp_record.work_permit_status = "Closed"
        doc = frappe.get_doc('Transfer Paper',doc_name)
        doc.check_signed_workContract_employee_completed()
    wp_record.save()

@frappe.whitelist()
def closed_old_wp_record(doc_name):
    wp = frappe.db.get_value("Work Permit",{'transfer_paper':doc_name, 'work_permit_status':'Draft'})
    if wp:
        wp_record = frappe.get_doc('Work Permit', wp)
        wp_record.work_permit_status = "Closed"
    wp_record.save()
    

    

