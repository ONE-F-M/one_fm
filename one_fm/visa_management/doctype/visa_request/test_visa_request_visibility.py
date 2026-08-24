# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002069: the Visa Request visibility rules brought over from the BA site."""

import frappe
from frappe.tests.utils import FrappeTestCase

GATED_FIELDS = (
	"pam_details_section",
	"custom_pam_file",
	"custom_work_permit_number",
	"moi_details_section",
	"visa_details_section",
)

MOI_STATE = "Pending By MOI"

# The rules that were switched off by writing "// " in front of them - a string Frappe reads
# as a fieldname and quietly treats as false.
DISABLED_RULES = ("custom_pam_file", "pam_reference_number", "custom_pam_designation_list")

# Every field the BA site locks once the request has moved past the step that fills it in.
# A reference number still editable three states later is one an operator can quietly change
# after the ministry has it.
READ_ONLY_FIELDS = (
	"custom_pam_file",
	"pam_reference_number",
	"custom_visa_application_date",
	"custom_pam_designation_list",
	"custom_work_permit_number",
	"moi_reference_number",
	"visa_reference_number",
	"visa_issue_date",
	"visa_expiry_date",
	"visa_document",
	"payment_receipt",
	"payment_date",
)


def _states():
	return {state.state for state in frappe.get_doc("Workflow", "Visa Request").states}


def _named_states(condition):
	return {part.split('"')[1] for part in (condition or "").split("||") if '"' in part}


class TestVisaRequestVisibility(FrappeTestCase):
	def setUp(self):
		self.meta = frappe.get_meta("Visa Request")

	def test_each_section_waits_for_the_stage_that_fills_it_in(self):
		for fieldname in GATED_FIELDS:
			with self.subTest(fieldname=fieldname):
				self.assertTrue(self.meta.get_field(fieldname).depends_on, fieldname)

	def test_every_state_a_rule_names_exists(self):
		"""The BA export writes the MOI state "Pending by MOI" where the workflow here has
		"Pending By MOI". A rule naming a state that does not exist hides the section at
		exactly the step that fills it in."""
		states = _states()
		for fieldname in GATED_FIELDS:
			with self.subTest(fieldname=fieldname):
				unknown = _named_states(self.meta.get_field(fieldname).depends_on) - states
				self.assertEqual(unknown, set(), f"{fieldname} names states the workflow lacks")

	def test_the_moi_section_is_shown_at_the_moi_state(self):
		self.assertIn(MOI_STATE, _named_states(self.meta.get_field("moi_details_section").depends_on))

	def test_the_pam_block_is_shown_from_the_operator_stage_on(self):
		named = _named_states(self.meta.get_field("pam_details_section").depends_on)
		self.assertIn("Pending by GRD Operator", named)
		self.assertIn("Pending By PAM", named)

	def test_the_visa_block_waits_for_issuance(self):
		named = _named_states(self.meta.get_field("visa_details_section").depends_on)
		self.assertIn("Pending Visa Issuance", named)
		self.assertNotIn("Pending by GRD Operator", named)

	def test_the_commented_out_mandatory_rules_are_gone(self):
		for fieldname in DISABLED_RULES:
			with self.subTest(fieldname=fieldname):
				self.assertFalse(self.meta.get_field(fieldname).mandatory_depends_on)

	def test_the_mandatory_rules_the_ba_site_never_had_are_gone(self):
		"""Kept at first on the reasoning that dropping them would make three fields optional.
		The BA confirmed she never wrote them, and the doctype is hers - so they go."""
		for fieldname in ("custom_work_permit_number", "visa_issue_date", "visa_expiry_date"):
			with self.subTest(fieldname=fieldname):
				self.assertFalse(self.meta.get_field(fieldname).mandatory_depends_on, fieldname)

	# ── read-only rules (the second half of the migration) ────────────────────────

	def test_every_field_the_ba_site_locks_is_locked_here(self):
		for fieldname in READ_ONLY_FIELDS:
			with self.subTest(fieldname=fieldname):
				self.assertTrue(
					self.meta.get_field(fieldname).read_only_depends_on,
					f"{fieldname} stays editable after its step",
				)

	def test_every_state_a_read_only_rule_names_exists(self):
		"""Same trap as the visibility rules: the export writes "Pending by MOI" where the
		workflow here has "Pending By MOI", and a rule naming a state that does not exist
		never fires - so the field stays editable at exactly the step it should be locked in."""
		states = _states()
		for fieldname in READ_ONLY_FIELDS:
			with self.subTest(fieldname=fieldname):
				unknown = _named_states(self.meta.get_field(fieldname).read_only_depends_on) - states
				self.assertEqual(unknown, set(), f"{fieldname} names states the workflow lacks")

	def test_a_pam_reference_locks_once_the_file_leaves_pam(self):
		named = _named_states(self.meta.get_field("pam_reference_number").read_only_depends_on)
		self.assertIn("Pending GRD Manager Approval", named)
		self.assertIn(MOI_STATE, named)

	def test_the_visa_fields_lock_on_completion(self):
		for fieldname in ("visa_reference_number", "visa_issue_date", "visa_expiry_date", "visa_document"):
			with self.subTest(fieldname=fieldname):
				named = _named_states(self.meta.get_field(fieldname).read_only_depends_on)
				self.assertIn("Completed", named)
				# Still editable at the step that fills them in.
				self.assertNotIn("Pending Visa Issuance", named)

	def test_the_remark_fields_match_the_ba_site(self):
		self.assertTrue(self.meta.get_field("operator_rejection_remark").read_only)
		self.assertTrue(self.meta.get_field("pam_remarks").hidden)
		self.assertTrue(self.meta.get_field("moi_remarks").hidden)
