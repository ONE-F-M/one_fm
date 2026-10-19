# Copyright (c) 2023, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

# each export makes about 6 Sheets API calls and Google allows 60 per minute per account
MAX_HOURLY_EXPORTS = 5


class GoogleSheetDataExport(Document):
	def validate(self):
		self.validate_hourly_limit()

	def validate_hourly_limit(self):
		if not self.enable_auto_update or self.update_frequency != "Hourly":
			return
		hourly = frappe.db.count(
			self.doctype,
			{"enable_auto_update": 1, "update_frequency": "Hourly", "name": ["!=", self.name]},
		)
		if hourly >= MAX_HOURLY_EXPORTS:
			frappe.throw(
				_("Only {0} exports can update hourly. Set this one to Daily or use Export Sheet.").format(
					MAX_HOURLY_EXPORTS
				)
			)
