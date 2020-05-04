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
