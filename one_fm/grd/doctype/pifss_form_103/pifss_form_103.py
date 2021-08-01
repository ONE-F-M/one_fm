# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import date
from frappe.utils import today, add_days, get_url, date_diff, getdate
from one_fm.api.notification import create_notification_log
from frappe import _
from frappe.utils import get_datetime, add_to_date, getdate, get_link_to_form, now_datetime
from one_fm.grd.doctype.work_permit import work_permit

class PIFSSForm103(Document):
	def validate(self):
		self.set_grd_values()
		self.set_date()
		self.check_penality_for_registration()

	def set_grd_values(self):
		if not self.grd_supervisor:
			self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
		if not self.grd_operator:
			self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_pifss")
	
	def set_date(self):
		if not self.signature_date:
			self.db_set("signature_date",date.today())
		if not self.employee_signature_date:
			self.db_set("employee_signature_date",date.today())
	
	def check_penality_for_registration(self):
		if self.request_type == "Registration":
			if not self.date_of_request:
				if self.status == "Pending by GRD": 
					self.db_set('date_of_request',date.today())
			if not self.date_of_registeration:
				if self.status == "Awaiting Response": 
					self.db_set('date_of_registeration',date.today())
	
	def on_submit(self):
		if self.workflow_state == "Completed":
			field_list = [{'Attach Accept Status Screenshot from PIFSS Website':'attach_accept_screenshot_from_pifss_website'},
			{'End Date':'end_date'}]
			self.set_mendatory_fields(field_list)
		self.db_set('date_of_acceptance', date.today())
		self.check_penality()
		self.recall_create_work_permit_new_kuwaiti()

	def on_update(self):
		self.check_workflow_states()
					
	def check_workflow_states(self):
		if self.workflow_state == "Draft":#check the previous workflow (DRAFT) required fields 
			field_list = [{'Request Type':'request_type'},{'Employee':'employee'},{'Company Name':'company_name'}
						,{'Signatory Name':'signatory_name'}]
			self.set_mendatory_fields(field_list)

		if self.workflow_state == "Pending by GRD":
			field_list = [{'Attach 103 Signed Form':'attach_signed_form'}]
			self.set_mendatory_fields(field_list)
			
		if self.workflow_state == "Awaiting Response":
			if not self.reference_number:
				field_list = [{'Reference Number':'reference_number'}]
				self.set_mendatory_fields(field_list)

		if self.workflow_state == "Rejected":
			if self.reference_number:
				self.db_set('reference_number',"")

		if self.workflow_state == "Under Process":
			self.db_set('pifss_is_under_process_on', now_datetime())

	def set_mendatory_fields(self,field_list):
		mandatory_fields = []
		for fields in field_list:
			for field in fields:
				if not self.get(fields[field]):
						mandatory_fields.append(field)

		if len(mandatory_fields) > 0:
			message = 'Mandatory fields required in PIFSS 103 form<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' + mandatory_field +'</li>'
			message += '</ul>'
			frappe.throw(message)
		
	def notify_grd_to_check_status_on_pifss(self):
		"""
		This method for notifying operator to check the status of the employee on PIFSS website
		after 5 days of Applying,
		(Accepted, Rejected, Under Process)
		For removing and Enrolling Kuwaiti in PIFSS
		"""
		today = date.today()
		if self.workflow_state == "Awaiting Response" and self.registered_on:
			if date_diff(today,self.registered_on) == 5:#5
				page_link = get_url("/desk#Form/PIFSS Form 103/" + self.name)
				subject = ("Check PIFSS website response for {0} employee <a href='{1}'></a>").format(self.employee_name,page_link)
				message = "<p>Check Status for <a href='{0}'> on PIFSS Website</a>.</p>".format(self.employee_name)
				create_notification_log(subject, message, [self.grd_operator], self)

	def notify_grd_to_check_under_process_status_on_pifss(self):
		"""
		This method for notifying operator to check the status of the employee on PIFSS website
		after 2 days of Applying,
		(Accepted, Rejected, Under Process)
		For removing and Enrolling Kuwaiti in PIFSS
		"""
		today = date.today()
		if self.workflow_state == "Under Process" and self.pifss_is_under_process_on:
			if date_diff(today,self.pifss_is_under_process_on) == 2:#2
				page_link = get_url("/desk#Form/PIFSS Form 103/" + self.name)
				subject = ("Check PIFSS website response for {0} employee <a href='{1}'></a>").format(self.employee_name,page_link)
				message = "<p>Check Status for <a href='{0}'></a>.</p>".format(self.employee_name)
				create_notification_log(subject, message, [self.grd_operator], self)



	def notify_grd(self):
		page_link = get_url("/desk#Form/PIFSS Form 103/" + self.name)
		subject = ("Requested to Apply for Form 103 By Onboarding to {0}").format(self.employee_name)
		message = "<p>Apply for Form 103 for <a href='{0}'></a>.</p>".format(self.employee_name)
		create_notification_log(subject, message, [self.grd_operator], self)

	def check_penality(self):
		if self.date_of_request and self.date_of_registeration and self.date_of_joining:
			if date_diff(self.date_of_registeration,self.date_of_joining) >= 9 and date_diff(self.date_of_request,self.date_of_joining) < 9:#need to check the other dates as well
				frappe.msgprint(_("Issue Penality for PRO"))
			if date_diff(self.date_of_request,self.date_of_joining) >= 9:
				frappe.msgprint(_("Issue Penality for Employee"))
	
	def notify_authorized_signatory(self):
		subject = _("Note: Will use Your Signator on PIFSS 103 Form")
		message = "You are requested to sgin on PIFSS 103 form {0} for {1}. <br>".format(self.name,self.employee)
		for_users = frappe.db.sql_list("""select user from `tabPAM Authorized Signatory Table`""")
		for user in for_users:
			if self.user == user:
				create_notification_log(subject, message, [self.user], self)
	
	def recall_create_work_permit_new_kuwaiti(self):
		if self.request_type == "Registration":
			work_permit.create_work_permit_new_kuwaiti(self.name,self.employee)


def notify_open_pifss(doc, method):
	docs = frappe.get_all("PIFSS Form 103", {"status": ("in", ["Submitted", "Under Process"])})
	subject = _("Reminder: Submitted/Under Process PIFSS Form 103's")
	for_users = frappe.db.sql_list("""select user from `tabPIFSS Settings Users` """)

	message = "Below is the list of submitted/under process PIFSS Form 103 (Click on the name to open the form).<br><br>"
	for doc in docs:
		message += "<a href='/desk#Form/PIFSS Form 103/{doc}'>{doc}</a> <br>".format(doc=doc.name) 


	for user in for_users:
		notification = frappe.new_doc("Notification Log")
		notification.subject = subject
		notification.email_content = message
		notification.document_type = "Notification Log"
		notification.for_user = user
		notification.save()
		notification.document_name = notification.name
		notification.save()
		frappe.db.commit()

@frappe.whitelist()
def get_signatory_name(parent):
	name_list = frappe.db.sql("""select  authorized_signatory_name_arabic from `tabPAM Authorized Signatory Table`
				where parent = %s  """,(parent),as_list=1)
	return ' ',name_list

@frappe.whitelist()
def get_signatory_user(user_name):
	user = frappe.db.get_value('PAM Authorized Signatory Table',{'authorized_signatory_name_arabic':user_name},['user'])
	return user
