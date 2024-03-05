# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ONEFMGeneralSetting(Document):
	def validate(self):
		if self.has_value_changed('extend_user_permissions'):
			#Clear Cache and Force Frappe to get updated permissions
			frappe.cache.delete_key('user_permissions')