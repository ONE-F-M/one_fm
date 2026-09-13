# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002178: the Action is "Renewal Expat", and it still opens the same three documents.

The rename touched four Select fields and eight modules. What breaks silently if one of
them is missed is not the label - it is the link: a Preparation row whose Action no longer
matches the string a sub-document lookup is keyed on opens nothing at all, and says nothing
about it.
"""

from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

import one_fm

from one_fm.grd.doctype.preparation.preparation import (
	CATEGORIES,
	SEQUENCED_CLASSIFICATIONS,
	YEAR_SCOPED_ACTIONS,
)
from one_fm.grd.doctype.residency.residency import (
	ACTIONS_HANDLED_ON_SUBMIT,
	MOI_CATEGORY_BY_ACTION,
)

RENEWAL_EXPAT = "Renewal Expat"
OLD_NAMES = ("Renewal (Non-Kuwaiti)", "Renewal Non Kuwaiti")


def _options(doctype, fieldname):
	return frappe.get_meta(doctype).get_field(fieldname).options.split("\n")


class TestRenewalExpatOptions(FrappeTestCase):
	def test_the_costing_table_offers_the_new_name(self):
		self.assertIn(RENEWAL_EXPAT, _options("GRD Renewal Extension Cost", "renewal_or_extend"))

	def test_the_preparation_row_offers_the_new_name(self):
		self.assertIn(RENEWAL_EXPAT, _options("Preparation Record", "renewal_or_extend"))

	def test_the_work_permit_type_offers_the_new_name(self):
		self.assertIn(RENEWAL_EXPAT, _options("Work Permit", "work_permit_type"))

	def test_no_field_still_offers_an_old_name(self):
		for doctype, fieldname in (
			("GRD Renewal Extension Cost", "renewal_or_extend"),
			("Preparation Record", "renewal_or_extend"),
			("Work Permit", "work_permit_type"),
		):
			options = _options(doctype, fieldname)
			for old in OLD_NAMES:
				self.assertNotIn(old, options, f"{doctype}.{fieldname} still offers {old!r}")

	def test_renewal_kuwaiti_is_untouched(self):
		"""Only the expat option was renamed - the Kuwaiti one is a different fee row."""
		self.assertIn("Renewal (Kuwaiti)", _options("Preparation Record", "renewal_or_extend"))
		self.assertIn("Renewal Kuwaiti", _options("Work Permit", "work_permit_type"))


class TestRenewalExpatStillLinksItsDocuments(FrappeTestCase):
	"""AC3: the Action opens a Renewal insurance, a Renewal residency and a Renewal PACI."""

	def test_it_opens_a_renewal_residency(self):
		self.assertEqual(MOI_CATEGORY_BY_ACTION[RENEWAL_EXPAT][0], "Renewal")

	def test_it_is_not_treated_as_an_extension(self):
		"""Missing here, the extend branch would open a second Residency categorised Extend."""
		self.assertIn(RENEWAL_EXPAT, ACTIONS_HANDLED_ON_SUBMIT)

	def test_no_call_site_was_left_on_an_old_name(self):
		"""The one check that catches a missed branch anywhere, not just the ones named here.

		Medical Insurance and PACI decide what to open with an inline comparison rather than
		a table, so there is no constant to assert on. A branch left comparing against the
		old spelling never matches, and opens nothing - silently.
		"""
		app = Path(one_fm.__file__).parent
		stragglers = [
			f"{path.relative_to(app)}:{number}"
			for path in app.rglob("*")
			if path.suffix in (".py", ".js", ".json")
			and "__pycache__" not in path.parts
			# The rename patch has to name what it is renaming, and so does this test.
			and "patches" not in path.parts
			and path.name != Path(__file__).name
			for number, line in enumerate(path.read_text(errors="ignore").splitlines(), 1)
			if any(old in line for old in OLD_NAMES)
		]
		self.assertEqual(stragglers, [], f"still on the old Action name: {stragglers}")

	def test_its_permit_stays_inside_the_document_sequence(self):
		_, values = SEQUENCED_CLASSIFICATIONS["Work Permit"]
		self.assertIn(RENEWAL_EXPAT, values)

	def test_it_is_still_a_year_scoped_renewal_action(self):
		self.assertIn(RENEWAL_EXPAT, YEAR_SCOPED_ACTIONS)

	def test_a_renewal_batch_may_still_carry_it(self):
		self.assertIn(RENEWAL_EXPAT, CATEGORIES["Renewal"]["actions"])


class TestHrCostingLabel(FrappeTestCase):
	def test_the_costing_table_is_labelled_hr_costing(self):
		"""AC1: the section and the table both read HR Costing."""
		meta = frappe.get_meta("HR Settings")
		self.assertEqual(meta.get_field("renewal_extension_cost").label, "HR Costing")
		self.assertEqual(meta.get_field("renewal_extension_costing_section").label, "HR Costing")
