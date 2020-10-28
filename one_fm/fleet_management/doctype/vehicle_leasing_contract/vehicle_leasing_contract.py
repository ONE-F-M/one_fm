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
			if d != 'vd':
				vehicle.set(d, args[d])
		vehicle_detail = frappe.get_doc('Vehicle Leasing Contract Item', args['vd'])
		vehicle.one_fm_vehicle_category = 'Leased'
		vehicle.make = vehicle_detail.make
		vehicle.model = vehicle_detail.model
		vehicle.one_fm_vehicle_type = vehicle_detail.vehicle_type
		vehicle.one_fm_year_of_made = vehicle_detail.year_of_made
		vehicle.save(ignore_permissions=True)
		child = self.append('vehicles', {})
		child.license_plate = args['license_plate']
		child.make = vehicle_detail.make
		child.model = vehicle_detail.model
		child.vehicle_type = vehicle_detail.vehicle_type
		child.purpose_of_use = args['one_fm_purpose_of_use']
		self.save()
