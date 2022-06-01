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
from one_fm.hiring.utils import update_onboarding_doc
from frappe.core.doctype.communication.email import make

class PIFSSForm103(Document):
	def validate(self):
		self.employee_full_name()
		self.check_employee_fields()
		self.set_grd_values()
		self.set_date()
		self.set_progress()
		# self.check_penality_for_registration()#for setting the 3 dates to identify to whom is the penlty (date of request - Date of Register - Date of Acceptance - Date of Joining)

	def after_insert(self):
		update_onboarding_doc(self)

	def set_progress(self):
		"""
		runs: `validate`
		param: PIFSS_for_103 object
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
		# self.check_penality_for_registration()#for setting the 3 dates to identify to whom is the penlty (date of request - Date of Register - Date of Acceptance - Date of Joining)
	def employee_full_name(self):
		"""
		runs: `validate`
		param: PIFSS_for_103 object
		This method fetches the arabic name and arranges it in the print format based on what is filled in employee doctype
		"""
		if self.employee:
			employee = frappe.get_doc('Employee',self.employee)
			if employee.one_fm_first_name_in_arabic and not employee.one_fm_second_name_in_arabic and not employee.one_fm_third_name_in_arabic and employee.one_fm_last_name_in_arabic:
				self.first_name = employee.one_fm_first_name_in_arabic
				self.second_name = employee.one_fm_last_name_in_arabic
				self.third_name = ''
				self.last_name = ''
			elif employee.one_fm_first_name_in_arabic and employee.one_fm_second_name_in_arabic and not employee.one_fm_third_name_in_arabic and employee.one_fm_last_name_in_arabic:
				self.first_name = employee.one_fm_first_name_in_arabic
				self.second_name = employee.one_fm_second_name_in_arabic
				self.third_name = employee.one_fm_last_name_in_arabic
				self.last_name = ''
			elif employee.one_fm_first_name_in_arabic and not employee.one_fm_second_name_in_arabic and employee.one_fm_third_name_in_arabic and employee.one_fm_last_name_in_arabic:
				self.first_name = employee.one_fm_first_name_in_arabic
				self.second_name = employee.one_fm_third_name_in_arabic
				self.third_name = employee.one_fm_last_name_in_arabic
				self.last_name = ''


	def check_employee_fields(self):
		"""
		runs: `validate`
		param: PIFSS_for_103 object
		This method asks for setting mandatory fields upon `request_type`
		`request_type` (eg: End of Service)
		"""
		field_list_in_employee=[]
		if self.request_type == "End of Service":
			field_list_in_employee = [{'Civil ID':'civil_id'},{'Mobile':'mobile'},
				{'Address':'address'},{'Date of Birth':'date_of_birth'},
				{'Nationality':'nationality'},{'PAM Designation':'position'},
				{'Salary':'salary'},{'Relieving Date':'relieving_date'}]
		if self.request_type == "Registration":
			field_list_in_employee = [{'Civil ID':'civil_id'},{'Mobile':'mobile'},
				{'Address':'address'},{'Date of Birth':'date_of_birth'},
				{'Nationality':'nationality'},{'PAM Designation':'position'},
				{'Salary':'salary'}]
		message_detail = '<b style="color:red; text-align:center"> You Need to Set The Missing Data In Employee Doctype</b><br>'
		self.set_mendatory_fields(field_list_in_employee,message_detail)

	def set_grd_values(self):
		"""
		runs: `validate`
		param: PIFSS_for_103 object
		This method is fetching values of grd supervisor or pifss operator from GRD settings
		"""
		if not self.grd_supervisor:
			self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
		if not self.grd_operator:
			self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_pifss")

	def set_date(self):
		"""
		runs: `validate`
		param: PIFSS_for_103 object
		This function is setting today's date for `signature_date` and `employee_signature_date` that are required in the PIFSS 103 print format
		"""
		if not self.signature_date:
			self.signature_date = today()
		if not self.employee_signature_date:
			self.employee_signature_date = today()

	def check_penality_for_registration(self):
		if self.request_type == "Registration":
			if not self.date_of_request:
				if self.status == "Pending by GRD":
					self.date_of_request = today()
			if not self.date_of_registeration:
				if self.status == "Awaiting Response":
					self.date_of_registeration = today()

	def on_submit(self):
		"""
		This method asks operator to fill mandatory fields upon `request_type` to be able to submit

		"""
		if self.workflow_state == "Completed" and self.request_type == "End of Service":
			field_list = [{'Attach Status from PIFSS Website ':'attach_end_of_service_from_pifss_website'}]
			message_detail = '<b style="color:red; text-align:center;">First, You Need to Take Screenshot of {0} Status from <a href="{1}">PIFSS Website</a></b><br>'.format(self.request_type,self.pifss_website)
			self.set_mendatory_fields(field_list,message_detail)

		if self.workflow_state == "Completed" and self.request_type == "Registration":
			field_list = [{'Attach Status from PIFSS Website ':'attach_registration_from_pifss_website'}]
			message_detail = '<b style="color:red; text-align:center;">First, You Need to Take Screenshot of {0} Status from <a href="{1}">PIFSS Website</a></b><br>'.format(self.request_type,self.pifss_website)
			self.set_mendatory_fields(field_list,message_detail)

		self.date_of_acceptance = today()
		# This method will be used to create penalty for operator work delay, but not defined yet by project owner, what have been defined currently is tracking three dates
		# (date_of_request, date_of_registration, date_of_acceptance)
		# and based on these three dates we can create penalty on (employee: delay in providing his/her documents, operator: delay on registering employee on pifss, onboarding user: delay on requesting grd to apply for employee on pifss)
		# self.check_penality()
		update_onboarding_doc(self)
		# self.recall_create_work_permit_new_kuwaiti()

	def on_update(self):
		self.check_workflow_states()
		self.set_work_permit_type()
		self.notify_authorized_signatory()
		self.notify_grd()#notify through erpnext to apply on pifss
		update_onboarding_doc(self)

	def check_workflow_states(self):
		"""
		runs: `on_update`
		param: PIFSS_for_103 object
		This function asks user to set the mandatory fields for each state in workflow states
		"""
		if self.workflow_state == "Form Printed":
			field_list = [{'Request Type':'request_type'},{'Employee':'employee'},{'Company Name':'company_name'}
						,{'Signatory Name':'signatory_name'}]
			self.set_mendatory_fields(field_list)


		if self.workflow_state == "Pending by GRD":
			field_list = [{'Attach 103 Signed Form':'attach_signed_form'}]
			message_detail = '<b style="color:red; text-align:center;">First, You Need to Print The Form and Take Employee Signature</b><br>'
			self.set_mendatory_fields(field_list,message_detail)
			self.date_of_request = today()


		if self.workflow_state == "Awaiting Response":
			if not self.reference_number:
				field_list = [{'PIFSS Reference Number':'reference_number'}]
				message_detail = '<b style="color:red; text-align:center;">First, You Need to Apply for {0} through <a href="{1}" target="_blank">PIFSS Website</a></b><br>'.format(self.request_type,self.pifss_website)
				self.set_mendatory_fields(field_list,message_detail)
			self.date_of_registeration = today()

		if self.workflow_state == "Rejected":
			if not self.reason_of_rejection:
				field_list = [{'Reason Of Rejection':'reason_of_rejection'}]
				self.set_mendatory_fields(field_list)

		if self.workflow_state == "Under Process":
			self.db_set('pifss_is_under_process_on', now_datetime())

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

	def set_work_permit_type(self):
		"""
		runs: `on_update`
		param: PIFSS_for_103 object
		This method set `work_permit_type` upon `request_type`
		"""
		if self.request_type == "End of Service":
			self.db_set('work_permit_type', 'Cancellation')
		if self.request_type == "Registration":
			self.db_set('work_permit_type', 'New Kuwaiti')

	def notify_grd(self):
		"""
		runs: `on_update`
		param: PIFSS_for_103 object
		This method notify operator to apply for PIFSS 103
		"""
		if self.workflow_state == "Pending by GRD":
			page_link = get_url(self.get_url())
			subject = _("PIFSS Form 103 has been created for {0}").format(self.employee_name)
			message = "<p>Please Apply for {0} throught PIFSS Website for {1} <a href='{2}'></a></p>".format(self.request_type,self.employee_name,page_link)
			create_notification_log(subject, message, [self.grd_operator], self)

	def check_penality(self):
		if self.date_of_request and self.date_of_registeration and self.date_of_joining:
			if date_diff(self.date_of_registeration,self.date_of_joining) >= 9 and date_diff(self.date_of_request,self.date_of_joining) < 9:#need to check the other dates as well
				frappe.msgprint(_("Issue Penality for PRO"))
			if date_diff(self.date_of_request,self.date_of_joining) >= 9:
				frappe.msgprint(_("Issue Penality for Employee"))

	def notify_authorized_signatory(self):
		"""
		runs: `on_update`
		param: PIFSS_for_103 object
		This method notifies the authorized signature that his Electronic signature will be used on the currect document.
		"""
		if self.notify_for_signature == 0 and self.user:
			name = frappe.db.get_value('PAM Authorized Signatory Table',{'authorized_signatory_name_arabic':self.signatory_name},['authorized_signatory_name_english'])
			page_link = get_url(self.get_url())
			subject = _("<p>Attention: Your signature will be used on PIFSS Form 103</p>")
			message = "<p>Dear {0},<br>You are requested to sgin on PIFSS Form 103 Record ({1}) for {2}<br>Please note that your E-Signature will be used on PIFSS Form 103 <a href='{3}'></a></p>.".format(name,self.name,self.employee_name,page_link)
			create_notification_log(subject, message, [self.user], self)
			self.db_set('notify_for_signature',1)

	def recall_create_work_permit_new_kuwaiti(self):
		if self.request_type == "Registration":
			work_permit.create_work_permit_new_kuwaiti(self.name,self.employee)


def notify_grd_to_check_under_process_status_on_pifss():
	"""
	runs: `Hooks` everyday at 8am
	This method fetches list of objects having `Awaiting Response` workflow state
	"""
	pifss_103_list = frappe.db.get_list('PIFSS Form 103',{'workflow_state':['=',('Awaiting Response')]},['name','civil_id'])
	notification_reminder(pifss_103_list)

def notification_reminder(pifss_103_list):
	"""
	This method for notifying operator to check the status of the employee on PIFSS website

	Args:
		pifss_103_list ([list of objects]): [list of objects having `Awaiting Response` workflow state]
	"""
	message_list=[]
	grd_user = frappe.db.get_single_value("GRD Settings", "default_grd_operator_pifss")
	grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
	for pifss_103 in pifss_103_list:
		page_link = get_url(pifss_103.get_url())
		message = "<a href='{0}'>{1}</a>".format(page_link, pifss_103.civil_id)
		message_list.append(message)

	if message_list:
		message = "<p>Please Check PIFSS website for PIFSS Form 103 listed below</p><ol>".format()
		for msg in message_list:
			message += "<li>"+msg+"</li>"
		message += "<ol>"
		make(
			subject=_('Awaiting Response PIFSS Form 103'),
			content=message,
			recipients=[grd_user],
			cc=grd_supervisor,
			send_email=True,
		)

@frappe.whitelist()
def get_signatory_name(parent):
	"""
	This method is passing company name to fetch `authorized_signatory_name_arabic` from the child table Authorized Signatory in PIFSS Authorized Signatory Doctype

	Args:
		parent: it is the selected `company_name` to get the Authorized signatory list upon company name

	Returns:
		names: list of authorized signatory arabic names
	"""
	names=[]
	names.append(' ') # To avoid adding the first name in the list as default name
	if parent:
		doc = frappe.get_doc('PIFSS Authorized Signatory',parent)

		for autorized_signatory in doc.authorized_signatory:
			if autorized_signatory.authorized_signatory_name_arabic:
				names.append(autorized_signatory.authorized_signatory_name_arabic)
	return names

@frappe.whitelist()
def get_signatory_user(user_name):
	"""
	This method returns the `user_id` and `signature` of the selected authrized signatorys
	Args:
		user_name: Authorized Signatory Arabic name

	Returns:
		user: Authorized Signatory user id to notify him later on
		signature: Authorized Electronic signature
	"""
	user,signature = frappe.db.get_value('PAM Authorized Signatory Table',{'authorized_signatory_name_arabic':user_name},['user','signature'])
	return user,signature

@frappe.whitelist()
def create_103_form(param, dateofrequest,rt,cn,sn,sf):
	"""
	This Method runs when operator re-apply for a rejected employee, so it will create new record with some common data.
	Args:
		param: employee (eg: HR-EMP-00001)
		dateofrequest: The auto fill date once HR User submit the record to GRD, means requested date won't change when re-applying for a rejected employee
		rt: `request_type` (eg: End of Service)
		cn: `company_name`
		sn: `signatory_name`
		sf: `attach_signed_form`

	Returns:
		[type]: [description]
	"""
	pifss = frappe.new_doc('PIFSS Form 103')
	pifss.request_type = rt
	pifss.company_name = cn
	pifss.signatory_name = sn
	pifss.employee = param
	pifss.date_of_request = dateofrequest
	pifss.attach_signed_form = sf
	pifss.insert()
	pifss.workflow_state = 'Form Printed'
	pifss.save()
	pifss.workflow_state = 'Pending by GRD'
	pifss.save()
	frappe.db.commit()
	frappe.msgprint("New Record Created")
	return pifss

@frappe.whitelist()
def create_103_form_for_onboarding(employee, onboard_employee):
	"""
	This Method will be called in onboarding once pressing `PIFSS Form 103` button and this button will show for Kuwaiti employee only

	Args:
		employee: (eg: HR-EMP-00001)
		onboard_employee: link to onboard_employee table (eg: EMP-ONB-2021-00021)

	Returns:
		pifss: PIFSS Form 103 object
	"""
	pifss = frappe.new_doc('PIFSS Form 103')
	pifss.request_type = "Registration"
	pifss.employee = employee
	pifss.onboard_employee = onboard_employee
	pifss.save(ignore_permissions=True)
	return pifss
