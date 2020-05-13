# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class ERFRequest(Document):
	def on_submit(self):
		# TODO: Notify the HR Manager through email
		frappe.msgprint(_('HR Manager Will Notified By Email.'))

	def on_update_after_submit(self):
		self.validate_with_erf()
		if self.status == 'Accepted':
			# TODO: Notify the Department Manager or Hiring Manager through email
			frappe.msgprint(_('Department Manager Will Notified By Email.'))
		elif self.status == 'Declined':
			# TODO: Notify the Department Manager or Hiring Manager through email, with reason Decline
			frappe.msgprint(_('Department Manager Will Notified By Email.'))

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
