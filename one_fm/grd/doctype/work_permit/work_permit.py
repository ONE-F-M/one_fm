# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today, add_days, get_url

class WorkPermit(Document):
	def validate(self):
		if not self.grd_supervisor:
			self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")

	def on_submit(self):
		self.validate_mandatory_fields_on_submit()
		self.db_set('work_permit_submitted', 'Yes')
		self.db_set('work_permit_submitted_by', frappe.session.user)
		self.db_set('work_permit_submitted_on', today())

	def on_update_after_submit(self):
		if self.work_permit_approved == 'Yes' and self.work_permit_status == 'Draft':
			self.db_set('work_permit_status', 'Submitted')
			self.db_set('work_permit_approved_by', frappe.session.user)
			self.db_set('work_permit_approved_on', today())

	def validate_mandatory_fields_on_submit(self):
		field_list = [{"Company Trade Name in Arabic":"company_trade_name_arabic"}, {"Contract File Number":"contract_file_number"},
			{"Authorized Signatory Name in Arabic":"authorized_signatory_name_arabic"}, {"PAM File Number":"pam_file_number"},
			{"Issuer Number":"issuer_number"}, {"First Name":"first_name"}, {"First Name in Arabic":"first_name_in_arabic"},
			{"Last Name":"last_name"}, {"Last Name in Arabic":"last_name_in_arabic"}, {'Date of Birth':'date_of_birth'},
			{'Gender':'gender'}, {'Religion':'religion'}, {'Marital Status':'marital_status'}, {'Nationality':'nationality'},
			{'Passport Type':'passport_type'}, {'Passport Number':'passport_number'}, {'Pratical Qualification':'pratical_qualification'}, {'Religion':'religion'},
			{'CIVIL ID':'civil_id'}, {'PAM Designation':'pam_designation'}, {'Salary':'salary'}, {'Salary Type':'religion'},
			{'Duration of Work Permit':'duration_of_work_permit'}, {'Visa Reference Number':'visa_reference_number'},
			{'Date of Issuance of Visa':'date_of_issuance_of_visa'}, {'Date of Entry in Kuwait':'date_of_entry_in_kuwait'},
			{'Documents Required':'documents_required'}]#Check the second and third name or no need? | salary Type | religion been mentioned twice
# Checking if both second and third names are filled to add the arabic fields
		if self.second_name and not self.second_name_in_arabic:
			field_list.extend({'Second Name in Arabic': 'second_name_in_arabic'})
		if self.third_name and not self.third_name_in_arabic:
			field_list.extend({'Third Name in Arabic': 'third_name_in_arabic'})

		mandatory_fields = []
		for fields in field_list:
			for field in fields:
				if not self.get(fields[field]):
					mandatory_fields.append(field)

		if len(mandatory_fields) > 0:
			message = 'Mandatory fields required in Work Permit to Submit<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' + mandatory_field +'</li>'
			message += '</ul>'
			frappe.throw(message)

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

@frappe.whitelist()
# will craete a list of work permit based on employee renewals
def get_employee_data_for_work_permit(employee_name):
	# employee = frappe.get_doc("Employee", employee_name)
	work_permit_exist = frappe.db.exists('Work Permit', {'employee': employee_name, 'docstatus': 1})
	return work_permit_exist

# Create Draft Work Permit Daily   +++++++++ will add the code for the list that needs renewal from Pre RPR
def create_work_permit_renewal():
    date_after_14_days = add_days(today(), 14)
    # Get employee list
    query = """
        select
            *
        from
            tabEmployee
        where
            active=1 and one_fm_work_permit is NOT NUL and
            (one_fm_renewal_date is NOT NULL and one_fm_work_permit_renewal_date = %(date_after_14_days))
    """
    employee_list = frappe.db.sql(query.format(), {'date_after_14_days': date_after_14_days}, as_dict=True)
	# employee_entries = frappe.db.get_list('Employee',
	# 						filters={
	# 							'expiry_residency_date': ['between',(first_day,Last_day)],
	# 							'status': 'Active'
	# 						},
	# 						fields=['one_fm_civil_id','employee_name','employee_id','expiry_residency_date']
							
							)
    for employee in employee_list:
        create_work_permit(employee)

def create_work_permit(employee):
	if employee.one_fm_work_permit:
		# Renew Work Permit: 1. Renew Kuwaiti Work Permit, 2. Renew Overseas Work Permit
		work_permit = frappe.get_doc('Work Permit', employee.one_fm_work_permit)
		new_work_permit = frappe.copy_doc(work_permit)
		work_permit.insert()
	else:
		# Create New Work Permit: 1. New Overseas, 2. New Kuwaiti, 3. Work Transfer
		# work_permit = frappe.new_doc('Work Permit')
		pass

# Notify GRD Operator at 8:30 am
def notify_grd_operator_draft_new_work_permit():
    pass

# Notify GRD Operator at 9:00 am
def work_permit_notify_first_grd_operator():
	work_permit_notify_grd_operator('yellow')

# Notify GRD Operator at 9:30 am
def work_permit_notify_again_grd_operator():
	work_permit_notify_grd_operator('red')

# Notify GRD Supervisor at 4:00 pm
def work_permit_notify_grd_supervisor_to_approve():
	work_permit_notify_grd_supervisor('yellow')

# Notify GRD Supervisor Daily
def work_permit_notify_grd_supervisor_to_approve():
	work_permit_notify_grd_supervisor('red')

# Notify GRD Supervisor 8:30 am after 2 Days of Approval //use it for 7 days++++++
def work_permit_notify_grd_supervisor_check_approval():
	work_permit_notify_grd_supervisor_to_check_approval('yellow', add_days(today(), -2))

# Notify GRD Supervisor 9:00 am after 3 Days of Approval
def work_permit_notify_again_grd_supervisor_check_approval():
	work_permit_notify_grd_supervisor_to_check_approval('red', add_days(today(), -3))

# Notify Finance Dept. 4:00 pm - Work Permit is Approved by the Govt. and do Payments
def work_permit_notify_finance_dept_for_payment():
	# Get work permit list
	filters = {
		'docstatus': 1, 'work_permit_submitted': 'Yes', 'work_permit_approved': 'Yes', 'work_permit_status': 'Approved',
		'payment_transferred_from_finance_dept': 0
	}
	work_permit_list = frappe.db.get_list('Work Permit', filters, ['name', 'notify_finance_user'])
	email_notification_to_grd_user('grd_supervisor', work_permit_list, reminder_indicator, 'Take action on Payment Transfer Requested for ')

def work_permit_notify_grd_supervisor_to_check_approval(reminder_indicator, date_x_days_before):
	# Get work permit list
	filters = {
		'docstatus': 1, 'work_permit_submitted': 'Yes', 'work_permit_approved': 'Yes', 'work_permit_status': 'Submitted',
		'work_permit_approved_on': getdate(date_x_days_before)
	}
	work_permit_list = frappe.db.get_list('Work Permit', filters, ['name', 'grd_supervisor'])
	email_notification_to_grd_user('grd_supervisor', work_permit_list, reminder_indicator, 'Check Approval status of ')

def work_permit_notify_grd_operator(reminder_indicator):
	# Get work permit list
	filters = {'docstatus': 0, 'work_permit_submitted': 'No', 'reminded_grd_operator': 0}
	if reminder_indicator == 'red':
		filters['reminded_grd_operator'] = 1
		filters['reminded_grd_operator_again'] = 0

	work_permit_list = frappe.db.get_list('Work Permit', filters, ['name', 'grd_operator', 'grd_supervisor'])

	cc = [work_permit_list[0].grd_supervisor] if reminder_indicator == 'red' else []
	email_notification_to_grd_user('grd_operator', work_permit_list, reminder_indicator, 'Submit', cc)

	# Update reminded grd operator to 1
	if reminder_indicator == 'red':
		field = 'reminded_grd_operator_again'
	elif reminder_indicator == 'yellow':
		field = 'reminded_grd_operator'

	frappe.db.set_value("Work Permit", filters, field, 1)

def work_permit_notify_grd_supervisor(reminder_indicator):
	# Get work permit list
	filters = {'docstatus': 1, 'work_permit_submitted': 'Yes', 'work_permit_approved': 'No'}
	work_permit_list = frappe.db.get_list('Work Permit', filters, ['name', 'grd_supervisor'])
	email_notification_to_grd_user('grd_supervisor', work_permit_list, reminder_indicator, 'Approve')

def email_notification_to_grd_user(grd_user, work_permit_list, reminder_indicator, action, cc=[]):
	recipients = {}

	for work_permit in work_permit_list:
		page_link = get_url("/desk#Form/Work Permit/"+work_permit.name)
		message = "<a href='{0}'>{1}</a>".format(page_link, work_permit.name)
		if work_permit[grd_user] in recipients:
			recipients[work_permit[grd_user]].append(message)
		else:
			recipients[work_permit[grd_user]]=[message]

	if recipients:
		for recipient in recipients:
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
