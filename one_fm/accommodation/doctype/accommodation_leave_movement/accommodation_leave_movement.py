# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class AccommodationLeaveMovement(Document):
	def autoname(self):
		if self.type == "OUT":
			self.naming_series = "HR-ALM-OUT-.YYYY.-"
		else:
			self.naming_series = "HR-ALM-IN-.YYYY.-"
		
		from frappe.model.naming import make_autoname
		self.name = make_autoname(self.naming_series)

	def on_submit(self):
		if self.type == "IN" and self.checkin_reference:
			frappe.db.set_value("Accommodation Leave Movement", self.checkin_reference, "checked_out", 1)

	def on_cancel(self):
		if self.type == "IN" and self.checkin_reference:
			frappe.db.set_value("Accommodation Leave Movement", self.checkin_reference, "checked_out", 0)

@frappe.whitelist()
def get_last_active_checkin(employee: str):
	"""
	Fetches the most recent active check-in for an employee from 'Accommodation Checkin Checkout'.
	Active check-in is defined as type 'IN' and 'checked_out' is 0.
	"""
	if not employee:
		return None
		
	checkins = frappe.get_all("Accommodation Checkin Checkout",
		filters={
			"employee": employee,
			"type": "IN",
			"checked_out": 0
		},
		fields=["bed", "accommodation", "floor", "accommodation_unit", "accommodation_space"],
		order_by="checkin_checkout_date_time desc, creation desc",
		limit=1
	)
	
	return checkins[0] if checkins else None

@frappe.whitelist()
def make_checkin_from_checkout(source_name: str):
	"""
	Maps fields from an 'OUT' Accommodation Leave Movement to a new 'IN' one.
	"""
	target_doc = get_mapped_doc(
		"Accommodation Leave Movement",
		source_name,
		{
			"Accommodation Leave Movement": {
				"doctype": "Accommodation Leave Movement",
				"validation": {
					"docstatus": ["=", 1],
					"type": ["=", "OUT"]
				}
			}
		},
		ignore_permissions=False,
	)
	
	target_doc.type = "IN"
	target_doc.checkin_reference = source_name
	target_doc.checkin_checkout_date_time = frappe.utils.now_datetime()
	
	return target_doc
