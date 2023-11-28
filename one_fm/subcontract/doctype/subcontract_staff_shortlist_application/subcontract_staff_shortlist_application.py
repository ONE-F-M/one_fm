# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class SubcontractStaffShortlistApplication(Document):
	def on_submit(self):
		if self.workflow_state == 'Approved':
			self.create_subcontract_onboard_employee()

	def create_subcontract_onboard_employee(self):
		if self.subcontract_staff_shortlist_detail:
			for staff_shortlist in self.subcontract_staff_shortlist_detail:
				doclist = get_mapped_doc("Subcontract Staff Shortlist Detail", staff_shortlist.name, {
					"Subcontract Staff Shortlist Detail": {
						"doctype": "Onboard Subcontract Employee",
						"field_map": {
							"parent": "subcontract_staff_shortlist",
							"name": "staff_shortlist_detail"
						}
					}
				})
				doclist.flags.ignore_mandatory = True
				doclist.save(ignore_permissions=True)
