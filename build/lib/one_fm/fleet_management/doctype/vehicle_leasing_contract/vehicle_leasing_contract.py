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
		# vehicle.vehicle_leasing_contract =
		# vehicle.vehicle_leasing_details =
		vehicle.one_fm_vehicle_type = vehicle_detail.vehicle_type
		vehicle.one_fm_year_of_made = vehicle_detail.year_of_made
		vehicle.save(ignore_permissions=True)
		update_leasing_cotract_with_vehicle_list(vehicle, self)

def after_insert_vehicle(doc, method):
	if doc.vehicle_leasing_contract and doc.vehicle_leasing_details:
		lc = frappe.get_doc('Vehicle Leasing Contract', doc.vehicle_leasing_contract)
		update_leasing_cotract_with_vehicle_list(doc, lc)

def update_leasing_cotract_with_vehicle_list(vehicle, lc):
	child = lc.append('vehicles', {})
	child.vehicle_id = vehicle.name
	child.license_plate = vehicle.license_plate
	child.make = vehicle.make
	child.model = vehicle.model
	child.vehicle_type = vehicle.one_fm_vehicle_type
	lc.save()

@frappe.whitelist()
def get_vehicle_from_leasing_contract(vehicle_detail):
	return frappe.get_doc('Vehicle Leasing Contract Item', vehicle_detail)
