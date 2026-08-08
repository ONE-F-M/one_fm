import frappe
from frappe import _
from frappe.utils import cint, flt, getdate


def set_naming_series(doc, method):
	"""Set the Vehicle naming series based on the vehicle category before insert."""
	if doc.one_fm_vehicle_category == "Leased":
		series = "VHL-L-.####"
	elif doc.one_fm_vehicle_category == "Subcontractor":
		series = "VHL-S-.####"
	else:
		series = "VHL-.####"

	doc.naming_series = series


def validate_vehicle_branding(doc, method):
	"""Validate branding details on Vehicle save."""
	validate_branding_expiration_dates(doc)
	validate_branding_image_required(doc)


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
