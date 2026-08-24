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

	def test_the_mandatory_rules_this_site_added_are_kept(self):
		"""The BA site does not carry these. Dropping them to match it would make three
		fields optional that the process needs."""
		for fieldname, state in (
			("custom_work_permit_number", MOI_STATE),
			("visa_issue_date", "Pending Visa Issuance"),
			("visa_expiry_date", "Pending Visa Issuance"),
		):
			with self.subTest(fieldname=fieldname):
				rule = self.meta.get_field(fieldname).mandatory_depends_on
				self.assertTrue(rule, fieldname)
				self.assertIn(state, rule)
