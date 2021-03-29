# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document
import frappe 
class RPRList(Document):
	pass


	# Begin_of_next_month = frappe.datetime.add_months(today(), 1) #add n month to a date
	# LastDay_of_next_month = frappe.datetime.month_end(Begin_of_next_month)# return the last date of the month of the given date
	# DateList_of_NextMonth = frappe.datime.get_day_diff(Begin_of_next_month, LastDay_of_next_month)#NO USE FOR IT
	
	# def get_employee_list(employee):
	# #what should I check to run this process??
		
	# 	for employee in frappe.get_all('employee', filters={'status':'Active'}, fields=['employee_number','employee_name','Employee-one_fm_civil_id','expiry_residency_date']):
	# 			if employee.expiry_residency_date in DateList_of_NextMonth
	# 					#rpr_list = employee.append('rpr_list')
	# 					rpr_list.employee_full_name = employee.employee_name
	# 					rpr_list.employee_number = employee.employee_number
	# 					rpr_list.employee_civil_id = employee.Employee-one_fm_civil_id
	# 					rpr_list.employee_residency_expiry_date = employee.expiry_residency_date
	# 			employee.save(ignore_permissions = True)

# 	def notify_employee_list(self):
# 		page_link = get_url("/desk#Form/DocType/RPR/List" + self.name)
# 			message = "<p>Please Review and Renewal or Extend the Request list <a href='{0}'>{1}</a>Please finalize it within 7 days.</p>".format(page_link, self.name)
# 			subject = '{0} Renewal or Extend the Request list'.format(self.status)
# 			send_email(self, [self.request_for_material_approver], message, subject)
# 			create_notification_log(subject, message, [self.request_for_material_approver], self)

# def send_email(doc, recipients, message, subject):
# 	frappe.sendmail(
# 		recipients= recipients,
# 		subject=subject,
# 		message=message,
# 		reference_doctype=doc.doctype,
# 		reference_name=doc.name
# 	)

# def create_notification_log(subject, message, for_users, reference_doc):
# 	for user in for_users:
# 		doc = frappe.new_doc('Notification Log')
# 		doc.subject = subject
# 		doc.email_content = message
# 		doc.for_user = user
# 		doc.document_type = reference_doc.doctype
# 		doc.document_name = reference_doc.name
# 		doc.from_user = reference_doc.modified_by
# 		doc.insert(ignore_permissions=True)

						