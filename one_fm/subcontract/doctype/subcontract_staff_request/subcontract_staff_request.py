# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError
from frappe.model.document import Document
from one_fm.utils import (workflow_approve_reject)


class SubcontractStaffRequest(Document):
    
    def on_update(self):
        if self.workflow_state == "Rejected":
            last_doc = self.get_doc_before_save()
            if last_doc and last_doc.get('workflow_state') != self.workflow_state:
                workflow_approve_reject(self)
            
        if self.workflow_state == "Pending":
            operations_manager = frappe.db.get_single_value("Operation Settings", "default_operation_manager")
            if operations_manager:
                self.approver = operations_manager
                try:
                    add_assignment({
					'doctype': 'Subcontract Staff Request',
					'name': self.name,
					'assign_to': [operations_manager],
					'description': _(f'Please review the Subcontract Staff Request {self.name}')
				})
                except DuplicateToDoError:
                    frappe.message_log.pop()
                    pass
                