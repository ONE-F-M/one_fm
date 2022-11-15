# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate
from frappe.model.document import Document

class RosterProjectionChecker(Document):

	def validate(self):
		if not self.check_date:
			self.check_date = getdate()
		self.fill_items()

	def fill_items(self):
		contract = frappe.get_doc("Contracts", self.contract)
		for item in contract.items:
			if item.subitem_group == "Service":
				ps = 
