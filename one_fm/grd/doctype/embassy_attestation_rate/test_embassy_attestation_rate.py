# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002025: the Embassy Cost Table master in HR Settings."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.utils import get_embassy_attestation_fee

A_COUNTRY = "Nepal"
ANOTHER_COUNTRY = "India"


def _rates(rows):
	settings = frappe.get_doc("HR Settings")
	settings.set("embassy_attestation_rates", [])
	for row in rows:
		settings.append("embassy_attestation_rates", row)
	settings.flags.ignore_permissions = True
	settings.save()
	return settings


class TestEmbassyAttestationRates(FrappeTestCase):
	def setUp(self):
		for country in (A_COUNTRY, ANOTHER_COUNTRY):
			if not frappe.db.exists("Country", country):
				self.skipTest(f"Country {country} is not on this site")

	def test_the_validation_hook_is_registered(self):
		self.assertIn(
			"one_fm.grd.utils.validate_embassy_attestation_rates",
			frappe.get_hooks("doc_events").get("HR Settings", {}).get("validate", []),
		)

	def test_a_country_and_its_fee_save_as_a_master_row(self):
		settings = _rates([{"country": A_COUNTRY, "embassy_fee_kwd": 15.0}])

		self.assertEqual(settings.embassy_attestation_rates[0].country, A_COUNTRY)
		self.assertEqual(settings.embassy_attestation_rates[0].embassy_fee_kwd, 15.0)

	def test_the_same_country_twice_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			_rates(
				[
					{"country": A_COUNTRY, "embassy_fee_kwd": 15.0},
					{"country": A_COUNTRY, "embassy_fee_kwd": 20.0},
				]
			)

	def test_different_countries_are_fine(self):
		settings = _rates(
			[
				{"country": A_COUNTRY, "embassy_fee_kwd": 15.0},
				{"country": ANOTHER_COUNTRY, "embassy_fee_kwd": 8.5},
			]
		)
		self.assertEqual(len(settings.embassy_attestation_rates), 2)

	def test_a_configured_country_returns_its_fee(self):
		_rates([{"country": A_COUNTRY, "embassy_fee_kwd": 15.0}])
		frappe.clear_cache(doctype="HR Settings")

		self.assertEqual(get_embassy_attestation_fee(A_COUNTRY), 15.0)

	def test_an_absent_country_returns_none_not_zero(self):
		# None means "this embassy does not attest, skip the step"; 0 means "it does and
		# charges nothing". The PCC workflow routes on the difference.
		_rates([{"country": A_COUNTRY, "embassy_fee_kwd": 15.0}])
		frappe.clear_cache(doctype="HR Settings")

		self.assertIsNone(get_embassy_attestation_fee(ANOTHER_COUNTRY))

	def test_a_zero_fee_country_returns_zero_not_none(self):
		_rates([{"country": A_COUNTRY, "embassy_fee_kwd": 0}])
		frappe.clear_cache(doctype="HR Settings")

		self.assertEqual(get_embassy_attestation_fee(A_COUNTRY), 0)

	def test_no_country_returns_none(self):
		self.assertIsNone(get_embassy_attestation_fee(None))
		self.assertIsNone(get_embassy_attestation_fee(""))

	def test_removing_a_row_bypasses_attestation_for_that_country(self):
		_rates([{"country": A_COUNTRY, "embassy_fee_kwd": 15.0}])
		frappe.clear_cache(doctype="HR Settings")
		self.assertEqual(get_embassy_attestation_fee(A_COUNTRY), 15.0)

		_rates([])
		frappe.clear_cache(doctype="HR Settings")

		self.assertIsNone(get_embassy_attestation_fee(A_COUNTRY))

	def test_an_updated_fee_is_what_later_lookups_get(self):
		_rates([{"country": A_COUNTRY, "embassy_fee_kwd": 15.0}])
		_rates([{"country": A_COUNTRY, "embassy_fee_kwd": 18.25}])
		frappe.clear_cache(doctype="HR Settings")

		self.assertEqual(get_embassy_attestation_fee(A_COUNTRY), 18.25)
