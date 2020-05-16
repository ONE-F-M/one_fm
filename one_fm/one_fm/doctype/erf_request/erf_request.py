# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class ERFRequest(Document):
	def on_submit(self):
		manager_users = get_manager_users()
		name_of_users = []
		for manager_user in manager_users:
			name_of_users.append(frappe.db.get_value('User', manager_user, 'full_name'))
		if manager_users:
			send_email(self, manager_users)
			frappe.msgprint(_('{0}, Will Notified By Email.').format(name_of_users[0]))

	def on_update_after_submit(self):
		# self.validate_with_erf()
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
	message = '<p> Please Review the ERF Request {0} and take action.</p>'.format(doc.name)
	if doc.status == 'Declined' and doc.reason_for_decline:
		message = '<p> ERF Request {0} is Declined due to {1}.</p>'.format(doc.name, doc.reason_for_decline)
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
