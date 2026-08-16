# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002026: the master MOFA and translation rates, and how a PCC Attestation picks them up.

The rates live in HR Settings; applying them is WI-002028's set_attestation_requirements,
which reads them alongside the per-nationality rules. The story's own wording asks for a
single global MOFA rate, and the reporter's master data charges every nationality the same
5 KWD - but it carries a MOFA Cost column per nationality, so the per-row fee wins when it is
set and the global rate is the fallback. That way the story's "master rate" is real and a
nationality that starts charging something else needs no code.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

MOFA_ONLY = "Indian"
NEEDS_TRANSLATION = "Ugandan"
STANDARD_MOFA_FEE = 5.0
TRANSLATION_FEE = 1.5


def _an_active_employee():
	name = frappe.db.get_value("Employee", {"status": "Active"}, "name", order_by="creation asc")
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestPCCProcessingFees(FrappeTestCase):
	def setUp(self):
		for nationality in (MOFA_ONLY, NEEDS_TRANSLATION):
			if not frappe.db.exists("Nationality", nationality):
				self.skipTest(f"Nationality {nationality} is not on this site")

		self.employee = _an_active_employee()
		self._configure()

	def _configure(self, mofa_fee_on_row=None):
		settings = frappe.get_doc("HR Settings")
		settings.set("nationality_attestation_rules", [])
		settings.append("nationality_attestation_rules", {
			"nationality": MOFA_ONLY,
			"embassy_required": 0,
			"mofa_required": 1,
			"mofa_fee_kwd": mofa_fee_on_row or 0,
			"translation_required": 0,
		})
		settings.append("nationality_attestation_rules", {
			"nationality": NEEDS_TRANSLATION,
			"embassy_required": 0, "mofa_required": 0, "translation_required": 1,
		})
		settings.mofa_fee_kwd = STANDARD_MOFA_FEE
		settings.pcc_translation_fee_kwd = TRANSLATION_FEE
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_cache(doctype="HR Settings")

	def _pcc(self, nationality, **kwargs):
		frappe.db.set_value("Employee", self.employee, "one_fm_nationality", nationality)
		pcc = frappe.get_doc({
			"doctype": "PCC Attestation",
			"employee": self.employee,
			"type": "Attestation",
			**kwargs,
		})
		pcc.flags.ignore_permissions = True
		pcc.insert()
		return pcc

	# ------------------------------------------------------------------- AC 1

	def test_hr_settings_holds_both_master_rates(self):
		meta = frappe.get_meta("HR Settings")

		for fieldname in ("mofa_fee_kwd", "pcc_translation_fee_kwd"):
			with self.subTest(fieldname=fieldname):
				field = meta.get_field(fieldname)
				self.assertIsNotNone(field, f"{fieldname} is not on HR Settings")
				self.assertEqual(field.fieldtype, "Currency")

	def test_the_rates_are_saved_centrally(self):
		settings = frappe.get_cached_doc("HR Settings")

		self.assertEqual(settings.mofa_fee_kwd, STANDARD_MOFA_FEE)
		self.assertEqual(settings.pcc_translation_fee_kwd, TRANSLATION_FEE)

	# ------------------------------------------------------------------- AC 2

	def test_a_record_needing_mofa_picks_up_the_master_rate(self):
		pcc = self._pcc(MOFA_ONLY)

		self.assertTrue(pcc.mofa_attestation_required)
		self.assertEqual(pcc.mofa_fee, STANDARD_MOFA_FEE)

	def test_a_nationality_s_own_mofa_fee_wins_over_the_master_rate(self):
		# The reporter's sheet carries a MOFA Cost per nationality. They are all 5 KWD today,
		# so the column exists for the day one of them is not.
		self._configure(mofa_fee_on_row=12)

		self.assertEqual(self._pcc(MOFA_ONLY).mofa_fee, 12.0)

	def test_a_record_not_needing_mofa_carries_no_mofa_fee(self):
		self.assertEqual(self._pcc(NEEDS_TRANSLATION).mofa_fee, 0)

	# ---------------------------------------------------------------- AC 3 & 4

	def test_translation_work_picks_up_the_translation_rate(self):
		pcc = self._pcc(MOFA_ONLY, type="Translation")

		self.assertEqual(pcc.translation_fee, TRANSLATION_FEE)

	def test_attestation_work_carries_no_translation_fee(self):
		"""AC4, as the reporter clarified it.

		Written as "selecting Type == Translation resets the Translation Fee to 0.000", which
		contradicts AC3 on the same trigger. Confirmed it means the opposite Type: anything
		other than Translation clears the fee.
		"""
		pcc = self._pcc(MOFA_ONLY)

		self.assertEqual(pcc.type, "Attestation")
		self.assertEqual(pcc.translation_fee, 0)

	def test_a_nationality_marked_translation_required_carries_the_rate(self):
		# The sheet's Translation Required column, which the Type field alone could not express.
		pcc = self._pcc(NEEDS_TRANSLATION)

		self.assertTrue(pcc.translation_required)
		self.assertEqual(pcc.translation_fee, TRANSLATION_FEE)

	def test_the_two_fees_are_never_both_charged(self):
		for nationality, doc_type in (
			(MOFA_ONLY, "Attestation"),
			(MOFA_ONLY, "Translation"),
			(NEEDS_TRANSLATION, "Attestation"),
			(NEEDS_TRANSLATION, "Translation"),
		):
			with self.subTest(nationality=nationality, type=doc_type):
				pcc = self._pcc(nationality, type=doc_type)
				self.assertFalse(
					pcc.mofa_fee and pcc.translation_fee,
					f"both fees charged: mofa={pcc.mofa_fee} translation={pcc.translation_fee}",
				)

	def test_the_rate_is_re_read_on_every_save(self):
		# A record saved after a rate changes carries the rate current at that save.
		pcc = self._pcc(MOFA_ONLY)
		self.assertEqual(pcc.mofa_fee, STANDARD_MOFA_FEE)

		frappe.db.set_value("HR Settings", "HR Settings", "mofa_fee_kwd", 9)
		frappe.clear_cache(doctype="HR Settings")
		pcc.save()

		self.assertEqual(pcc.mofa_fee, 9.0)
