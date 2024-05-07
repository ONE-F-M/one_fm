# Copyright (c) 2024, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class UserAppService(Document):
	
	def validate(self):
		self.validate_user_services()

	def validate_user_services(self):
		"""Validate that the user service is not duplicate"""
		servies_detail_map = {} 
		for i in self.service_detail:
			det = i.service+ ' ' +i.service_group
			if servies_detail_map.get(det):
				servies_detail_map[det] += 1
			else:
				servies_detail_map[det] = 1

			if  servies_detail_map[det] > 1:
				frappe.throw(f" {i.service} in group {i.service_group} already exists")