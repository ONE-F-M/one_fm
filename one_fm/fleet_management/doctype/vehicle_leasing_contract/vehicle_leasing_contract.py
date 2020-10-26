# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class VehicleLeasingContract(Document):
	def create_vehicle(self, args):
		vehicle = frappe.new_doc("Vehicle")
		for d in args:
			vehicle.set(d, args[d])
		vehicle.one_fm_vehicle_category = 'Leased'
		# vehicle.one_fm_vehicle_leasing_contract = self.vehicle_leasing_contract
		vehicle.make = self.make
		vehicle.model = self.model
		vehicle.one_fm_vehicle_type = self.vehicle_type
		vehicle.one_fm_year_of_made = self.year_of_made
		vehicle.save(ignore_permissions=True)
		child = self.append('vehicles', {})
		child.license_plate = args['license_plate']
		child.make = self.make
		child.model = self.model
		child.vehicle_type = self.vehicle_type
		child.purpose_of_use = args['one_fm_purpose_of_use']
		self.save()
