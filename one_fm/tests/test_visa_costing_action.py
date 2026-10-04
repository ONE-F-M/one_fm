# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A Visa Costing Action worth 20 KWD in the HR Costing table.

The BA site has no Visa Costing row and its Action list is still the older spelling, so
the option ships with the doctype JSON and the row is seeded by a patch rather than
migrated.

The 20 KWD lives in its own Visa Amount column rather than in the work permit fee, and is
tied to the Action: picking it fills an empty amount, switching away takes the 20 back
off, and an amount typed in by hand is left alone either way.
"""

import json
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.add_visa_costing_action import ACTION, PARENT, VISA_AMOUNT

CHILD_DOCTYPE = "GRD Renewal Extension Cost"
SCRIPT = "one_fm/public/js/doctype_js/hr_settings.js"
HARNESS = "one_fm/tests/js/visa_costing_default_harness.js"


def run_handler(row, event="renewal_or_extend"):
	"""Run the shipped hr_settings.js handler over one row and return the row after."""
	app = frappe.get_app_path("one_fm", "..")
	out = subprocess.run(
		["node", f"{app}/{HARNESS}", f"{app}/{SCRIPT}", json.dumps({"event": event, "row": row})],
		capture_output=True, text=True, check=True,
	)
	return json.loads(out.stdout)


class TestTheActionIsOffered(FrappeTestCase):
	def test_visa_costing_is_one_of_the_actions(self):
		options = frappe.get_meta(CHILD_DOCTYPE).get_field("renewal_or_extend").options.split("\n")
		self.assertIn(ACTION, options)

	def test_the_actions_that_were_already_there_are_untouched(self):
		# No existing costing option may be affected.
		options = frappe.get_meta(CHILD_DOCTYPE).get_field("renewal_or_extend").options.split("\n")
		for existing in ("New Kuwaiti", "Overseas", "Overseas (Government)", "Renewal (Kuwaiti)",
						 "Renewal Expat", "Extension", "Visa Extension", "Local Transfer",
						 "Cancellation"):
			self.assertIn(existing, options)

	def test_it_is_not_scoped_by_years(self):
		# Only the two renewal Actions are keyed by duration; a Visa Costing row filed
		# under no duration must still be found by the master fee lookup.
		from one_fm.grd.doctype.preparation.preparation import YEAR_SCOPED_ACTIONS
		self.assertNotIn(ACTION, YEAR_SCOPED_ACTIONS)


class TestTheAmountDefaults(FrappeTestCase):
	"""The browser side, exercised by loading the shipped file rather than reading it."""

	def test_picking_visa_costing_fills_in_20(self):
		row = run_handler({"renewal_or_extend": ACTION})
		self.assertEqual(row.get("visa_amount"), VISA_AMOUNT)

	def test_the_row_total_follows_the_amount(self):
		# The fee is worthless if Total Amount does not move with it.
		row = run_handler({"renewal_or_extend": ACTION})
		self.assertEqual(row.get("total_amount"), VISA_AMOUNT)

	def test_an_amount_somebody_set_is_not_overwritten(self):
		row = run_handler({"renewal_or_extend": ACTION, "visa_amount": 35})
		self.assertEqual(row.get("visa_amount"), 35)

	def test_the_work_permit_fee_is_left_alone(self):
		# The visa fee has its own column now; picking the Action must not touch the
		# work permit amount, and the row totals both.
		row = run_handler({"renewal_or_extend": ACTION, "work_permit_amount": 10})
		self.assertEqual(row.get("work_permit_amount"), 10)
		self.assertEqual(row.get("visa_amount"), VISA_AMOUNT)
		self.assertEqual(row.get("total_amount"), 30)

	def test_the_field_exists_on_the_costing_table(self):
		field = frappe.get_meta(CHILD_DOCTYPE).get_field("visa_amount")
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Currency")
		self.assertEqual(field.label, "Visa Amount")

	def test_the_server_totals_it_too(self):
		# The browser and the HR Settings validate hook must agree, or a row saved by
		# any other route carries a total that does not match its own components.
		from one_fm.grd.doctype.preparation.preparation import (
			COST_COMPONENT_FIELDS,
			MASTER_COST_COMPONENT_FIELDS,
		)
		self.assertIn("visa_amount", MASTER_COST_COMPONENT_FIELDS)
		# Preparation Record has no visa_amount column, so its contract is unchanged -
		# widening it would set a field that does not exist and drop the value on save.
		self.assertNotIn("visa_amount", COST_COMPONENT_FIELDS)
		self.assertIsNone(frappe.get_meta("Preparation Record").get_field("visa_amount"))

	def test_no_other_action_gets_the_visa_costing_fee(self):
		for other in ("Extension", "Renewal Expat", "Cancellation"):
			row = run_handler({"renewal_or_extend": other})
			self.assertIsNone(row.get("visa_amount"), other)

	def test_switching_away_takes_the_fee_back_off(self):
		for other in ("Extension", "Renewal Expat", "Cancellation", "Visa Extension"):
			row = run_handler({"renewal_or_extend": other,
							   "visa_amount": VISA_AMOUNT})
			self.assertEqual(row.get("visa_amount"), 0, other)

	def test_the_total_follows_the_fee_back_down(self):
		row = run_handler({"renewal_or_extend": "Extension",
						   "visa_amount": VISA_AMOUNT})
		self.assertEqual(row.get("total_amount"), 0)

	def test_switching_away_leaves_a_typed_amount_alone(self):
		# Only the 20 comes off. Any other figure was entered by hand.
		row = run_handler({"renewal_or_extend": "Extension", "visa_amount": 35})
		self.assertEqual(row.get("visa_amount"), 35)

	def test_the_other_components_are_never_touched(self):
		row = run_handler({"renewal_or_extend": "Extension",
						   "visa_amount": VISA_AMOUNT,
						   "medical_insurance_amount": 50, "civil_id_amount": 5})
		self.assertEqual(row.get("medical_insurance_amount"), 50)
		self.assertEqual(row.get("civil_id_amount"), 5)
		self.assertEqual(row.get("total_amount"), 55)


def costing_row():
	return frappe.db.get_value(
		CHILD_DOCTYPE,
		{"parent": PARENT, "parenttype": PARENT, "renewal_or_extend": ACTION},
		["visa_amount", "total_amount"], as_dict=True)


def set_fee(amount):
	settings = frappe.get_single(PARENT)
	for row in settings.renewal_extension_cost:
		if row.renewal_or_extend == ACTION:
			row.visa_amount = amount
			break
	else:
		settings.append("renewal_extension_cost",
						{"renewal_or_extend": ACTION, "visa_amount": amount})
	settings.save(ignore_permissions=True)


# Two classes rather than two tests: FrappeTestCase rolls back per CLASS, so a fee written
# by one test is still there for the next one in the same class - which is exactly what
# made the overwrite test pass while hiding the seeding test.
class TestThePatchSeedsTheRow(FrappeTestCase):
	def test_it_configures_the_action_with_its_fee(self):
		from one_fm.patches.v15_0 import add_visa_costing_action as patch

		if costing_row():
			self.skipTest("Visa Costing is already configured on this site")

		patch.execute()

		row = costing_row()
		self.assertIsNotNone(row)
		self.assertEqual(row.visa_amount, VISA_AMOUNT)
		# The fee is worthless if Total Amount does not move with it.
		self.assertEqual(row.total_amount, VISA_AMOUNT)

	def test_it_leaves_every_other_costing_row_alone(self):
		from one_fm.patches.v15_0 import add_visa_costing_action as patch

		before = {
			(r.renewal_or_extend, r.no_of_years): r.total_amount
			for r in frappe.get_single(PARENT).renewal_extension_cost
			if r.renewal_or_extend != ACTION
		}
		patch.execute()
		after = {
			(r.renewal_or_extend, r.no_of_years): r.total_amount
			for r in frappe.get_single(PARENT).renewal_extension_cost
			if r.renewal_or_extend != ACTION
		}
		self.assertEqual(before, after)


class TestThePatchDoesNotOverwriteAFee(FrappeTestCase):
	def test_rerunning_it_leaves_a_corrected_fee_alone(self):
		# A patch reruns on every migrate that has not recorded it. One that rewrote the
		# fee would undo a correction somebody made in HR Settings, every time.
		from one_fm.patches.v15_0 import add_visa_costing_action as patch

		set_fee(35)
		patch.execute()
		self.assertEqual(costing_row().visa_amount, 35)
