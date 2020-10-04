# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_years

class MedicalInsurance(Document):
	def validate(self):
		self.valid_work_permit_exists()
		self.update_end_date()
		self.validate_no_of_application()
		if not self.grd_supervisor:
			self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")

	def validate_no_of_application(self):
		if self.category == "Group" and len(self.items) > 20:
			frappe.throw(_("More than 20 Application is not Possible"))

	def update_end_date(self):
		if self.category == 'Individual' and self.no_of_years and self.no_of_years > 0 and self.start_date:
			self.end_date = add_years(self.start_date, self.no_of_years)
		elif self.category == 'Group':
			for item in self.items:
				if item.no_of_years and item.no_of_years > 0 and item.start_date:
					item.end_date = add_years(item.start_date, item.no_of_years)

	def valid_work_permit_exists(self):
		# TODO: Check valid work permit exists for the employee
		pass


@frappe.whitelist()
def get_employee_data_from_civil_id(civil_id):
	employee_id = frappe.db.exists('Employee', {'one_fm_civil_id': civil_id})
	if employee_id:
		return frappe.get_doc('Employee', employee_id)

# Notify GRD Operator at 9:00 am
def notify_grd_operator_draft_new_mi():
	# Medical Insurance will create whenever the Work Permit is Done
    pass



def email_notification_to_grd_user(grd_user, mi_list, reminder_indicator, action, cc=[]):
	recipients = {}

	for mi in mi_list:
		page_link = get_url("/desk#Form/Medical Insurance/"+mi.name)
		message = "<a href='{0}'>{1}</a>".format(page_link, mi.name)
		if mi[grd_user] in recipients:
			recipients[mi[grd_user]].append(message)
		else:
			recipients[mi[grd_user]]=[message]

	if recipients:
		for recipient in recipients:
			message = "<p>Please {0} Medical Insurance listed below</p><ol>".format(action)
			for msg in recipients[recipient]:
				message += "<li>"+msg+"</li>"
			message += "<ol>"
			frappe.sendmail(
				recipients=[recipient],
				cc=cc,
				subject=_('{0} Medical Insurance'.format(action)),
				message=message,
				header=['Medical Insurance Reminder', reminder_indicator],
			)
			to_do_to_grd_users(_('{0} Medical Insurance'.format(action)), message, recipient)

def to_do_to_grd_users(subject, description, user):
	frappe.get_doc({
		"doctype": "ToDo",
		"subject": subject,
		"description": description,
		"owner": user,
		"date": today()
	}).insert(ignore_permissions=True)
