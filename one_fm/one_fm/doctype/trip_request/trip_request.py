# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

# Maps a Source Doctype to the fieldname on that doctype whose value should be
# copied into the Trip Request's Destination Location. Source doctypes not
# listed here (e.g. "Client Interview Shortlist") carry no location, so the
# Destination Location is left empty for the dispatcher to fill in manually.
SOURCE_DESTINATION_FIELD_MAP = {
	"Fingerprint Appointment": "service_location",
	"Medical Appointment": "service_location",
}


def resolve_destination_location(source_doctype: str, source_reference: str) -> str | None:
	"""Return the destination location text for the given source document.

	Returns None when the source doctype is not mapped, the mapped field does
	not exist on the source doctype, or the source record has no value there.
	"""
	if not source_doctype or not source_reference:
		return None

	fieldname = SOURCE_DESTINATION_FIELD_MAP.get(source_doctype)
	if not fieldname:
		return None

	# Guard against a mapped field that no longer exists on the source doctype.
	if not frappe.get_meta(source_doctype).has_field(fieldname):
		return None

	return frappe.db.get_value(source_doctype, source_reference, fieldname) or None


@frappe.whitelist()
def get_destination_location(source_doctype: str, source_reference: str) -> str | None:
	"""Whitelisted resolver used by the Trip Request form to auto-fill the
	Destination Location once a Source Reference is selected."""
	if not source_doctype or not source_reference:
		return None

	# Only expose data the user is allowed to read on the source document.
	if not frappe.has_permission(source_doctype, "read", doc=source_reference):
		frappe.throw(
			_("You do not have permission to read {0} {1}.").format(
				_(source_doctype), source_reference
			),
			frappe.PermissionError,
		)

	return resolve_destination_location(source_doctype, source_reference)


class TripRequest(Document):
	def validate(self):
		self.set_destination_location()
		self.validate_passengers()
		self.calculate_total_headcount()

	def set_destination_location(self):
		"""Server-side fallback that fills Destination Location from the source
		document when it has not already been set (e.g. via the form or API)."""
		if self.destination_location:
			return

		destination = resolve_destination_location(
			self.source_doctype, self.source_reference
		)
		if destination:
			self.destination_location = destination

	def validate_passengers(self):
		"""Ensure at least one passenger has been added to the trip request.

		A Trip Request with no passengers has nothing to transport, so we
		block the save with a clear, translatable message.
		"""
		if not self.transport_request_passenger:
			frappe.throw(
				_("Please add at least one employee to the passenger list."),
				title=_("No Passengers Added"),
			)

	def calculate_total_headcount(self):
		"""Populate the read-only Total Headcount from the passenger table."""
		self.total_headcount = len(self.transport_request_passenger)

	def on_submit(self):
		"""Fragment the request into per-camp shipment demand cards.

		Passengers living in different camps have different physical pickup
		points, so a single multi-passenger request is split — clustered strictly
		by accommodation_camp — into one Outward + one Return shipment per camp.
		"""
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			generate_shipments_from_trip_request,
		)

		generate_shipments_from_trip_request(self)

	def on_cancel(self):
		"""Withdraw the still-Unassigned camp cards generated for this request.

		Cards already Assigned to a Route Plan are deliberately left untouched.
		"""
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			remove_unassigned_shipments_for_trip_request,
		)

		remove_unassigned_shipments_for_trip_request(self.name)
