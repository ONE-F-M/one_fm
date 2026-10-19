# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""HD-1806399: the Bed Space Summary Report's columns have to add up to Total.

The report used to read Occupied live off the open check-ins and Vacant off the
stored Bed.status field, so a bed that drifted out of sync was counted in
neither column: production showed 1641 beds with 1421 occupied and 212 vacant,
thirteen short of the 220 the reporter arrived at by subtraction.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.accommodation.report.bed_space_summary_report.bed_space_summary_report import (
	get_columns,
	get_total_row,
	summarise,
)

NAME, LABEL, TOTAL, OCCUPIED, OCCUPIED_TEMP, BOOKED, TEMP_BOOKED, UNAVAILABLE, VACANT = range(9)

NAMES = {"ACC-TEST": "Test Accommodation"}


def bed(name, status="Vacant", accommodation="ACC-TEST"):
	return frappe._dict(name=name, status=status, accommodation=accommodation)


class TestBedSpaceSummaryReport(FrappeTestCase):
	def row(self, beds, occupancy=None):
		return summarise(beds, occupancy or {}, NAMES)[0]

	def test_every_bed_lands_in_exactly_one_column(self):
		"""The arithmetic the reporter did by hand has to hold on every row."""
		beds = [
			bed("B1"),
			bed("B2", status="Occupied Temporarily"),
			bed("B3", status="Booked"),
			bed("B4", status="Temporarily Booked"),
			bed("B5", status="Under Maintenance"),
			bed("B6", status="Blocked"),
		]
		row = self.row(beds, {"B1": "temporary", "B2": "permanent"})

		self.assertEqual(row[TOTAL], 6)
		self.assertEqual(
			row[TOTAL],
			row[OCCUPIED] + row[OCCUPIED_TEMP] + row[BOOKED] + row[TEMP_BOOKED]
			+ row[UNAVAILABLE] + row[VACANT],
		)

	def test_a_bed_with_no_open_checkin_is_vacant_whatever_its_status_says(self):
		"""The fourteen beds stuck on production were flagged occupied with nobody
		checked in - reading the stored field hid them from the Vacant count."""
		row = self.row([bed("B1", status="Occupied Temporarily"), bed("B2", status="Occupied")])

		self.assertEqual(row[VACANT], 2)
		self.assertEqual(row[OCCUPIED] + row[OCCUPIED_TEMP], 0)

	def test_a_bed_with_an_open_checkin_is_occupied_whatever_its_status_says(self):
		"""The inverse drift: one production bed read Vacant with a live check-in on it."""
		row = self.row([bed("B1", status="Vacant")], {"B1": "temporary"})

		self.assertEqual(row[OCCUPIED_TEMP], 1)
		self.assertEqual(row[VACANT], 0)

	def test_an_occupied_bed_is_never_also_counted_as_booked(self):
		"""Occupancy wins over the reservation statuses - a booked bed somebody has
		since moved into is one occupied bed, not one of each."""
		row = self.row([bed("B1", status="Booked")], {"B1": "permanent"})

		self.assertEqual(row[OCCUPIED], 1)
		self.assertEqual(row[BOOKED], 0)

	def test_the_temporary_booking_status_is_spelt_the_way_the_bed_spells_it(self):
		"""The Bed DocType offers "Temporarily Booked". The old report counted
		"Temporary Booked", which matched nothing, so the column was always zero."""
		row = self.row([bed("B1", status="Temporarily Booked")])

		self.assertEqual(row[TEMP_BOOKED], 1)
		self.assertEqual(row[VACANT], 0)

	def test_an_accommodation_with_no_beds_still_gets_a_row(self):
		row = self.row([])

		self.assertEqual(row[NAME], "ACC-TEST")
		self.assertEqual(row[TOTAL], 0)

	def test_percentages_do_not_divide_by_zero_on_an_empty_accommodation(self):
		row = self.row([])

		self.assertEqual(row[-2:], [0, 0])

	def test_the_total_row_sums_the_accommodations(self):
		data = summarise(
			[bed("B1"), bed("B2", accommodation="ACC-OTHER")],
			{"B1": "temporary"},
			{"ACC-TEST": "Test Accommodation", "ACC-OTHER": "Other Accommodation"},
		)
		total_row = get_total_row(data)

		self.assertEqual(total_row[NAME], "Total")
		self.assertEqual(total_row[TOTAL], 2)
		self.assertEqual(total_row[OCCUPIED_TEMP], 1)
		self.assertEqual(total_row[VACANT], 1)

	def test_the_total_row_is_as_wide_as_the_columns(self):
		"""An Unavailable column was added - a total row of the old width would
		push every percentage one cell to the left."""
		data = summarise([bed("B1")], {}, NAMES)

		self.assertEqual(len(get_total_row(data)), len(get_columns()))
		self.assertEqual(len(data[0]), len(get_columns()))
