# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import get_url
from one_fm.api.notification import create_notification_log
# from frappe.utils import today
from datetime import date
from one_fm.hiring.utils import update_onboarding_doc

class MGRP(Document):
	def validate(self):
		self.children_table()
		self.set_grd_values()
		self.set_status()
		if not self.end_of_service_attachment:
			self.set_resignation_attachment()
		if not self.date_of_application:
			self.set_date_of_applicantion_value()

	def after_insert(self):
		update_onboarding_doc(self)

	def set_progress(self):
		progress_wf_list = {'Draft': 0, 'Form Printed': 10}
		if self.workflow_state in progress_wf_list:
			self.progress = progress_wf_list[self.workflow_state]

	def on_trash(self):
		if self.docstatus == 0:
			update_onboarding_doc(self, True)

	def on_cancel(self):
		update_onboarding_doc(self, True)

	def on_submit(self):
		update_onboarding_doc(self)

	def on_update(self):
		self.check_workflow_states()
		update_onboarding_doc(self)

	def set_resignation_attachment(self):
		""" If the resination form is not set from the employee attachments, will fetch the attachment and set its value"""
		Table = frappe.get_doc('Employee',{'one_fm_civil_id':self.civil_id},['one_fm_employee_documents'])
		for row in Table.one_fm_employee_documents:
			if row.document_name  == "Resignation Form":
				self.db_set('end_of_service_attachment',row.attach)

	def set_date_of_applicantion_value(self):
		self.db_set('date_of_application',date.today())


	def set_grd_values(self):
		if not self.grd_supervisor:
			self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
		if not self.grd_operator:
			self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_pifss")

	def children_table(self):
		"""This method is getting the child table details from the employee record based on the selected employee"""
		table=[]
		if self.employee:
			child_num = frappe.db.get_value('Employee',{'name':self.employee},['number_of_children'])
			if child_num:
				employee = frappe.get_doc('Employee',self.employee)
				for child in employee.children_details:
					table.append({
						'child_name': child.child_name,
						'child_name_in_arabic': child.child_name_in_arabic,
						'age': child.age,
						'work_status': child.work_status,
						'married': child.married,
						'health_status': child.health_status
					})

			if len(table)>0:
				for row in table:
					children = self.append('children_details_table',{})
					children.child_name = row['child_name']
					children.child_name_in_arabic = row['child_name_in_arabic']
					children.age = row['age']
					children.work_status = row['work_status']
					children.married = row['married']
					children.health_status = row['health_status']
				children.save()
				frappe.db.commit()

			print("child table >",self.children_details_table)
	def set_status(self):
		if self.status == "New Kuwaiti":
			self.db_set('status',"Registration")
		if self.status == "Cancellation":
			self.db_set('status',"Cancellation")


	def check_workflow_states(self):
		if self.workflow_state == "Form Printed":
			field_list = [{'Status':'status'},{'Employee':'employee'},{'Company Name':'company_name'}
						,{'Signatory Name':'signatory_name'}]
			self.set_mendatory_fields(field_list)
		
		if self.workflow_state == "Apply Online by PRO":
			field_list = [{'Attach MGRP Signed Form':'attach_mgrp_signed_form'}]
			self.set_mendatory_fields(field_list)

		if self.workflow_state == "Awaiting Response" and self.flag == 0:#check the previous workflow (DRAFT) required fields
			message_detail = '<b style="color:red; text-align:center;">First, You Need to Apply through <a href="{0}">MGRP Website</a></b><br><b>You Will Be Notified Daily at 8am To Check Applicantion Status</b>'.format(self.mgrp_website)
			frappe.msgprint(message_detail)
			self.db_set('flag',1)

		if self.workflow_state == "Completed":
			field_list = [{'Attach MGRP Approval':'attach_mgrp_approval'}]
			message_detail = '<b style="color:red; text-align:center;">First, You Need to Take Screenshot of Acceptance from <a href="{0}">MGRP Website</a></b>'.format(self.mgrp_website)
			self.set_mendatory_fields(field_list,message_detail)

	def set_mendatory_fields(self,field_list,message_detail=None):
		mandatory_fields = []
		for fields in field_list:
			for field in fields:
				if not self.get(fields[field]):
						mandatory_fields.append(field)

		if len(mandatory_fields) > 0:
			if message_detail:
				message = message_detail
				message += '<br>Mandatory fields required in PIFSS 103 form<br><br><ul>'
			else:
				message= 'Mandatory fields required in PIFSS 103 form<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' + mandatory_field +'</li>'
			message += '</ul>'
			frappe.throw(message)


	# def check_mgrp_website_response(self):
	# 	if self.workflow_state == "Awaiting Response":
	# 		page_link = get_url("/desk#Form/MGRP/" + self.name)
	# 		subject = _("Check MGRP website response")
	# 		message = "<p>Please check {0} response throught MGRP Website <a href='{1}'></a></p>".format(self.status,page_link)
	# 		create_notification_log(subject, message, [self.grd_operator], self)

def notify_awaiting_response_mgrp(doc, method): #will run everyday at 8 am
	docs = frappe.get_all("MGRP", {"workflow_state": ("in", ["Awaiting Response"]),"date_of_application":("<",date.today())})
	subject = _("Reminder: Awaiting Response MGRP's")
	for_users = doc.grd_operator

	message = "Below is the list of Awaiting Response MGRP (Click on the name to open the form).<br><br>"
	for doc in docs:
		message += "<a href='/desk#Form/MGRP/{doc}'>{doc}</a> <br>".format(doc=doc.name)


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
def get_signatory_name_for_mgrp(parent):
	"""Mehtod fetching the name of the company and passing child table field upon company name"""
	names=[]
	names.append(' ')#add empty record, to check if this field got selected by onboard user else it will throw message to fill the empty record
	if parent:
		doc = frappe.get_doc('PIFSS Authorized Signatory',parent)

		for autorized_signatory in doc.authorized_signatory:
			if autorized_signatory.authorized_signatory_name_arabic:
				names.append(autorized_signatory.authorized_signatory_name_arabic)
	return names

@frappe.whitelist()
def get_signatory_user_for_mgrp(company_name,user_name):
	"""Method getting user id & attached signature from record based on given filter"""
	parent = frappe.db.get_value('PIFSS Authorized Signatory',{'company_name_arabic':company_name},['name'])
	user,signature = frappe.db.get_value('PAM Authorized Signatory Table',{'parent':parent,'authorized_signatory_name_arabic':user_name},['user','signature'])
	return user,signature

@frappe.whitelist()#onboarding linking
def create_mgrp_form_for_onboarding(employee, onboard_employee):
	""" This Method for onboarding """
	mgrp = frappe.new_doc('MGRP')
	mgrp.status = "Registration"
	mgrp.employee = employee
	mgrp.onboard_employee = onboard_employee
	mgrp.save(ignore_permissions=True)
	return mgrp
