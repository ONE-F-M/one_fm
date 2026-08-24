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

# Every field the BA site's Visa Request carries. A local addition (reapplied_from) is not
# listed - this pins that nothing of theirs is missing, not that nothing of ours is extra.
BA_FIELDS = (
	"section_break_mbv7", "naming_series", "job_offer", "candidate_country_process",
	"job_applicant", "column_break_vujs", "request_date", "job_applicant_full_name", "agency",
	"assign_grd_operator", "applicant_details_section", "first_name", "second_name",
	"third_name", "last_name", "first_name_in_arabic", "second_name_in_arabic",
	"third_name_in_arabic", "last_name_in_arabic", "column_break_kupi", "nationality", "gender",
	"religion", "place_of_birth", "date_of_birth", "marital_status", "designation",
	"salary_details_section", "salary_type", "column_break_lzkz", "work_permit_salary",
	"educational_qualification_details_section", "educational_qualification",
	"education_specialization", "column_break_rlpq", "university", "place_of_study",
	"passport_details_section", "passport_number", "passport_holder_of", "place_of_issue",
	"column_break_wims", "passport_issued_on", "passport_expires_on", "attachments",
	"passport_copy", "column_break_sqvj", "driver_license", "column_break_byjf",
	"degree_certificate", "column_break_wjxj", "rejection_remarks_section", "column_break_cpvu",
	"operator_rejection_remark", "grd_manager_remark", "column_break_jdrk",
	"pam_rejection_remark", "moi_rejection_remark", "pam_details_section", "custom_pam_file",
	"pam_reference_number", "custom_visa_application_date", "column_break_gvey",
	"custom_pam_designation_list", "custom_work_permit_number", "pam_remarks",
	"column_break_gcih", "pam_decision_date", "moi_details_section", "moi_reference_number",
	"column_break_jvjp", "moi_remarks", "column_break_hyho", "moi_decision_date",
	"visa_details_section", "visa_reference_number", "visa_issue_date", "visa_expiry_date",
	"column_break_uxnb", "visa_document", "payment_receipt", "payment_date",
	"section_break_jrbe", "amended_from",
)

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

	def test_the_doctype_carries_every_field_the_ba_site_has(self):
		"""Pinned as a list rather than a count, so a field added on the BA site and missed
		here names itself instead of showing up as an off-by-one."""
		meta_fields = {f.fieldname for f in self.meta.fields}
		for fieldname in BA_FIELDS:
			with self.subTest(fieldname=fieldname):
				self.assertIn(fieldname, meta_fields)

	def test_the_grd_operator_holder_is_present_and_hidden(self):
		"""Added on the BA site after the first migration pass. Nothing reads it there yet -
		no assignment rule takes its assignee from it, no script mentions it - so it is an
		empty holder, and it is hidden the way the BA site hides it."""
		field = self.meta.get_field("assign_grd_operator")
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "User")
		self.assertTrue(field.hidden)

	def test_the_remark_fields_match_the_ba_site(self):
		self.assertTrue(self.meta.get_field("operator_rejection_remark").read_only)
		self.assertTrue(self.meta.get_field("pam_remarks").hidden)
		self.assertTrue(self.meta.get_field("moi_remarks").hidden)
