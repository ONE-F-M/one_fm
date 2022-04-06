# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AccommodationAssetandConsumable(Document):
	def before_insert(self):
		if self.type == 'Return':
			self.naming_series = 'AACR-.YYYY.-'
		else:
			self.naming_series = 'AACI-.YYYY.-'
		if not self.employee and self.employee_id:
			employee = frappe.db.get_value('Employee', {'employee_id': self.employee_id})
			if employee:
				self.employee = employee

	def set_assets_and_consumables_details(self):
		assets_and_consumables = False
		if self.employee:
			if self.type == "Issue" and self.designation:
				assets_and_consumables = get_accomodation_assets_and_consumables_details(self.designation, self.project)
				if not assets_and_consumables:
					frappe.msgprint(msg = 'No Designation Profile - Assets Found',
				       title = 'Warning',
				       indicator = 'red'
				    )
			# elif self.type == "Return":
			# 	uniforms = get_items_to_return(self.employee)

		if assets_and_consumables:
			if assets_and_consumables['assets']:
				for asset in assets_and_consumables['assets']:
					uniform_issue_ret = self.append('assets')
					uniform_issue_ret.asset_item = asset.item
					uniform_issue_ret.item_name = asset.item_name
					# uniform_issue_ret.actual_quantity = uniform.quantity
					uniform_issue_ret.quantity = asset.quantity
					uniform_issue_ret.uom = asset.uom
					uniform_issue_ret.expire = frappe.utils.add_months(self.issued_on, 12)
					# if self.type == "Issue":
					# 	args = {
					# 		'item_code': uniform.item,
					# 		'doctype': self.doctype,
					# 		'buying_price_list': frappe.defaults.get_defaults().buying_price_list,
					# 		'currency': frappe.defaults.get_defaults().currency,
					# 		'name': self.name,
					# 		'qty': uniform.quantity,
					# 		'company': self.company,
					# 		'conversion_rate': 1,
					# 		'plc_conversion_rate': 1
					# 	}
					# 	uniform_issue_ret.rate = get_item_details(args).price_list_rate
					# 	if self.issued_on:
					# 		uniform_issue_ret.expire_on = frappe.utils.add_months(self.issued_on, 12)
					# elif self.type == "Return":
					# 	uniform_issue_ret.expire_on = uniform.expire_on
					# 	uniform_issue_ret.rate = uniform.rate
					# 	uniform_issue_ret.issued_item_link = uniform.issued_item_link
					# 	uniform_issue_ret.issued_on = uniform.issued_on

			if assets_and_consumables['consumables']:
				for consumable in assets_and_consumables['consumables']:
					uniform_issue_ret = self.append('consumables')
					uniform_issue_ret.item = consumable.item
					uniform_issue_ret.item_name = consumable.item_name
					uniform_issue_ret.quantity = consumable.quantity
					uniform_issue_ret.uom = consumable.uom
					uniform_issue_ret.expire = frappe.utils.add_months(self.issued_on, 12)

def get_accomodation_assets_and_consumables_details(designation_id, project_id=''):
	filters = {'designation': designation_id, 'project': project_id}
	query = """
		select
			name
		from
			`tabDesignation Profile`
		where
			designation=%(designation)s {condition}
	"""

	condition = "and project IS NULL"
	if project_id:
		condition = "and project=%(project)s"

	profile_id = frappe.db.sql(query.format(condition=condition), filters, as_dict=1)
	if not profile_id and project_id:
		condition = "and project IS NULL"
		profile_id = frappe.db.sql(query.format(condition=condition), filters, as_dict=1)
	if profile_id and profile_id[0]['name']:
		profile = frappe.get_doc('Designation Profile', profile_id[0]['name'])
		assets = profile.accommodation_assets if profile.accommodation_assets else False
		consumables = profile.accommodation_consumables if profile.accommodation_consumables else False
		return {'assets': assets, 'consumables': consumables}
	return False
