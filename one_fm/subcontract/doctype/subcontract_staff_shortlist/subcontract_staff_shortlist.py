# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from one_fm.utils import (workflow_approve_reject)


class SubcontractStaffShortlist(Document):
	def on_update(self):
		last_doc = self.get_doc_before_save()
		if self.workflow_state in ["Draft","Rejected",'Approved']:
			if last_doc and last_doc.get('workflow_state') != self.workflow_state:
				if self.workflow_state =='Draft':
					workflow_approve_reject(self,message = f"Your Subcontract Staff Shortlist {self.name} has been returned to Draft Workflow State. Click '<a href='{self.get_url()}'>Here</a>' to view")
				else:
					workflow_approve_reject(self)
	def on_submit(self):
		if self.workflow_state == 'Approved':
			self.create_subcontract_onboard_employee()

	def create_subcontract_onboard_employee(self):
		if self.subcontract_staff_shortlist_detail:
			for staff_shortlist in self.subcontract_staff_shortlist_detail:
				def set_missing_values(source, target):
					target.department = self.department
					target.date_of_joining = self.expected_date_of_joining
					target.salary = 0.00
					target.employment_type = frappe.db.get_single_value('Hiring Settings', 'subcontract_employment_type')

				doclist = get_mapped_doc("Subcontract Staff Shortlist Detail", staff_shortlist.name, {
					"Subcontract Staff Shortlist Detail": {
						"doctype": "Onboard Subcontract Employee",
						"field_map": {
							"parent": "subcontract_staff_shortlist",
							"name": "staff_shortlist_detail"
						}
					}
				}, None, set_missing_values)
				doclist.flags.ignore_mandatory = True
				doclist.save(ignore_permissions=True)
