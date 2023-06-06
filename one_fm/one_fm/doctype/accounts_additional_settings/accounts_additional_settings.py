# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AccountsAdditionalSettings(Document):
	def onload(self):
		self.set_onload('collection_officer_role_exists', frappe.db.exists("Role", {"role_name": 'Collection Officer'}))
	def validate(self):
		if self.customer_advance_account:
			account_type = frappe.get_value("Account",self.customer_advance_account,'account_type')
			if account_type != "Receivable":
				frappe.throw("Customer Advance Account must be of type Receivable")

@frappe.whitelist()
def get_options_for_assign_collection_officer_on_workflow_sate():
	from one_fm.one_fm.utils import get_workflow_sates
	states = []
	workflow_states = get_workflow_sates('Sales Invoice')
	for state in workflow_states:
		states.append(state.state)
	return states
