# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe import msgprint, throw, _
from frappe.utils import today, add_days, get_url, date_diff
from frappe.model.document import Document
from one_fm.api.notification import create_notification_log
from one_fm.grd.doctype.work_permit import work_permit
class PIFSSForm103(Document):
	# def validate(self):
	# 	self.check_penality()

	def on_update(self):
		self.notify_authorized_signatory()
		self.check_penality()
			
	def notify_authorized_signatory(self):
		if self.pifss_authorized_signatory and self.signatory_name and self.notify_for_signature == 0:
			subject = _("Reminder: Authorized Signatory on PIFSS 103 Form")
			message = "You are requested to sgin on PIFSS 103 form. <br>".format(self.name)
			for_users = frappe.db.sql_list("""select user from `tabPAM Authorized Signatory Table`""")
			for user in for_users:
				if self.user == user:
					create_notification_log(subject, message, [self.user], self)
			if not frappe.db.exists('Work Permit',{'employee':self.employee, 'work_permit_type':'New Kuwaiti'}):#create record only one time but can sent notification everytime
				self.recall_create_work_permit_new_kuwaiti()
			self.notify_for_signature = 1

	def check_penality(self):
		if self.date_of_request and self.date_of_registeration and self.date_of_joining:
			if date_diff(self.date_of_registeration,self.date_of_joining) == 9 or date_diff(self.date_of_registeration,self.date_of_joining) > 9:
				frappe.msgprint(_("Issue Penality for PRO"))
			if date_diff(self.date_of_request,self.date_of_joining) == 9 or date_diff(self.date_of_request,self.date_of_joining) > 9:
				frappe.msgprint(_("Issue Penality for Employee"))
	
	
	def recall_create_work_permit_new_kuwaiti(self):
		work_permit.create_work_permit_new_kuwaiti(self.name, self.employee)

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
