# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002091 backfill: the actual headcounts on every PAM licence sector row.

The arithmetic itself is WI-002094/002099/002135's and is tested with the controller. What
is tested here is the backfill's own two decisions - where the sector each designation
belongs to is read from, and which rows it refuses to touch.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.pam_license_details.pam_license_details import (
	EXEMPT_SECTOR,
	count_workers,
	derived_figures,
)
from one_fm.patches.v15_0.backfill_pam_license_sector_headcounts import (
	RATIO_DECISION_FIELD,
	fill_designation_sectors,
	mapped_sectors,
	recount_every_sector_row,
)

SEEDED = "WI-002091-BF-"


def _designation(suffix, stated=None, sector=None):
	name = SEEDED + suffix
	doc = frappe.new_doc("PAM Designation List")
	doc.name = name
	doc.designation_name_english = name
	doc.set(RATIO_DECISION_FIELD, stated)
	doc.occupational_sector = sector
	doc.db_insert()
	return name


def _clear():
	frappe.db.delete("PAM Designation List", {"name": ["like", SEEDED + "%"]})


class TestTheSectorIsReadFromTheColumnThatHasIt(FrappeTestCase):
	"""The Link the counting code reads is empty on every designation on this site; the
	sector is on the same record under an Arabic Select nobody joined to."""

	def setUp(self):
		_clear()
		self.sector = frappe.db.get_value("Occupational Sector", {"name": ["!=", EXEMPT_SECTOR]}, "name")
		if not self.sector:
			self.skipTest("no Occupational Sector records on this site")

	def tearDown(self):
		_clear()

	def test_a_blank_link_is_filled_from_the_select(self):
		name = _designation("A", stated=self.sector)

		fill_designation_sectors()

		self.assertEqual(
			frappe.db.get_value("PAM Designation List", name, "occupational_sector"), self.sector
		)

	def test_a_sector_somebody_has_already_set_is_left_alone(self):
		"""Only blanks are filled, so a correction made by hand survives the patch."""
		other = frappe.db.get_value(
			"Occupational Sector", {"name": ["not in", [self.sector, EXEMPT_SECTOR]]}, "name"
		)
		if not other:
			self.skipTest("needs two non-exempt Occupational Sectors")

		name = _designation("B", stated=self.sector, sector=other)

		fill_designation_sectors()

		self.assertEqual(frappe.db.get_value("PAM Designation List", name, "occupational_sector"), other)

	def test_a_value_naming_no_sector_record_is_not_written(self):
		"""A Link pointing at nothing is worse than a blank one: the count that reads it
		would fail rather than come back empty."""
		name = _designation("C", stated="WI-002091 no such sector")

		fill_designation_sectors()

		self.assertFalse(frappe.db.get_value("PAM Designation List", name, "occupational_sector"))

	def test_a_designation_with_nothing_stated_is_not_written(self):
		name = _designation("D")

		fill_designation_sectors()

		self.assertFalse(frappe.db.get_value("PAM Designation List", name, "occupational_sector"))

	def test_it_reports_how_many_it_filled(self):
		_designation("E", stated=self.sector)
		_designation("F", stated=self.sector)
		# Neither of these is fillable.
		_designation("G")
		_designation("H", stated="WI-002091 no such sector")

		self.assertGreaterEqual(fill_designation_sectors(), 2)

	def test_running_it_twice_fills_nothing_the_second_time(self):
		_designation("I", stated=self.sector)
		fill_designation_sectors()

		self.assertEqual(fill_designation_sectors(), 0)


class TestWhichRowsItRefusesToTouch(FrappeTestCase):
	"""A sector no designation maps to can only ever count zero, whatever the licence
	holds. Writing that over a figure somebody has would be the patch erasing a number
	rather than filling one in."""

	def setUp(self):
		_clear()
		# A licence with sector rows on it, not simply the first one with a number: a
		# licence nobody has configured has nothing for this patch to touch, and picking
		# one would skip every test here while looking like a pass.
		self.licence = next(
			(
				name
				for name in frappe.get_all(
					"PAM License Details",
					filters={"civil_id_number_for_licensing": ["is", "set"]},
					pluck="name",
				)
				if frappe.get_doc("PAM License Details", name).pam_license_stats
			),
			None,
		)
		if not self.licence:
			self.skipTest("no configured PAM License Details on this site")

	def tearDown(self):
		_clear()

	def _a_row_in_an_unmapped_sector(self):
		"""Chosen rather than taken first: the licence's rows are mostly in sectors that do
		map, and a test that happened to land on one of those would pass without ever
		reaching the rule it is about."""
		fill_designation_sectors()
		mapped = mapped_sectors()

		# Read off the parent rather than queried: frappe.get_all on a child table refuses
		# a bare parent filter, and comes back empty rather than saying so.
		for row in frappe.get_doc("PAM License Details", self.licence).pam_license_stats:
			if row.occupational_sector and row.occupational_sector not in mapped:
				return row

		return None

	def test_a_row_in_an_unmapped_sector_that_already_has_a_figure_is_left_alone(self):
		row = self._a_row_in_an_unmapped_sector()
		if not row:
			self.skipTest("every sector on this licence has designations mapped to it")

		frappe.db.set_value(
			"PAM License Stats", row.name, "national_number_of_workers", "99", update_modified=False
		)

		recount_every_sector_row()

		self.assertEqual(
			frappe.db.get_value("PAM License Stats", row.name, "national_number_of_workers"), "99"
		)

	def test_the_same_row_is_filled_when_it_is_blank(self):
		"""The other half of the rule, and the one production needs: the guard is against
		erasing a figure, not against writing one. Every sector row on the live site is
		blank, so this is the path the patch will actually take there."""
		row = self._a_row_in_an_unmapped_sector()
		if not row:
			self.skipTest("every sector on this licence has designations mapped to it")

		frappe.db.set_value(
			"PAM License Stats",
			row.name,
			{"national_number_of_workers": "", "expatriate_number_of_workers": ""},
			update_modified=False,
		)

		recount_every_sector_row()

		self.assertEqual(
			frappe.db.get_value("PAM License Stats", row.name, "national_number_of_workers"), "0"
		)

	def test_the_figures_it_does_write_are_the_ones_the_live_path_writes(self):
		"""The backfill goes through recount_sector rather than repeating the arithmetic,
		so it cannot state a figure an Employee save would not."""
		licence = frappe.get_doc("PAM License Details", self.licence)
		row = next((r for r in licence.pam_license_stats if r.occupational_sector), None)
		if not row:
			self.skipTest("the licence has no configured sector rows")

		fill_designation_sectors()
		if row.occupational_sector not in mapped_sectors():
			self.skipTest("this sector has no designations mapped to it")

		recount_every_sector_row()

		nationals, expatriates = count_workers(
			licence.civil_id_number_for_licensing, row.occupational_sector
		)
		expected = {
			"national_number_of_workers": str(nationals),
			"expatriate_number_of_workers": str(expatriates),
			**derived_figures(
				row.occupational_sector,
				row.ratio_number_of_national_workers,
				nationals,
				expatriates,
			),
		}
		written = frappe.db.get_value(
			"PAM License Stats", row.name, list(expected.keys()), as_dict=True
		)

		self.assertEqual(dict(written), expected)

	def test_it_adds_no_rows(self):
		"""A licence can have employees in a sector it has no row for, and recount_sector
		would add one. Filling in a figure is what was asked for; changing what the licence
		declares is not."""
		before = frappe.db.count("PAM License Stats", {"parenttype": "PAM License Details"})

		fill_designation_sectors()
		recount_every_sector_row()

		self.assertEqual(
			frappe.db.count("PAM License Stats", {"parenttype": "PAM License Details"}), before
		)
