import frappe
from frappe import _
from frappe.utils import cint, flt, getdate


def validate_vehicle_branding(doc, method):
	"""Validate branding details on Vehicle save."""
	validate_branding_expiration_dates(doc)
	validate_branding_image_required(doc)


def passenger_capacity(seats, includes_driver_seat) -> int:
	"""How many passengers a vehicle may legally carry (WI-002000).

	Whether ``seats`` counts the driver differs from vehicle to vehicle, so it is
	the fleet team's answer per record rather than a rule in the code: a 5-seater
	that includes the driver carries 4, a 30-seater that does not carries 30.

	The one place the arithmetic lives, so the Vehicle form, the schedule canvas,
	the route optimizer and the Route Plan save can never disagree about how full
	a bus is.
	"""
	return max(cint(seats) - (1 if cint(includes_driver_seat) else 0), 0)


def set_max_passenger_capacity(doc, method=None):
	"""Keep Max Passenger Capacity in step with seats and the driver-seat flag.

	The field is read-only on the form (AC6), so it is only ever derived here —
	on every save, which is what makes editing either input enough to correct it.
	"""
	doc.custom_max_passenger_capacity = passenger_capacity(
		doc.get("seats"), doc.get("custom_includes_driver_seat")
	)


def validate_custodian_history(doc, method):
	"""Validate and recompute the Vehicle Custodian History table on save.

	The table rows are appended by the client script whenever a new custodian
	takes over, snapshotting the vehicle's current mileage into
	``mileage_at_handover``. Here we (1) block chronologically out-of-order
	handovers and (2) recompute ``mileage_covered`` server-side so the values
	are correct regardless of the client state.
	"""
	rows = doc.get("custom_vehicle_custodian_history") or []
	if not rows:
		return

	enforce_handover_chronology(rows)
	recompute_mileage_covered(doc, rows)


def enforce_handover_chronology(rows):
	"""Prevent saving if a row's handover date precedes the previous row's."""
	previous_date = None
	for row in rows:
		if not row.handover_date:
			continue

		current_date = getdate(row.handover_date)
		if previous_date and current_date < previous_date:
			frappe.throw(
				_("Row #{0}: Handover Date {1} cannot be earlier than the previous custodian's Handover Date {2}.").format(
					row.idx,
					frappe.format(current_date, {"fieldtype": "Date"}),
					frappe.format(previous_date, {"fieldtype": "Date"}),
				)
			)
		previous_date = current_date


def recompute_mileage_covered(doc, rows):
	"""Recalculate mileage covered for every custodian row.

	Past rows: next row's mileage at handover minus this row's.
	Last (active) row: the vehicle's current mileage minus this row's.
	"""
	current_mileage = flt(doc.one_fm_milage)
	last_index = len(rows) - 1

	for index, row in enumerate(rows):
		if index < last_index:
			covered = flt(rows[index + 1].mileage_at_handover) - flt(row.mileage_at_handover)
		else:
			covered = current_mileage - flt(row.mileage_at_handover)

		row.mileage_covered = cint(covered)


def validate_branding_expiration_dates(doc):
	"""Ensure expiration date is later than both application date and issue date."""
	expiration_date = doc.custom_branding_registration_expiration_date
	if not expiration_date:
		return

	expiration = getdate(expiration_date)

	application_date = doc.custom_branding_application_date
	if application_date and getdate(application_date) >= expiration:
		frappe.throw(
			_("Branding Registration Expiration Date must be later than Branding Application Date.")
		)

	issue_date = doc.custom_branding_registration_issue_date
	if issue_date and getdate(issue_date) >= expiration:
		frappe.throw(
			_("Branding Registration Expiration Date must be later than Branding Registration Issue Date.")
		)


def validate_branding_image_required(doc):
	"""Require branding image when branding registration issue date is set."""
	if doc.custom_branding_registration_issue_date and not doc.custom_branding_image:
		frappe.throw(
			_("Branding Image is required when Branding Registration Issue Date is set.")
		)
