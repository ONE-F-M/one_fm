# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AccountsAdditionalSettings(Document):
	pass

@frappe.whitelist()
def get_options_for_assign_collection_officer_on_workflow_sate():
	from one_fm.one_fm.utils import get_workflow_sates
	states = []
	workflow_states = get_workflow_sates('Sales Invoice')
	for state in workflow_states:
		states.append(state.state)
	return states
