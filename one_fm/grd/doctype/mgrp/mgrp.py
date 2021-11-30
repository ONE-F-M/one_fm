# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import get_url, cint, today
from one_fm.api.notification import create_notification_log
from datetime import date
from one_fm.hiring.utils import update_onboarding_doc
from frappe.core.doctype.communication.email import make
class MGRP(Document):
	def validate(self):
		self.get_children_table()
		self.set_grd_values()
		self.set_status()
		self.set_progress()
		if self.status == "Cancellation" and not self.end_of_service_attachment:
			self.set_resignation_attachment()
		if not self.date_of_application:
			self.date_of_application = today()

	def after_insert(self):
		update_onboarding_doc(self)

	def set_progress(self):
		"""
		runs: `validate`
		param: mgrp object
		This method visualizing the progress in `Onboard Employee` record under progress section
		"""
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
		""" 
		runs: `validate`
		param: mgrp object
		This method checks if resignation form is not set in employee attachments, will fetch the attachment and set its value
		"""
		table = frappe.get_doc('Employee',{'one_fm_civil_id':self.civil_id},['one_fm_employee_documents'])
		for row in table.one_fm_employee_documents:
			if row.document_name  == "Resignation Form":
				self.db_set('end_of_service_attachment',row.attach)
		
	def set_grd_values(self):
		"""
		runs: `validate`
		param: mgrp object
		This method sets the user_id for both GRD Supervisor and Operator handling pifss form GRD Settings Doctype
		"""
		if not self.grd_supervisor:
			self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
		if not self.grd_operator:
			self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_pifss")

	def get_children_table(self):
		"""
		runs: `validate`
		param: mgrp object
		This method is getting the children details from the employee record based on the selected employee,
		"""
		if self.employee and cint(self.number_of_children) > 0 and len(self.children_details_table) == 0:
			child_num = frappe.db.get_value('Employee',{'name':self.employee},['number_of_children'])
			if cint(child_num) > 0:
				employee = frappe.get_doc('Employee',self.employee) # Fetching the children table from Employee to MGRP doctype
				for child in employee.children_details:
					children = self.append('children_details_table',{})
					children.child_name = child.child_name
					children.child_name_in_arabic = child.child_name_in_arabic
					children.age = child.age
					children.work_status = child.work_status
					children.married = child.married
					children.health_status = child.health_status
				frappe.db.commit()

	def set_status(self):
		"""
		runs: `validate`
		param: mgrp object
		This method sets mgrp status upon `work_permit_type` otherwise it will asks user to set status value
		"""
		if self.work_permit_type:
			if self.work_permit_type == "New Kuwaiti":
				self.db_set('status',"Registration")
			if self.work_permit_type == "Cancellation":
				self.db_set('status',"Cancellation")
		else:
			field_list = [{'Status':'status'}]
			self.set_mendatory_fields(field_list)


	def check_workflow_states(self):
		"""
		runs: `on_update`
		param: mgrp object
		This method asks for mandatory fields in every `workflow_state` 
		"""
		if self.workflow_state == "Form Printed":
			field_list = [{'Status':'status'},{'Employee':'employee'},{'Company Name':'company_name'}
						,{'Signatory Name':'signatory_name'}]
			self.set_mendatory_fields(field_list)
		
		if self.workflow_state == "Apply Online by PRO":
			field_list = [{'Attach MGRP Signed Form':'attach_mgrp_signed_form'}]
			self.set_mendatory_fields(field_list)

		if self.workflow_state == "Awaiting Response" and self.flag == 0:
			message_detail = '<b style="color:red; text-align:center;">First, You Need to Apply through <a href="{0}">MGRP Website</a></b><br><b>You Will Be Notified Daily at 8am To Check Applicantion Status</b>'.format(self.mgrp_website)
			frappe.msgprint(message_detail)
			self.db_set('flag',1)

		if self.workflow_state == "Completed":
			field_list = [{'Attach MGRP Approval':'attach_mgrp_approval'}]
			message_detail = '<b style="color:red; text-align:center;">First, You Need to Take Screenshot of Acceptance from <a href="{0}">MGRP Website</a></b>'.format(self.mgrp_website)
			self.set_mendatory_fields(field_list,message_detail)

	def set_mendatory_fields(self,field_list,message_detail=None):
		"""
		This method throws a message and the mandatory fields that need to be set by user

		Args:
			field_list: List of dictionary having the lable and field name (eg: [{'Status':'status'},{'Employee':'employee'}] )
			message_detail(optional): The message will have detailed description or sometime a website link to help operator fetch the needed values from mgrp website directly. Defaults to None.
		"""
		mandatory_fields = []
		for fields in field_list:
			for field in fields:
				if not self.get(fields[field]):
						mandatory_fields.append(field)

		if len(mandatory_fields) > 0:
			if message_detail:
				message = message_detail
				message += '<br>Mandatory fields required in MGRP form<br><br><ul>'
			else:
				message= 'Mandatory fields required in MGRP form<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' + mandatory_field +'</li>'
			message += '</ul>'
			frappe.throw(message)

def notify_awaiting_response_mgrp():
	"""
	runs: `Hooks` everyday at 8am
	This method fetches list of objects having `Awaiting Response` workflow state
	"""
	mgrp_list = frappe.db.get_list('MGRP',{'workflow_state':['=',('Awaiting Response')]},['name','civil_id'])
	notification_reminder(mgrp_list)

def notification_reminder(mgrp_list):
	"""
	This method for notifying operator to check the status of the employee on MGRP website
	
	Args:
		mgrp_list ([list of objects]): [list of objects having `Awaiting Response` workflow state]
	"""
	message_list=[]
	grd_user = frappe.db.get_single_value("GRD Settings", "default_grd_operator_pifss")
	grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
	for mgrp in mgrp_list:
		page_link = get_url("/desk#Form/MGRP/"+mgrp.name)
		message = "<a href='{0}'>{1}</a>".format(page_link, mgrp.civil_id)
		message_list.append(message)

	if message_list:
		message = "<p>Please Check MGRP website for MGRP listed below</p><ol>".format()
		for msg in message_list:
			message += "<li>"+msg+"</li>"
		message += "<ol>"
		make(
			subject=_('Awaiting Response MGRP'),
			content=message,
			recipients=[grd_user],
			cc=grd_supervisor,
			send_email=True,
		)

@frappe.whitelist()
def get_signatory_name_for_mgrp(parent):
	"""
	This method is passing company name to fetch `authorized_signatory_name_arabic` from the child table Authorized Signatory in PIFSS Authorized Signatory Doctype

	Args:
		parent: it is the selected `company_name` to get the Authorized signatory list upon company name

	Returns:
		names: list of authorized signatory arabic names
	"""
	names=[]
	names.append(' ')# add empty record, to check if this field got selected by onboard user else it will throw message to fill the empty record
	if parent:
		doc = frappe.get_doc('PIFSS Authorized Signatory',parent)

		for autorized_signatory in doc.authorized_signatory:
			if autorized_signatory.authorized_signatory_name_arabic:
				names.append(autorized_signatory.authorized_signatory_name_arabic)
	return names

@frappe.whitelist()
def get_signatory_user_for_mgrp(company_name,user_name):
	"""
	This method returns the `user_id` and `signature` of the selected authrized signatory
	Args:
		company_name: the selected company name in mgrp document
		user_name: Authorized Signatory Arabic name

	Returns:
		user: Authorized Signatory user id to notify him later on
		signature: Authorized Electronic signature 
	"""
	parent = frappe.db.get_value('PIFSS Authorized Signatory',{'company_name_arabic':company_name},['name'])
	user,signature = frappe.db.get_value('PAM Authorized Signatory Table',{'parent':parent,'authorized_signatory_name_arabic':user_name},['user','signature'])
	return user,signature

@frappe.whitelist()
def create_mgrp_form_for_onboarding(employee, onboard_employee):
	"""
	This Method will be called in onboarding once pressing `MGRP` button and this button will show for Kuwaiti employee only
	Args:
		employee: (eg: HR-EMP-00001)
		onboard_employee: link to onboard_employee table (eg: EMP-ONB-2021-00021)

	Returns:
		mgrp: MGRP object
	"""
	mgrp = frappe.new_doc('MGRP')
	mgrp.status = "Registration"
	mgrp.employee = employee
	mgrp.onboard_employee = onboard_employee
	mgrp.save(ignore_permissions=True)
	return mgrp
