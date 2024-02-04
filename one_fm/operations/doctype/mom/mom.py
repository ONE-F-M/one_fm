# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from json import loads

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
				if not issue.subject:
					op_task.subject = issue.description[:30]
				else:
					op_task.subject = issue.subject
				op_task.description = issue.description
				op_task.priority = issue.priority
				op_task.project = self.project 
				op_task.save(ignore_permissions=True)
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


@frappe.whitelist()
def fetch_designation_of_users(list_of_users: list = []):
	try:
		return frappe.db.sql("""
							SELECT employee_name, designation from `tabEmployee`
							WHERE user_id IN %s
							""",(tuple(loads(list_of_users)), ) ,as_dict=1)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Error encountered while fetching users designation (MOM)")
     