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

		if self.type == "OUT" and self.leave_application:
			self.reapply_leave_application_assignment_rules()

	def on_cancel(self):
		if self.type == "IN" and self.checkin_reference:
			frappe.db.set_value("Accommodation Leave Movement", self.checkin_reference, "checked_out", 0)

		if self.type == "OUT" and self.leave_application:
			self.reapply_leave_application_assignment_rules()

	def reapply_leave_application_assignment_rules(self):
		"""Set accommodation checkout flag and re-evaluate assignment rules.

		Assignment rules only fire on the target document's own save/update events.
		When an Accommodation Leave Movement is submitted or cancelled, the Leave
		Application is not saved, so its unassign_condition is never checked.

		This method:
		1. Sets/clears the custom_accommodation_checked_out flag on the Leave Application
		2. Explicitly calls the assignment rule engine to evaluate unassign/assign conditions
		"""
		from frappe.automation.doctype.assignment_rule.assignment_rule import apply

		try:
			checked_out = 1 if self.docstatus == 1 else 0
			frappe.db.set_value(
				"Leave Application",
				self.leave_application,
				"custom_accommodation_checked_out",
				checked_out,
			)
			apply(doctype="Leave Application", name=self.leave_application)
		except Exception:
			frappe.log_error(
				message=frappe.get_traceback(),
				title="Error Reapplying Assignment Rules for Leave Application",
			)

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
def has_linked_checkin(checkout_name: str) -> bool:
	"""
	Returns True if a non-cancelled IN record already exists that is linked to
	the given OUT document via the checkin_reference field.

	Used by the client script to decide whether to render the "Create > Check In"
	button.  The check covers Draft (docstatus=0) and Submitted (docstatus=1)
	records so that the button is hidden as soon as the IN record is created,
	not only after it is submitted.
	"""
	if not checkout_name:
		return False

	AlmDoctype = frappe.qb.DocType("Accommodation Leave Movement")
	result = (
		frappe.qb.from_(AlmDoctype)
		.select(AlmDoctype.name)
		.where(AlmDoctype.checkin_reference == checkout_name)
		.where(AlmDoctype.type == "IN")
		.where(AlmDoctype.docstatus != 2)  # exclude cancelled records
		.limit(1)
	).run(as_dict=True)

	return bool(result)


@frappe.whitelist()
def make_checkin_from_checkout(source_name: str):
	"""
	Maps fields from an 'OUT' Accommodation Leave Movement to a new 'IN' one.
	"""
	if has_linked_checkin(source_name):
		frappe.throw(frappe._("A linked check-in already exists for this check-out."))

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
