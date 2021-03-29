# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe.utils import cstr
from frappe.utils import datetime
from frappe.utils import nowdate
from frappe.model.document import Document
from frappe.utils import today, add_days, get_url#extra
from datetime import date
from dateutil.relativedelta import relativedelta
from frappe.utils import get_datetime, add_to_date, getdate



class PreRPR(Document):
	#pass
	def on_submit(self):
		self.validate_mandatory_fields_on_submit()

	def validate_mandatory_fields_on_submit(self):
		field_list = [{'Renewal or extend':'renewal_or_extend'}, {'RPR List':'rpr_list'}]
		
		mandatory_fields = []
		mandatory_fields_reqd = False
		for item in self.rpr_list:#each item in the rpr list row
			if not item.renewal_or_extend:#column not filled
				mandatory_fields_reqd = True
				mandatory_fields.append(item.idx)


		if len(mandatory_fields) > 0:
			message = 'Mandatory fields required in Pre RPR to Submit<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' +'<p> fill the renewal or extend field </p>'+ str(mandatory_field) +'</li>'
			message += '</ul>'
			frappe.throw(message)
		

def create_pre_rpr():
	doc = frappe.new_doc('Pre RPR')
	doc.posting_date = nowdate()
	print(doc)
	today = date.today()
	first_day = today.replace(day=1) + relativedelta(months=1)
	Last_day = today.replace(day=31) + relativedelta(months=1)
	print(first_day)
	print(Last_day)
	get_employee_entries(doc,first_day,Last_day)
	# doc.save(ignore_permission=True)

def get_employee_entries(doc,first_day,Last_day):
#def get_employee_entries(doc):	
	#employee_doctypes = [{'dt': 'employee', 'employee_residency_expiry_date': 'expiry_residency_date'}]
	#res = []
	#for employee_doctype in employee_doctypes:
	#Available_employees = frappe.get_all('employee', filters={'status':'Active'}, fields=['employee_number','employee_name','one_fm_civil_id','expiry_residency_date'])
	#for employee in Available_employees:
		#res += list(employee)	
	
	# Test sql 1#
	# query = """ 
	# 		select one_fm_civil_id, employee_name, employee_id, expiry_residency_date from `tabEmployee`
	# 		where expiry_residency_date between {0} and {1}
	# 		"""
	# employee_entries = frappe.db.sql(query.format(first_day,Last_day))
	# print(employee_entries)

	# Test sql 2#
	# employee_entries = frappe.db.sql(""" 
	# 		select one_fm_civil_id, employee_name, employee_id, expiry_residency_date from `tabEmployee`
	# 		where expiry_residency_date between {0} and {1}
	# 		""", as_dict=1)
	
	# Test other solution than sql #
	employee_entries = frappe.db.get_list('Employee',
							filters={
								'expiry_residency_date': ['between',(first_day,Last_day)],
								'status': 'Active'
							},
							fields=['one_fm_civil_id','employee_name','employee_id','expiry_residency_date']
							
							)
		
	#res += list(employee_entries)	
	doc.set("rpr_list", [])
	for d in employee_entries:
		#print(d)
		doc.append("rpr_list", {
			"employee_civil_id": d.one_fm_civil_id,
			"employee_full_name": d.employee_name,
			"employee_number": d.employee_id,
			"employee_residency_expiry_date": d.expiry_residency_date# TypeError: 'datetime.date' object is not iterable
		})
	doc.save()

# @frappe.whitelist()
# # Notify HR manager 9:00 am after 7 Days of System notification
# def rpr_list_notify_again_hr_supervisor_check_approval():
# 	rpr_list_notify_hr_supervisor_to_check_approval('red', add_days(today(), -7))

# def rpr_list_notify_hr_supervisor_to_check_approval(reminder_indicator, date_x_days_before):
# 	# Get rpr list
# 	filters = {
# 		'docstatus': 1, 'hr_approval': 'No','posting_date': getdate(date_x_days_before)
# 	}
# 	rpr_list = frappe.db.get_list('Pre RPR', filters, ['posting_date','rpr_list'])
# 	email_notification_to_hr_user('hr_supervisor', rpr_list, reminder_indicator, 'Check renewal or extend of the emplyee list')

# def email_notification_to_hr_user(grd_user, work_permit_list, reminder_indicator, action, cc=[]):
# 	recipients = {}

# 	for work_permit in work_permit_list:
# 		page_link = get_url("/desk#Form/Work Permit/"+work_permit.name)
# 		message = "<a href='{0}'>{1}</a>".format(page_link, work_permit.name)
# 		if work_permit[grd_user] in recipients:
# 			recipients[work_permit[grd_user]].append(message)
# 		else:
# 			recipients[work_permit[grd_user]]=[message]

# 	if recipients:
# 		for recipient in recipients:
# 			message = "<p>Please {0} Work Permit listed below</p><ol>".format(action)
# 			for msg in recipients[recipient]:
# 				message += "<li>"+msg+"</li>"
# 			message += "<ol>"
# 			frappe.sendmail(
# 				recipients=[recipient],
# 				cc=cc,
# 				subject=_('{0} Work Permit'.format(action)),
# 				message=message,
# 				header=['Work Permit Reminder', reminder_indicator],
# 			)
# 			to_do_to_grd_users(_('{0} Work Permit'.format(action)), message, recipient)

# def to_do_to_grd_users(subject, description, user):
# 	frappe.get_doc({
# 		"doctype": "ToDo",
# 		"subject": subject,
# 		"description": description,
# 		"owner": user,
# 		"date": today()
# 	}).insert(ignore_permissions=True)