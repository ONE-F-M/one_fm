# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002094: the nationals a sector needs, and what it is short of."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.pam_license_details.pam_license_details import (
	as_figure,
	derived_figures,
	round_to_half,
)

# The requirement and the shortfall do not depend on the sector - only the expatriate
# allowance does - so these cases state one and hold it still.
SECTOR_UNDER_TEST = "مديرون"

SECTOR = "_Test Figures Sector"


def _a_sector(name):
	if not frappe.db.exists("Occupational Sector", name):
		frappe.get_doc({"doctype": "Occupational Sector", "occupational_sector_type": name}).insert(
			ignore_permissions=True
		)
	return name


class TestRoundToHalf(FrappeTestCase):
	def test_it_rounds_to_the_nearest_half(self):
		for value, expected in ((0, 0), (0.2, 0), (0.3, 0.5), (0.7, 0.5), (0.8, 1.0), (2.24, 2.0), (2.26, 2.5)):
			with self.subTest(value=value):
				self.assertEqual(round_to_half(value), expected)

	def test_a_whole_figure_loses_its_decimal(self):
		self.assertEqual(as_figure(3.0), "3")
		self.assertEqual(as_figure(3.5), "3.5")
		self.assertEqual(as_figure(0), "0")

	def test_a_blank_reads_as_nothing(self):
		"""Every figure on the row is a Data field, so it can be empty rather than zero."""
		self.assertEqual(as_figure(None), "0")
		self.assertEqual(as_figure(""), "0")


class TestDerivedFigures(FrappeTestCase):
	def test_the_requirement_follows_the_ratio(self):
		# 20% of the workforce Kuwaiti: 8 expats need 8 x 20 / 80 = 2 nationals.
		figures = derived_figures(SECTOR_UNDER_TEST, ratio=20, nationals=0, expatriates=8)
		self.assertEqual(figures["required_number_of_national_workers"], "2")

	def test_the_requirement_is_stated_to_the_nearest_half(self):
		# 9 x 20 / 80 = 2.25 -> 2
		self.assertEqual(derived_figures(SECTOR_UNDER_TEST, 20, 0, 9)["required_number_of_national_workers"], "2")
		# 11 x 20 / 80 = 2.75 -> 2.5... rounds to 3 at .75
		self.assertEqual(derived_figures(SECTOR_UNDER_TEST, 20, 0, 11)["required_number_of_national_workers"], "3")
		# 10 x 20 / 80 = 2.5, already a half
		self.assertEqual(derived_figures(SECTOR_UNDER_TEST, 20, 0, 10)["required_number_of_national_workers"], "2.5")

	def test_a_shortfall_is_what_the_sector_is_missing(self):
		figures = derived_figures(SECTOR_UNDER_TEST, ratio=20, nationals=1, expatriates=8)
		self.assertEqual(figures["required_number_of_national_workers"], "2")
		self.assertEqual(figures["exceeding_the_ratio_number_of_national_workers"], "1")

	def test_a_sector_that_already_has_enough_is_short_of_nothing(self):
		"""Never negative - a sector carrying more nationals than required is not short."""
		figures = derived_figures(SECTOR_UNDER_TEST, ratio=20, nationals=5, expatriates=8)
		self.assertEqual(figures["exceeding_the_ratio_number_of_national_workers"], "0")

	def test_no_ratio_asks_for_no_nationals(self):
		for ratio in (None, "", 0):
			with self.subTest(ratio=ratio):
				figures = derived_figures(SECTOR_UNDER_TEST, ratio, nationals=0, expatriates=8)
				self.assertEqual(figures["required_number_of_national_workers"], "0")
				self.assertEqual(figures["exceeding_the_ratio_number_of_national_workers"], "0")

	def test_a_ratio_of_a_hundred_or_more_states_no_requirement(self):
		"""At 100 the formula divides by zero and above it the answer is negative. A
		hand-typed ratio must not stop the licence saving."""
		for ratio in (100, 120):
			with self.subTest(ratio=ratio):
				self.assertEqual(
					derived_figures(SECTOR_UNDER_TEST, ratio, nationals=0, expatriates=8)["required_number_of_national_workers"],
					"0",
				)

	def test_the_counts_may_arrive_as_the_strings_the_row_stores(self):
		figures = derived_figures(SECTOR_UNDER_TEST, "20", "1", "8")
		self.assertEqual(figures["required_number_of_national_workers"], "2")
		self.assertEqual(figures["exceeding_the_ratio_number_of_national_workers"], "1")


class TestLicenceRecalculates(FrappeTestCase):
	def setUp(self):
		self.sector = _a_sector(SECTOR)

	def test_saving_a_licence_fills_the_figures_in(self):
		license = frappe.get_doc({
			"doctype": "PAM License Details",
			"label_name": "_Test Figures Licence",
			"civil_id_number_for_licensing": "_TEST-PAM-FIG",
			"license_name": "_Test Figures Licence",
			"classification": "Commercial",
			"status": "Not suspended",
			"pam_license_stats": [{
				"occupational_sector": self.sector,
				"ratio_number_of_national_workers": "20",
				"national_number_of_workers": "1",
				"expatriate_number_of_workers": "8",
			}],
		})
		license.flags.ignore_permissions = True
		license.insert()

		row = license.pam_license_stats[0]
		self.assertEqual(row.required_number_of_national_workers, "2")
		self.assertEqual(row.exceeding_the_ratio_number_of_national_workers, "1")

	def test_changing_the_ratio_moves_the_figures(self):
		license = frappe.get_doc({
			"doctype": "PAM License Details",
			"label_name": "_Test Ratio Change Licence",
			"civil_id_number_for_licensing": "_TEST-PAM-RATIO",
			"license_name": "_Test Ratio Change Licence",
			"classification": "Commercial",
			"status": "Not suspended",
			"pam_license_stats": [{
				"occupational_sector": self.sector,
				"ratio_number_of_national_workers": "20",
				"national_number_of_workers": "0",
				"expatriate_number_of_workers": "8",
			}],
		})
		license.flags.ignore_permissions = True
		license.insert()
		self.assertEqual(license.pam_license_stats[0].required_number_of_national_workers, "2")

		license.pam_license_stats[0].ratio_number_of_national_workers = "50"
		license.save()

		# 8 x 50 / 50 = 8
		self.assertEqual(license.pam_license_stats[0].required_number_of_national_workers, "8")
		self.assertEqual(license.pam_license_stats[0].exceeding_the_ratio_number_of_national_workers, "8")
