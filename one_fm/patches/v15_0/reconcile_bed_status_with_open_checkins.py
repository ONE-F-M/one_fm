"""HD-1806399: bring Bed.status back in line with the open check-ins.

The Bed Space Summary Report read its Vacant column from the stored Bed.status
field while reading Occupied live from Accommodation Checkin Checkout, so the
two never reconciled: Total minus Occupied came to 220 where the report printed
212 vacant.

Bed.status drifted because the check-out branch of
AccommodationCheckinCheckout.update_bed_details only freed a bed when
bed.employee still matched the employee being checked out. Where that link had
been cleared or overwritten the bed stayed flagged occupied for good - fourteen
beds on production, the oldest stuck since May 2025, seven of them with no
employee at all.

The controller no longer skips that reset and the report no longer trusts the
field. This clears the beds that drifted while it did, so the stored status
agrees with the check-ins from here on. Occupancy is the source of truth: a bed
with no open inward check-in is free, whatever its status says, and a bed with
one is not.
"""

import frappe
from frappe.query_builder import DocType

OCCUPIED_STATUSES = ("Occupied", "Occupied Temporarily")


def execute():
	occupied_beds = get_beds_with_open_checkin()

	Bed = DocType("Bed")
	flagged_occupied = {
		d.name
		for d in (
			frappe.qb.from_(Bed)
			.select(Bed.name)
			.where(Bed.disabled == 0)
			.where(Bed.status.isin(OCCUPIED_STATUSES))
		).run(as_dict=True)
	}

	# Flagged occupied, nobody actually checked in: free the bed.
	for bed in sorted(flagged_occupied - occupied_beds):
		# update_modified=False: this is a correction of our own bookkeeping,
		# not somebody editing the bed.
		frappe.db.set_value(
			"Bed", bed, {"status": "Vacant", "employee": ""}, update_modified=False
		)

	frappe.db.commit()


def get_beds_with_open_checkin():
	"""Beds holding an inward check-in that has not been checked out.

	Draft check-ins count - accommodation check-ins are not submitted in
	practice, so excluding them would empty the whole estate.
	"""
	Bed = DocType("Bed")
	Checkin = DocType("Accommodation Checkin Checkout")

	return {
		d.bed
		for d in (
			frappe.qb.from_(Checkin)
			.inner_join(Bed).on(Bed.name == Checkin.bed)
			.select(Checkin.bed)
			.where(Bed.disabled == 0)
			.where(Checkin.type == "IN")
			.where(Checkin.checked_out == 0)
			.where(Checkin.docstatus < 2)
		).run(as_dict=True)
	}
