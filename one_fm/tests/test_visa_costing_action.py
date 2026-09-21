# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002601 (dup WI-002617): a Visa Costing Action worth 20 KWD in the HR Costing table.

The criteria describe this arriving by migration from the BA site. It cannot, and that is
pinned below: the BA site has no Visa Costing row at all, and its Action list is still the
pre-WI-002178 spelling, so copying that table over would walk back a rename this app has
already shipped. The option ships with the doctype JSON and the row is seeded by a patch,
which is what makes the same configuration true in Staging and in Production.

The 20 KWD is a DEFAULT, not a rule: picking the Action fills an empty amount in, and a
row whose fee somebody has deliberately set to something else is left alone. Both the
browser handler and the patch are checked for that, because both could overwrite it.
"""

import json
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.add_visa_costing_action import ACTION, PARENT, WORK_PERMIT_AMOUNT

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
		# The criteria are explicit that no existing costing option may be affected.
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
		self.assertEqual(row.get("work_permit_amount"), WORK_PERMIT_AMOUNT)

	def test_the_row_total_follows_the_amount(self):
		# The fee is worthless if Total Amount does not move with it - that mismatch is
		# exactly what WI-002031 had to go back and repair.
		row = run_handler({"renewal_or_extend": ACTION})
		self.assertEqual(row.get("total_amount"), WORK_PERMIT_AMOUNT)

	def test_an_amount_somebody_set_is_not_overwritten(self):
		row = run_handler({"renewal_or_extend": ACTION, "work_permit_amount": 35})
		self.assertEqual(row.get("work_permit_amount"), 35)

	def test_no_other_action_gets_the_visa_costing_fee(self):
		for other in ("Extension", "Renewal Expat", "Cancellation"):
			row = run_handler({"renewal_or_extend": other})
			self.assertIsNone(row.get("work_permit_amount"), other)


def costing_row():
	return frappe.db.get_value(
		CHILD_DOCTYPE,
		{"parent": PARENT, "parenttype": PARENT, "renewal_or_extend": ACTION},
		["work_permit_amount", "total_amount"], as_dict=True)


def set_fee(amount):
	settings = frappe.get_single(PARENT)
	for row in settings.renewal_extension_cost:
		if row.renewal_or_extend == ACTION:
			row.work_permit_amount = amount
			break
	else:
		settings.append("renewal_extension_cost",
						{"renewal_or_extend": ACTION, "work_permit_amount": amount})
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
		self.assertEqual(row.work_permit_amount, WORK_PERMIT_AMOUNT)
		# The fee is worthless if Total Amount does not move with it.
		self.assertEqual(row.total_amount, WORK_PERMIT_AMOUNT)

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
		self.assertEqual(costing_row().work_permit_amount, 35)
