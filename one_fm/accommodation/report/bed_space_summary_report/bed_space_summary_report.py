# Copyright (c) 2013, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.query_builder import DocType

# Bed.status values that mean the bed exists but cannot be offered to anyone.
UNAVAILABLE_STATUSES = ("Under Maintenance", "Blocked")

# Bed.status values that mean the bed is reserved but not yet occupied.
# NOTE: the Bed DocType spells it "Temporarily Booked"; the old report looked
# for "Temporary Booked", which never matched a single row.
BOOKED_STATUS = "Booked"
TEMPORARILY_BOOKED_STATUS = "Temporarily Booked"


def execute(filters=None):
	columns, data = get_columns(), get_data(filters or {})
	data.append(get_total_row(data))
	return columns, data


def get_columns():
	return [
		_("Code/Rerf") + ":Link/Accommodation:100",
		_("Accommodation Name") + ":Data:180",
		_("Total Bed") + ":Data:100",
		_("Occupied") + ":Data:120",
		_("Occupied Temporarily") + ":Data:180",
		_("Booked") + ":Data:100",
		_("Temporary Booked") + ":Data:150",
		_("Unavailable") + ":Data:120",
		_("Vacant") + ":Data:100",
		_("Occupied %") + ":Percent:100",
		_("Vacant %") + ":Percent:100",
	]


def get_data(filters):
	"""One row per Accommodation, every column from the same two live sources."""
	return summarise(
		get_beds(filters), get_occupied_bed_map(filters), get_accommodation_names()
	)


def summarise(beds, occupancy, accommodation_names):
	"""Classify each bed into exactly one column.

	Every column is derived from the same two live sources - the Bed list and
	the open check-in list - so the row always adds up:

		Total = Occupied + Occupied Temporarily + Booked + Temporary Booked
		        + Unavailable + Vacant

	Vacant is deliberately *not* read from the stored ``Bed.status`` field.
	That field is only maintained by the check-in/check-out controller and
	silently goes stale (e.g. a check-out that cannot reset the bed), which is
	what made Total - Occupied disagree with the Vacant column.
	"""
	# Seed every accommodation so one with no (matching) bed still gets a row.
	summary = {name: new_counts() for name in accommodation_names}

	for bed in beds:
		row = summary.setdefault(bed.accommodation, new_counts())
		row["total"] += 1

		occupancy_type = occupancy.get(bed.name)
		if occupancy_type == "permanent":
			row["occupied"] += 1
		elif occupancy_type == "temporary":
			row["occupied_temp"] += 1
		elif bed.status == BOOKED_STATUS:
			row["booked"] += 1
		elif bed.status == TEMPORARILY_BOOKED_STATUS:
			row["temp_booked"] += 1
		elif bed.status in UNAVAILABLE_STATUSES:
			row["unavailable"] += 1
		else:
			# No open check-in and not reserved or blocked - the bed is free,
			# whatever the stored status happens to say.
			row["vacant"] += 1

	data = []
	for accommodation in sorted(summary, key=lambda d: d or ""):
		row = summary[accommodation]
		total = row["total"]
		occupied_percent = ((row["occupied"] + row["occupied_temp"]) * 100) / total if total else 0
		vacant_percent = (row["vacant"] * 100) / total if total else 0

		data.append([
			accommodation,
			accommodation_names.get(accommodation),
			total,
			row["occupied"],
			row["occupied_temp"],
			row["booked"],
			row["temp_booked"],
			row["unavailable"],
			row["vacant"],
			occupied_percent,
			vacant_percent,
		])

	return data


def new_counts():
	return {
		"total": 0,
		"occupied": 0,
		"occupied_temp": 0,
		"booked": 0,
		"temp_booked": 0,
		"unavailable": 0,
		"vacant": 0,
	}


def get_beds(filters):
	"""All active beds, with the filters exposed on the report."""
	Bed = DocType("Bed")

	query = (
		frappe.qb.from_(Bed)
		.select(Bed.name, Bed.accommodation, Bed.status)
		.where(Bed.disabled == 0)
	)

	if filters.get("bed_space_type"):
		query = query.where(Bed.bed_space_type == filters.get("bed_space_type"))

	if filters.get("gender"):
		query = query.where(Bed.gender == filters.get("gender"))

	return query.run(as_dict=True)


def get_occupied_bed_map(filters):
	"""Map of bed -> "permanent" | "temporary" for every bed with an open check-in.

	A bed counts as occupied when an inward check-in exists that has not been
	checked out. Draft check-ins are included because accommodation check-ins
	are, in practice, never submitted - excluding them would report the whole
	estate as empty.

	Permanent vs. temporary is decided by whether the signed accommodation
	policy is attached to the check-in.
	"""
	Bed = DocType("Bed")
	Checkin = DocType("Accommodation Checkin Checkout")

	query = (
		frappe.qb.from_(Checkin)
		.inner_join(Bed).on(Bed.name == Checkin.bed)
		.select(Checkin.bed, Checkin.attach_print_accommodation_policy)
		.where(Bed.disabled == 0)
		.where(Checkin.type == "IN")
		.where(Checkin.checked_out == 0)
		.where(Checkin.docstatus < 2)
	)

	if filters.get("bed_space_type"):
		query = query.where(Bed.bed_space_type == filters.get("bed_space_type"))

	if filters.get("gender"):
		query = query.where(Bed.gender == filters.get("gender"))

	occupancy = {}
	for d in query.run(as_dict=True):
		# A bed with more than one open check-in is still one occupied bed.
		# Treat it as permanent if any of those check-ins carries the policy.
		if d.attach_print_accommodation_policy:
			occupancy[d.bed] = "permanent"
		else:
			occupancy.setdefault(d.bed, "temporary")

	return occupancy


def get_accommodation_names():
	Accommodation = DocType("Accommodation")

	return {
		d.name: d.accommodation
		for d in frappe.qb.from_(Accommodation).select(Accommodation.name, Accommodation.accommodation).run(as_dict=True)
	}


def get_total_row(data):
	totals = [sum(row[i] for row in data) for i in range(2, 9)]
	total_beds = totals[0]
	total_occupied, total_occupied_temp, total_vacant = totals[1], totals[2], totals[6]

	total_occupied_percent = (total_occupied + total_occupied_temp) * 100 / total_beds if total_beds else 0
	total_vacant_percent = total_vacant * 100 / total_beds if total_beds else 0

	return ["Total", ""] + totals + [total_occupied_percent, total_vacant_percent]
