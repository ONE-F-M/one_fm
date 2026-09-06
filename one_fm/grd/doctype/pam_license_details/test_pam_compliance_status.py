# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002135: the Status a sector row takes from its violation."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.pam_license_details.pam_license_details import (
	COMPLIANT,
	EXEMPT_SECTOR,
	NON_COMPLIANT,
	derived_figures,
)

PROFESSIONALS = "علميون و فنيون"   # allowance 5


class TestComplianceStatus(FrappeTestCase):
	def test_no_violation_is_compliant(self):
		# 20% ratio, 4 nationals -> 21 allowed; 10 on the books.
		figures = derived_figures(PROFESSIONALS, ratio=20, nationals=4, expatriates=10)
		self.assertEqual(figures["violation_number_of_workers"], "0")
		self.assertEqual(figures["status"], COMPLIANT)

	def test_any_violation_is_non_compliant(self):
		figures = derived_figures(PROFESSIONALS, ratio=20, nationals=4, expatriates=22)
		self.assertEqual(figures["violation_number_of_workers"], "1")
		self.assertEqual(figures["status"], NON_COMPLIANT)

	def test_half_a_violation_still_counts(self):
		# 30% ratio, 1 national -> 3.5 allowed; 4 on the books is 0.5 over.
		figures = derived_figures("مديرون", ratio=30, nationals=1, expatriates=4)
		self.assertEqual(figures["violation_number_of_workers"], "0.5")
		self.assertEqual(figures["status"], NON_COMPLIANT)

	def test_exactly_on_the_allowance_is_compliant(self):
		figures = derived_figures(PROFESSIONALS, ratio=20, nationals=4, expatriates=21)
		self.assertEqual(figures["status"], COMPLIANT)

	def test_an_empty_sector_is_compliant(self):
		figures = derived_figures(PROFESSIONALS, ratio=20, nationals=0, expatriates=0)
		self.assertEqual(figures["status"], COMPLIANT)

	def test_an_expatriate_in_the_exempt_sector_is_not_compliant(self):
		"""Nothing is allowed there, so anybody on the books is over the line."""
		figures = derived_figures(EXEMPT_SECTOR, ratio=20, nationals=4, expatriates=1)
		self.assertEqual(figures["status"], NON_COMPLIANT)

	def test_the_status_is_not_the_operator_s_to_pick(self):
		self.assertTrue(frappe.get_meta("PAM License Stats").get_field("status").read_only)

	def test_the_status_moves_with_the_headcount_on_a_saved_licence(self):
		license = frappe.get_doc({
			"doctype": "PAM License Details",
			"label_name": "_Test Status Licence",
			"civil_id_number_for_licensing": "_TEST-PAM-STATUS",
			"license_name": "_Test Status Licence",
			"classification": "Commercial",
			"status": "Not suspended",
			"pam_license_stats": [{
				"occupational_sector": PROFESSIONALS,
				"ratio_number_of_national_workers": "20",
				"national_number_of_workers": "4",
				"expatriate_number_of_workers": "10",
			}],
		})
		license.flags.ignore_permissions = True
		license.insert()
		self.assertEqual(license.pam_license_stats[0].status, COMPLIANT)

		license.pam_license_stats[0].expatriate_number_of_workers = "30"
		license.save()

		self.assertEqual(license.pam_license_stats[0].status, NON_COMPLIANT)
