# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ObjectMaintenanceChecklist(Document):
	def validate(self):
		self.resequence_tasks()

	def resequence_tasks(self):
		"""Auto-resequence the 'No.' field (sequence_no) to maintain a clean SOP order.

		Runs on every save to handle additions, removals, and reordering.
		"""
		for idx, row in enumerate(self.object_maintenance_checklist_items, start=1):
			row.sequence_no = idx
