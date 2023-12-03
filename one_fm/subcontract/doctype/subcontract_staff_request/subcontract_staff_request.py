# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError
from frappe.model.document import Document


class SubcontractStaffRequest(Document):
    
    def on_update(self):
        if self.workflow_state == "Pending":
            operations_manager = frappe.db.get_single_value("Operation Settings", "default_operation_manager")
            if operations_manager:
                self.approver = operations_manager
                try:
                    add_assignment({
					'doctype': 'Subcontract Staff Request',
					'name': self.name,
					'assign_to': [operations_manager],
					'description': _(f'Please review the Subcontract Staff Request {self.name}'),
                    "assignment_rule": ""
				})
                except DuplicateToDoError:
                    frappe.message_log.pop()
                    pass
                