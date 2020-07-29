# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url

class ERFRequest(Document):
	def validate(self):
		if self.is_new():
			self.department_manager = frappe.session.user

	def on_submit(self):
		self.notify_approver()

	def notify_approver(self):
		erf_approver = False
		if self.reason_for_request == "UnPlanned":
			erf_approver = frappe.db.get_value('Hiring Settings', None, 'unplanned_erf_approver')
		else:
			erf_approver = frappe.db.get_value('Hiring Settings', None, 'erf_approver')
		if erf_approver:
			send_email(self, [erf_approver])
			frappe.msgprint(_('{0}, Will Notified By Email.').format(frappe.db.get_value('User', erf_approver, 'full_name')))

	def on_update_after_submit(self):
		self.validate_with_erf()
		if self.status in ['Accepted', 'Declined']:
			send_email(self, self.department_manager)
			frappe.msgprint(_('{0}, Will Notified By Email.').format(frappe.db.get_value('User', self.department_manager, 'full_name')))

	def validate_with_erf(self):
		erf = frappe.db.exists('ERF', {'erf_request': self.name, 'docstatus': ['<', 2]})
		if erf:
			frappe.throw(_("""An ERF <b><a href="#Form/ERF/{0}">{0}</a></b> is exists against this request, \
				Can not change this ERF Request.!""").format(erf, self.name))

def trigger_employee_exit(doc, method):
	if doc.status == 'Left' and not exists_erf_request_on_employee_exit(doc):
		create_erf_request(doc.doctype, doc.name)

def exists_erf_request_on_employee_exit(employee):
	return frappe.db.exists('Employee', {'name': employee.name, 'docstatus': 1})

def create_erf_request(trigger_dt, trigger_dn):
	trigger_doc = frappe.get_doc(trigger_dt, trigger_dn)
	erf_request = frappe.new_doc('ERF Request')
	erf_request.reference_type = trigger_dt
	erf_request.reference_name = trigger_dn
	if trigger_dt == 'Employee':
		erf_request.reason_for_request = 'Employee Exit'
		erf_request.number_of_candidates_required = 1
		erf_request.department = trigger_doc.department
		erf_request.designation = trigger_doc.designation

	erf_request.save(ignore_permissions=True)
	frappe.msgprint(_('ERF Request {0} is created').format(erf_request.name), alert=True)

def send_email(doc, recipients):
	page_link = get_url("/desk#Form/ERF Request/" + doc.name)
	message = "<p>Please Review the ERF Request <a href='{0}'>{1}</a> and take action.</p>".format(page_link, doc.name)
	if doc.status == 'Accepted':
		if frappe.db.exists('Email Template', {'name': 'Approved ERF Request'}):
			email_template = frappe.get_doc("Email Template", 'Approved ERF Request')
			if email_template:
				context = doc.as_dict()
				message += frappe.render_template(email_template.response, context)
	if doc.status == 'Declined' and doc.reason_for_decline:
		message = "<p>ERF Request <a href='{0}'>{1}</a> is Declined due to {2}</p>".format(page_link, doc.name, doc.reason_for_decline)
	frappe.sendmail(
		recipients= recipients,
		subject='{0} ERF Request for {1}'.format(doc.status, doc.designation),
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name
	)

def get_manager_users(role='HR Manager'):
	query = """
		select
			parent
		FROM
			`tabHas Role`
		WHERE
			role=%(role)s AND parent!='Administrator' AND parent IN (SELECT email FROM tabUser WHERE enabled=1)
	"""
	return frappe.db.sql_list(query,{"role": role})
