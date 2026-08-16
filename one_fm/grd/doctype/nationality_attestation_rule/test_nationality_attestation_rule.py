# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002025: the per-nationality attestation rules master in HR Settings.

The reporter's master data is a list of nationalities, not of countries - "Nepali",
"Sudanese", "Bangladeshi" - and all thirteen of them exist as Nationality records on this
site. So the table is keyed on Nationality and matched against Employee.one_fm_nationality.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.utils import (
	get_nationality_attestation_rule,
	get_pcc_attestation_fees,
	validate_nationality_attestation_rules,
)

# Straight from the reporter's spreadsheet, and the reason the shape is what it is.
# nationality: (embassy_required, embassy_fee, mofa_required, mofa_fee, translation_required)
SPREADSHEET = {
	"Malawi": (True, 7, True, 5, True),
	"South Sudanese": (True, 15, True, 5, True),
	"Sudanese": (True, 17, True, 5, True),
	"Moroccan": (False, 0, True, 5, False),
	"Ugandan": (False, 0, False, 0, True),
	"Indian": (False, 0, True, 5, False),
	"Yemeni": (True, 10, True, 5, False),
	"Nepali": (True, 16, True, 5, False),
	"Bangladeshi": (False, 0, True, 5, False),
}

STANDARD_MOFA_FEE = 5.0
TRANSLATION_FEE = 1.5


class TestNationalityAttestationRule(FrappeTestCase):
	def setUp(self):
		self.settings = frappe.get_cached_doc("HR Settings")
		self.settings.set("nationality_attestation_rules", [])
		for nationality, (embassy, embassy_fee, mofa, mofa_fee, translation) in SPREADSHEET.items():
			self.settings.append("nationality_attestation_rules", {
				"nationality": nationality,
				"embassy_required": int(embassy),
				"embassy_fee_kwd": embassy_fee,
				"mofa_required": int(mofa),
				"mofa_fee_kwd": mofa_fee,
				"translation_required": int(translation),
			})
		self.settings.mofa_fee_kwd = STANDARD_MOFA_FEE
		self.settings.pcc_translation_fee_kwd = TRANSLATION_FEE

	# --------------------------------------------------------------- the lookup

	def test_every_row_in_the_reporter_s_data_resolves(self):
		for nationality, expected in SPREADSHEET.items():
			with self.subTest(nationality=nationality):
				fees = get_pcc_attestation_fees(nationality)
				embassy, embassy_fee, mofa, mofa_fee, translation = expected

				self.assertEqual(fees.embassy_required, embassy)
				self.assertEqual(fees.embassy_fee, float(embassy_fee))
				self.assertEqual(fees.mofa_required, mofa)
				self.assertEqual(fees.mofa_fee, float(mofa_fee))
				self.assertEqual(fees.translation_required, translation)

	def test_a_nationality_needing_neither_embassy_nor_mofa(self):
		# Ugandan is the row the earlier shape could not represent at all: no embassy and no
		# MOFA, translation only. It routed to Pending MOFA and blocked the PRO on a receipt
		# that would never exist.
		fees = get_pcc_attestation_fees("Ugandan")

		self.assertFalse(fees.embassy_required)
		self.assertFalse(fees.mofa_required)
		self.assertTrue(fees.translation_required)

	def test_a_nationality_with_mofa_but_no_embassy(self):
		fees = get_pcc_attestation_fees("Indian")

		self.assertFalse(fees.embassy_required)
		self.assertEqual(fees.embassy_fee, 0.0)
		self.assertTrue(fees.mofa_required)
		self.assertEqual(fees.mofa_fee, STANDARD_MOFA_FEE)

	def test_a_nationality_with_all_three(self):
		fees = get_pcc_attestation_fees("Sudanese")

		self.assertTrue(fees.embassy_required)
		self.assertEqual(fees.embassy_fee, 17.0)
		self.assertTrue(fees.mofa_required)
		self.assertTrue(fees.translation_required)
		self.assertEqual(fees.translation_fee, TRANSLATION_FEE)

	def test_an_unlisted_nationality_still_goes_through_mofa(self):
		# WI-002029's third criterion: not listed in the table -> Pending MOFA. The table
		# records exceptions, so an absent row is the ordinary case, not an exemption.
		fees = get_pcc_attestation_fees("Kuwaiti")

		self.assertFalse(fees.embassy_required)
		self.assertTrue(fees.mofa_required)
		self.assertEqual(fees.mofa_fee, STANDARD_MOFA_FEE)
		self.assertFalse(fees.translation_required)
		self.assertEqual([fees.embassy_fee, fees.translation_fee], [0.0, 0.0])

	def test_no_nationality_at_all_takes_the_same_default(self):
		# A data gap rather than an exemption, and MOFA is the safe side of it.
		fees = get_pcc_attestation_fees(None)

		self.assertFalse(fees.embassy_required)
		self.assertTrue(fees.mofa_required)
		self.assertIsNone(get_nationality_attestation_rule(None))

	def test_a_listed_nationality_with_mofa_off_is_respected(self):
		# Ugandan. The only way to be exempt from MOFA is to be listed with the box unchecked.
		fees = get_pcc_attestation_fees("Ugandan")

		self.assertFalse(fees.mofa_required)
		self.assertEqual(fees.mofa_fee, 0.0)

	# -------------------------------------------------------- fees follow the flags

	def test_a_fee_is_zero_when_its_step_is_not_required(self):
		# The fee fields are Currency and the cost breakdown sums them, so a step that does
		# not apply has to contribute nothing rather than blank out the total.
		row = self.settings.nationality_attestation_rules[0]
		row.embassy_required = 0
		row.embassy_fee_kwd = 99

		fees = get_pcc_attestation_fees(row.nationality)

		self.assertEqual(fees.embassy_fee, 0.0)

	def test_a_required_mofa_step_with_no_fee_falls_back_to_the_standard_rate(self):
		# Every nationality in the data pays the same 5 KWD, so the per-row fee exists for
		# the day one of them differs. Blank should mean "the usual", not "free".
		row = self.settings.nationality_attestation_rules[0]
		row.mofa_required = 1
		row.mofa_fee_kwd = 0

		self.assertEqual(get_pcc_attestation_fees(row.nationality).mofa_fee, STANDARD_MOFA_FEE)

	def test_a_row_s_own_mofa_fee_wins_over_the_standard_rate(self):
		row = self.settings.nationality_attestation_rules[0]
		row.mofa_required = 1
		row.mofa_fee_kwd = 12

		self.assertEqual(get_pcc_attestation_fees(row.nationality).mofa_fee, 12.0)

	# ------------------------------------------------------------------ validation

	def test_a_nationality_listed_twice_is_blocked(self):
		self.settings.append("nationality_attestation_rules", {
			"nationality": "Nepali", "embassy_required": 1, "embassy_fee_kwd": 20,
		})

		with self.assertRaises(frappe.ValidationError):
			validate_nationality_attestation_rules(self.settings)

	def test_the_reporter_s_data_passes_validation(self):
		validate_nationality_attestation_rules(self.settings)

	def test_a_blank_nationality_row_does_not_trip_the_duplicate_check(self):
		self.settings.append("nationality_attestation_rules", {"nationality": None})
		self.settings.append("nationality_attestation_rules", {"nationality": None})

		validate_nationality_attestation_rules(self.settings)

	# ------------------------------------------------- the key is Nationality

	def test_the_table_is_keyed_on_nationality(self):
		field = frappe.get_meta("Nationality Attestation Rule").get_field("nationality")

		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Nationality")
		self.assertTrue(field.reqd)

	def test_the_reporter_s_values_are_all_real_nationality_records(self):
		"""Every value in the spreadsheet exists as a Nationality, which is why it is the key.

		Including "Malawi", which reads like a country name beside twelve demonyms but is the
		actual name of the Nationality record on this site - so it is not a data-entry slip.
		"""
		for nationality in SPREADSHEET:
			with self.subTest(nationality=nationality):
				self.assertTrue(frappe.db.exists("Nationality", nationality))

	def test_the_employee_field_it_matches_is_a_nationality_link(self):
		field = frappe.get_meta("Employee").get_field("one_fm_nationality")

		self.assertEqual(field.options, "Nationality")
