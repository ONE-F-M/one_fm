# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002099: how many expatriates a sector is allowed, and how far it is over."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.pam_license_details.pam_license_details import (
	EXEMPT_SECTOR,
	SECTOR_EXPAT_ALLOWANCE,
	derived_figures,
	expats_allowed,
)

PROFESSIONALS = "علميون و فنيون"   # allowance 5
MANAGERS = "مديرون"                # allowance 1
SERVICES = "مقدمي خدمات"           # allowance 10


class TestExpatsAllowed(FrappeTestCase):
	def test_every_sector_pam_rations_has_an_allowance(self):
		self.assertEqual(
			SECTOR_EXPAT_ALLOWANCE,
			{
				"علميون و فنيون": 5,
				"مديرون": 1,
				"كتبة و تنفيذيون": 2,
				"مقدمي خدمات": 10,
				"بائعون": 3,
			},
		)

	def test_the_allowance_is_the_ratio_plus_the_sector_s_own(self):
		# 20% ratio, 4 nationals: 4 x 80 / 20 = 16, plus 5 for professionals.
		self.assertEqual(expats_allowed(PROFESSIONALS, 20, 4), 21)
		# Same numbers, managers get 1.
		self.assertEqual(expats_allowed(MANAGERS, 20, 4), 17)
		# Service providers get 10.
		self.assertEqual(expats_allowed(SERVICES, 20, 4), 26)

	def test_the_exempt_sector_is_allowed_none(self):
		"""PAM does not ration it by the ratio, so there is no headcount to permit against."""
		self.assertEqual(expats_allowed(EXEMPT_SECTOR, 20, 40), 0)

	def test_no_ratio_permits_nothing(self):
		for ratio in (None, "", 0):
			with self.subTest(ratio=ratio):
				self.assertEqual(expats_allowed(PROFESSIONALS, ratio, 4), 0)

	def test_a_sector_with_no_allowance_configured_gets_the_ratio_alone(self):
		"""A gap in the master data is not a licence to invent an allowance for it."""
		self.assertEqual(expats_allowed("_Test Unmapped Sector", 20, 4), 16)

	def test_the_sectors_pam_rations_exist_as_records(self):
		for sector in tuple(SECTOR_EXPAT_ALLOWANCE) + (EXEMPT_SECTOR,):
			with self.subTest(sector=sector):
				self.assertTrue(frappe.db.exists("Occupational Sector", sector))


class TestExpatsViolated(FrappeTestCase):
	def test_a_sector_over_its_allowance_is_in_violation_by_the_difference(self):
		# 20% ratio, 4 nationals -> 21 allowed for professionals. 25 on the books.
		figures = derived_figures(PROFESSIONALS, ratio=20, nationals=4, expatriates=25)
		self.assertEqual(figures["exempt_number_of_workers"], "21")
		self.assertEqual(figures["violation_number_of_workers"], "4")

	def test_a_sector_inside_its_allowance_is_in_violation_by_nothing(self):
		"""Never negative, and never a violation for being under the limit - which is what
		the AC's own subtraction, read literally, would have produced."""
		figures = derived_figures(PROFESSIONALS, ratio=20, nationals=4, expatriates=10)
		self.assertEqual(figures["exempt_number_of_workers"], "21")
		self.assertEqual(figures["violation_number_of_workers"], "0")

	def test_a_sector_exactly_on_its_allowance_is_compliant(self):
		figures = derived_figures(PROFESSIONALS, ratio=20, nationals=4, expatriates=21)
		self.assertEqual(figures["violation_number_of_workers"], "0")

	def test_every_expatriate_in_the_exempt_sector_is_in_violation(self):
		"""Nothing is allowed there, so anyone on the books is over the line."""
		figures = derived_figures(EXEMPT_SECTOR, ratio=20, nationals=4, expatriates=3)
		self.assertEqual(figures["exempt_number_of_workers"], "0")
		self.assertEqual(figures["violation_number_of_workers"], "3")

	def test_the_figures_are_stated_to_the_nearest_half(self):
		# 30% ratio, 1 national: 1 x 70 / 30 = 2.333 + 1 = 3.333 -> 3.5
		figures = derived_figures(MANAGERS, ratio=30, nationals=1, expatriates=6)
		self.assertEqual(figures["exempt_number_of_workers"], "3.5")
		self.assertEqual(figures["violation_number_of_workers"], "2.5")

	def test_the_values_may_arrive_as_the_strings_the_row_stores(self):
		figures = derived_figures(MANAGERS, "20", "4", "25")
		self.assertEqual(figures["exempt_number_of_workers"], "17")
		self.assertEqual(figures["violation_number_of_workers"], "8")


class TestLicenceFillsInTheAllowance(FrappeTestCase):
	def test_saving_a_licence_states_the_allowance_and_the_violation(self):
		license = frappe.get_doc({
			"doctype": "PAM License Details",
			"label_name": "_Test Allowance Licence",
			"civil_id_number_for_licensing": "_TEST-PAM-ALLOW",
			"license_name": "_Test Allowance Licence",
			"classification": "Commercial",
			"status": "Not suspended",
			"pam_license_stats": [{
				"occupational_sector": PROFESSIONALS,
				"ratio_number_of_national_workers": "20",
				"national_number_of_workers": "4",
				"expatriate_number_of_workers": "25",
			}],
		})
		license.flags.ignore_permissions = True
		license.insert()

		row = license.pam_license_stats[0]
		self.assertEqual(row.exempt_number_of_workers, "21")
		self.assertEqual(row.violation_number_of_workers, "4")
