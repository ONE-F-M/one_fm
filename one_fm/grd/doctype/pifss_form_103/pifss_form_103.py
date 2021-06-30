# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import date
from one_fm.api.notification import create_notification_log
from frappe import _
from one_fm.grd.doctype.work_permit import work_permit
class PIFSSForm103(Document):
	
	def validate(self):
		self.set_grd_values()
		
	def set_grd_values(self):
		if not self.grd_supervisor:
			self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
		if not self.grd_operator:
			self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")
	
	def on_submit(self):
		if self.workflow_state == "Accepted":
			self.check_penality()
			self.recall_create_work_permit_new_kuwaiti()

class PIFSSForm103(Document):
	def on_update(self):
		self.check_workflow_states()
		#self.set_required_document_by_operator()
		
			
	def notify_authorized_signatory(self):
		if self.pifss_authorized_signatory and self.signatory_name and self.notify_for_signature == 0:
			subject = _("You are Authorized for PIFSS 103 Form Signatory")
			message = "You are requested to sgin on PIFSS 103 form.<br>".format(self.name)
			for_users = frappe.db.sql_list("""select user from `tabPAM Authorized Signatory Table`""")
			for user in for_users:
				if self.user == user:
					create_notification_log(subject, message, [self.user], self)
			self.notify_for_signature = 1


	def check_workflow_states(self):
		today = date.today()
		if self.workflow_state == "Under Process" and self.notify_grd_operator == 0:
			self.db_set('date_of_request', today)
			self.notify_grd()
			self.db_set('notify_grd_operator', 1)
		if self.workflow_state == "Apply Online by PRO" and frappe.session.user == self.grd_operator and not self.registration_application_number:
			frappe.throw("Registration Application Number is Required")
		if self.workflow_state == "Apply Online by PRO" and frappe.session.user == self.grd_operator and self.registration_application_number:
			self.db_set('date_of_registeration', today)
		if self.workflow_state == "Accepted":
			self.db_set('date_of_acceptance', today)
			#if not frappe.db.exists('Work Permit',{'employee':self.employee, 'work_permit_type':'New Kuwaiti'}):#create record only one time but can sent notification everytime
			


	def notify_grd(self):
		page_link = get_url("/desk#Form/Fingerprint Appointment/" + self.name)
		subject = ("Requested to Apply for Form 103 By Onboarding to {0}").format(self.employee_name)
		message = "<p>Apply for Form 103 for <a href='{0}'></a>.</p>".format(self.employee_name)
		create_notification_log(subject, message, [self.grd_operator], self)

	def check_penality(self):
		if self.date_of_request and self.date_of_registeration and self.date_of_joining:
			if date_diff(self.date_of_registeration,self.date_of_joining) >= 9:
				frappe.msgprint(_("Issue Penality for PRO"))
			if date_diff(self.date_of_request,self.date_of_joining) >= 9 :
				frappe.msgprint(_("Issue Penality for Employee"))
	
	def notify_authorized_signatory(self):
		subject = _("Reminder: Authorized Signatory on PIFSS 103 Form")
		message = "You are requested to sgin on PIFSS 103 form. <br>".format(self.name)
		for_users = frappe.db.sql_list("""select user from `tabPAM Authorized Signatory Table`""")
		for user in for_users:
			if self.user == user:
				create_notification_log(subject, message, [self.user], self)
	
	def create_wp_record(self):
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
	return name_list

@frappe.whitelist()
def get_signatory_user(user_name):
	user = frappe.db.get_value('PAM Authorized Signatory Table',{'authorized_signatory_name_arabic':user_name},['user'])
	return user
