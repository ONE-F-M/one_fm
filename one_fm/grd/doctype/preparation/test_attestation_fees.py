# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""PCC attestation fees on a Preparation row, and their place in the row's Total Amount."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.grd.doctype.preparation.preparation import (
	ATTESTATION_FEE_FIELDS,
	COST_COMPONENT_FIELDS,
	category_for_action,
	get_preparation_row_costing,
)

NEEDS_ALL = "Nepali"
NEEDS_NONE = "Ugandan"
NO_RULE = "Egyptian"
EMBASSY_FEE = 17.0
MOFA_FEE = 5.0
TRANSLATION_FEE = 5.0
BASELINE_MOFA_FEE = 4.0

COMPONENTS = {
	"work_permit_amount": 10,
	"medical_insurance_amount": 20,
	"residency_stamp_amount": 30,
	"civil_id_amount": 5,
}
COMPONENT_TOTAL = sum(COMPONENTS.values())


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestPreparationAttestationFees(FrappeTestCase):
	def setUp(self):
		for nationality in (NEEDS_ALL, NEEDS_NONE):
			if not frappe.db.exists("Nationality", nationality):
				self.skipTest(f"Nationality {nationality} is not on this site")

		self.employee = _an_active_employee()

		settings = frappe.get_doc("HR Settings")
		settings.set("nationality_attestation_rules", [])
		settings.append(
			"nationality_attestation_rules",
			{
				"nationality": NEEDS_ALL,
				"embassy_required": 1,
				"embassy_fee_kwd": EMBASSY_FEE,
				"mofa_required": 1,
				"mofa_fee_kwd": MOFA_FEE,
				"translation_required": 1,
			},
		)
		settings.append(
			"nationality_attestation_rules",
			{
				"nationality": NEEDS_NONE,
				"embassy_required": 0,
				"mofa_required": 0,
				"translation_required": 0,
			},
		)
		settings.set("renewal_extension_cost", [])
		for action in ("Overseas", "Overseas (Government)", "Extension"):
			settings.append("renewal_extension_cost", dict(COMPONENTS, renewal_or_extend=action))
		settings.mofa_fee_kwd = BASELINE_MOFA_FEE
		settings.pcc_translation_fee_kwd = TRANSLATION_FEE
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_cache(doctype="HR Settings")

	def _preparation(self, action, nationality, **row):
		frappe.db.set_value("Employee", self.employee, "one_fm_nationality", nationality)
		preparation = frappe.get_doc(
			{
				"doctype": "Preparation",
				"category": category_for_action(action),
				"posting_date": nowdate(),
				"preparation_record": [
					dict(COMPONENTS, employee=self.employee, renewal_or_extend=action, **row)
				],
			}
		)
		preparation.flags.ignore_permissions = True
		preparation.insert()
		return preparation

	def _fees(self, row):
		return [row.embassy_attestation_fee, row.mofa_fee, row.pcc_translation_fee]

	def test_a_nationality_needing_every_step_is_charged_every_fee(self):
		row = self._preparation("Overseas", NEEDS_ALL).preparation_record[0]

		self.assertEqual(row.nationality, NEEDS_ALL)
		self.assertEqual(self._fees(row), [EMBASSY_FEE, MOFA_FEE, TRANSLATION_FEE])
		self.assertEqual(row.total_amount, COMPONENT_TOTAL + EMBASSY_FEE + MOFA_FEE + TRANSLATION_FEE)

	def test_a_nationality_needing_no_step_is_charged_nothing(self):
		row = self._preparation("Overseas (Government)", NEEDS_NONE).preparation_record[0]

		self.assertEqual(self._fees(row), [0, 0, 0])
		self.assertEqual(row.total_amount, COMPONENT_TOTAL)

	def test_a_nationality_with_no_rule_pays_the_baseline_mofa_fee(self):
		row = self._preparation("Overseas", NO_RULE).preparation_record[0]

		self.assertEqual(self._fees(row), [0, BASELINE_MOFA_FEE, 0])
		self.assertEqual(row.total_amount, COMPONENT_TOTAL + BASELINE_MOFA_FEE)

	def test_a_non_overseas_row_drops_stale_fees(self):
		preparation = self._preparation(
			"Renewal Expat",
			NEEDS_ALL,
			no_of_years="1 Year",
			embassy_attestation_fee=EMBASSY_FEE,
			mofa_fee=MOFA_FEE,
			pcc_translation_fee=TRANSLATION_FEE,
		)
		row = preparation.preparation_record[0]

		self.assertEqual(self._fees(row), [0, 0, 0])
		self.assertEqual(row.total_amount, COMPONENT_TOTAL)
		self.assertEqual(preparation.total_payment, COMPONENT_TOTAL)

	def test_the_fee_fields_are_read_only(self):
		meta = frappe.get_meta("Preparation Record")
		for fieldname in ATTESTATION_FEE_FIELDS:
			with self.subTest(fieldname=fieldname):
				field = meta.get_field(fieldname)
				self.assertEqual(field.fieldtype, "Currency")
				self.assertTrue(field.read_only)
				self.assertTrue(field.allow_on_submit)

	def test_the_fees_are_not_a_master_cost_component(self):
		for fieldname in ATTESTATION_FEE_FIELDS:
			self.assertNotIn(fieldname, COST_COMPONENT_FIELDS)

	def test_a_change_after_submit_is_stored(self):
		preparation = self._preparation("Overseas", NEEDS_ALL)
		row_name = preparation.preparation_record[0].name
		# Marked submitted directly: a real submit opens every GRD document for the row.
		preparation.db_set("docstatus", 1)
		frappe.db.set_value("Preparation Record", row_name, "docstatus", 1)
		frappe.db.set_value(
			"Preparation Record",
			row_name,
			{"embassy_attestation_fee": 0, "mofa_fee": 0, "pcc_translation_fee": 0},
		)

		preparation.reload()
		preparation.preparation_record[0].work_permit_amount = 100
		preparation.save()

		stored = frappe.db.get_value(
			"Preparation Record",
			row_name,
			list(ATTESTATION_FEE_FIELDS) + ["total_amount"],
			as_dict=True,
		)
		self.assertEqual(
			[stored.embassy_attestation_fee, stored.mofa_fee, stored.pcc_translation_fee],
			[EMBASSY_FEE, MOFA_FEE, TRANSLATION_FEE],
		)
		self.assertEqual(
			stored.total_amount,
			COMPONENT_TOTAL - COMPONENTS["work_permit_amount"] + 100
			+ EMBASSY_FEE + MOFA_FEE + TRANSLATION_FEE,
		)

	def test_row_costing_carries_the_fees(self):
		costing = get_preparation_row_costing("Overseas", nationality=NEEDS_ALL)
		self.assertEqual(
			[costing[field] for field in ATTESTATION_FEE_FIELDS],
			[EMBASSY_FEE, MOFA_FEE, TRANSLATION_FEE],
		)

	def test_row_costing_for_an_extension_has_no_fees(self):
		costing = get_preparation_row_costing("Extension", no_of_months="1 Month", nationality=NEEDS_ALL)
		self.assertEqual([costing[field] for field in ATTESTATION_FEE_FIELDS], [0, 0, 0])
