# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002498: raising a Residency Payment Request from the record that owes the money."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.residency_payment import (
	LIVE_DOCSTATUS,
	SOURCE_DOCTYPES,
	is_payable,
	make_residency_payment_request,
)

BUTTON_SCRIPT = frappe.get_app_path(
	"one_fm", "public", "js", "grd", "residency_payment_request_button.js"
)


class TestWhatCanOweAPayment(FrappeTestCase):
	def test_a_submitted_preparation_can(self):
		self.assertTrue(is_payable(frappe._dict(doctype="Preparation", docstatus=1)))

	def test_a_draft_preparation_cannot(self):
		"""The costing is only real once it has been submitted."""
		self.assertFalse(is_payable(frappe._dict(doctype="Preparation", docstatus=0)))

	def test_a_residency_with_a_fine_can(self):
		self.assertTrue(
			is_payable(
				frappe._dict(
					doctype="Residency",
					workflow_state="Completed",
					residency_fine_to_be_added=1,
					residency_fine_amount_kwd=10.0,
				)
			)
		)

	def test_a_residency_whose_fine_is_ticked_but_unpriced_cannot(self):
		"""A fine with no amount is one nobody has worked out yet."""
		self.assertFalse(
			is_payable(
				frappe._dict(
					doctype="Residency",
					workflow_state="Completed",
					residency_fine_to_be_added=1,
					residency_fine_amount_kwd=0,
				)
			)
		)

	def test_a_residency_with_no_fine_cannot(self):
		"""The base processing amounts belong to the Preparation that opened it."""
		self.assertFalse(
			is_payable(
				frappe._dict(
					doctype="Residency",
					workflow_state="Completed",
					residency_fine_to_be_added=0,
					residency_fine_amount_kwd=10.0,
				)
			)
		)

	def test_a_paci_with_a_fine_can(self):
		self.assertTrue(
			is_payable(
				frappe._dict(
					doctype="PACI",
					workflow_state="Completed",
					is_paci_fine_applicable=1,
					paci_fine_amount_kwd=2.0,
				)
			)
		)

	def test_a_cancelled_record_cannot(self):
		for doctype, ticked, amount in (
			("Residency", "residency_fine_to_be_added", "residency_fine_amount_kwd"),
			("PACI", "is_paci_fine_applicable", "paci_fine_amount_kwd"),
		):
			self.assertFalse(
				is_payable(
					frappe._dict(
						{"doctype": doctype, "workflow_state": "Cancelled", ticked: 1, amount: 5.0}
					)
				),
				doctype,
			)

	def test_nothing_else_can(self):
		self.assertFalse(is_payable(frappe._dict(doctype="Work Permit", docstatus=1)))


class TestTheRequestIsRefusedFromTheWrongPlace(FrappeTestCase):
	def test_an_unsupported_doctype_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			make_residency_payment_request("Work Permit", "WP-0001")

	def test_the_three_sources_are_the_ones_the_story_names(self):
		self.assertEqual(SOURCE_DOCTYPES, ("Preparation", "Residency", "PACI"))


class TestTheDuplicateRule(FrappeTestCase):
	def test_a_cancelled_request_does_not_block_a_new_one(self):
		"""Draft and Submitted are live claims; a cancelled request is not."""
		self.assertEqual(LIVE_DOCSTATUS, (0, 1))
		self.assertNotIn(2, LIVE_DOCSTATUS)


class TestTheReferenceFields(FrappeTestCase):
	def setUp(self):
		self.definition = json.loads(
			frappe.read_file(
				frappe.get_app_path(
					"one_fm",
					"grd",
					"doctype",
					"residency_payment_request",
					"residency_payment_request.json",
				)
			)
		)
		self.fields = {f["fieldname"]: f for f in self.definition["fields"]}

	def test_the_request_records_what_it_was_raised_from(self):
		self.assertEqual(self.fields["reference_doctype"]["fieldtype"], "Link")
		self.assertEqual(self.fields["reference_doctype"]["options"], "DocType")
		self.assertEqual(self.fields["reference_docname"]["fieldtype"], "Dynamic Link")
		self.assertEqual(self.fields["reference_docname"]["options"], "reference_doctype")

	def test_neither_is_typed_by_hand(self):
		"""They are what the duplicate rule is keyed on; an editable one defeats it."""
		self.assertEqual(self.fields["reference_doctype"]["read_only"], 1)
		self.assertEqual(self.fields["reference_docname"]["read_only"], 1)


class TestTheFormScript(FrappeTestCase):
	def setUp(self):
		self.source = frappe.read_file(BUTTON_SCRIPT)

	def test_it_is_loaded_once_for_the_session(self):
		"""A file listed under doctype_js is evaluated again for every DocType it is
		listed against, which would add the button three times."""
		from one_fm import hooks

		self.assertIn(
			"/assets/one_fm/js/grd/residency_payment_request_button.js", hooks.app_include_js
		)
		for doctype in SOURCE_DOCTYPES:
			self.assertNotEqual(
				hooks.doctype_js.get(doctype),
				"public/js/grd/residency_payment_request_button.js",
			)

	def test_it_registers_on_all_three_sources(self):
		for doctype in SOURCE_DOCTYPES:
			self.assertIn(f'"{doctype}"', self.source)

	def test_it_opens_the_existing_request_rather_than_raising_a_second(self):
		self.assertIn("r.message.existing", self.source)
		self.assertIn(
			"A Residency Payment Request [{0}] is already linked to this document.",
			self.source,
		)

	def test_the_new_request_is_handed_over_unsaved(self):
		"""An operator who clicked by mistake should leave nothing behind."""
		self.assertIn("frappe.model.sync(r.message.doc)", self.source)

	def test_every_user_facing_string_is_translatable(self):
		self.assertIn('__("Create Residency Payment Request")', self.source)
