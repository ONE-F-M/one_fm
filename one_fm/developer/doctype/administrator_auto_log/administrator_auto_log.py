# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AdministratorAutoLog(Document):

	def on_trash(self):
		frappe.throw("This document cannot be deleted.")
