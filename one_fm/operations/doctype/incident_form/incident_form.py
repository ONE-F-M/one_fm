# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class IncidentForm(Document):
	def validate(self):
		if not self.operation_manager:
			operation_manager = frappe.db.get_single_value("Operation Settings", "default_operation_manager")
			if operation_manager:
				self.operation_manager = operation_manager
			else:
				frappe.throw(_("Set Default Operation Manager in Operation Settings"))
