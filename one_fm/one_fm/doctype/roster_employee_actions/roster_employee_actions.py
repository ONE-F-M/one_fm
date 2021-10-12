# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class RosterEmployeeActions(Document):
	def autoname(self):
		self.name = self.start_date + "|" + self.end_date + "|" + self.action_type + self.supervisor

		
