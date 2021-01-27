# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class MOM(Document):
	def validate(self):
		attendees_count = 0
		for attendee in self.attendees[:]:
			if attendee.attended_meeting:
				attendees_count = attendees_count + 1
			else:
				self.remove(attendee)

		if(attendees_count < 1):
			frappe.throw(_("Please check the attendees present."))

		if self.issues == "Yes" and len(self.action) < 1:
			frappe.throw(_("Please add Action taken to the table."))


	def after_insert(self):
		if self.issues == "Yes" and len(self.action) > 0:
			for issue in self.action:
				op_task = frappe.new_doc("Task")
				op_task.subject = issue.subject
				op_task.description = issue.description
				op_task.priority = issue.priority
				op_task.project = self.project 
				op_task.save()
			frappe.db.commit()

@frappe.whitelist()

def review_last_mom(mom,site):
	last_mom = frappe.db.get_list('MOM', filters={ 
		'name': ['!=', mom ],
		'site': site
	
	},
	order_by='date desc',
	page_length=1

	)
	if len(last_mom)>0:
		return frappe.get_doc('MOM',last_mom[0].name)

@frappe.whitelist()
def review_pending_actions(project):
	filters = {'project': project}
	data = frappe.db.sql("""
	SELECT *
	FROM `tabTask` 
	WHERE (project = %(project)s) AND (status != 'Completed' AND status != 'Cancelled')
	""", filters, as_dict=1)
	return data

