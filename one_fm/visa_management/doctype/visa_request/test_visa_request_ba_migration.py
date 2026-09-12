# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002426: the later Visa Request changes brought over from the BA site.

Three things the earlier migration (WI-002069, guarded in test_visa_request_visibility)
did not cover: what the GRD Operator has to fill in, the list view the analyst configured,
and the Visa Requests showing on the Job Offer they were raised from.

Two BA values are deliberately *not* followed, and are pinned here so a later pass does not
quietly re-apply them:
  * custom_pam_file still points at PAM License Details, not PAM File (WI-002233); and
  * the two rejection remarks stay writable (WI-002106) - the Processa map requires the
    reason to be typed on the form, which a read-only field makes impossible.
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.add_visa_request_list_view_columns import BA_COLUMNS, TOTAL_FIELDS

# What the BA site makes mandatory on Visa Request, exactly. The GRD Operator cannot move a
# request on without them, and a field quietly losing its reqd flag is invisible until a
# request reaches PAM with a blank passport.
BA_MANDATORY_FIELDS = (
	"job_offer",
	"job_applicant",
	"request_date",
	"nationality",
	"passport_number",
	"passport_holder_of",
	"passport_issued_on",
	"passport_expires_on",
	"passport_copy",
)

MANAGER_STATE = "Pending GRD Manager Approval"


class TestWhatTheOperatorMustFillIn(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.meta = frappe.get_meta("Visa Request")

	def test_every_field_the_ba_site_requires_is_required_here(self):
		for fieldname in BA_MANDATORY_FIELDS:
			with self.subTest(fieldname=fieldname):
				self.assertTrue(
					self.meta.get_field(fieldname).reqd, f"{fieldname} is not mandatory"
				)

	def test_nothing_else_was_made_mandatory(self):
		"""A field the BA site leaves optional and this one demands would stop an operator
		saving a request the analyst expects to be saveable."""
		required = {field.fieldname for field in self.meta.fields if field.reqd}

		self.assertEqual(required, set(BA_MANDATORY_FIELDS))

	def test_the_driver_licence_is_asked_for_only_from_drivers(self):
		field = self.meta.get_field("driver_license")
		self.assertFalse(field.reqd)
		self.assertEqual(field.mandatory_depends_on, 'eval:doc.designation=="Driver"')


class TestTheWorkPermitNumberLocks(FrappeTestCase):
	"""The BA site added the manager's state to this field's lock, so the number cannot be
	changed once the request is in front of the GRD Manager. Its siblings on the PAM section
	already locked there."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.meta = frappe.get_meta("Visa Request")

	def test_it_locks_at_the_manager_stage(self):
		self.assertIn(
			MANAGER_STATE, self.meta.get_field("custom_work_permit_number").read_only_depends_on
		)

	def test_it_names_only_states_the_workflow_has(self):
		"""The BA export recases the MOI state to "Pending by MOI"; a rule naming a state
		that does not exist never fires, so the field would stay editable at exactly the
		step it should be locked in."""
		import re

		workflow = frappe.db.get_value(
			"Workflow", {"document_type": "Visa Request", "is_active": 1}, "name"
		)
		if not workflow:
			self.skipTest("no active Visa Request workflow on this site")

		states = set(
			frappe.get_all(
				"Workflow Document State",
				filters={"parent": workflow, "parenttype": "Workflow"},
				pluck="state",
			)
		)
		named = set(
			re.findall(
				r'workflow_state\s*==\s*"([^"]+)"',
				self.meta.get_field("custom_work_permit_number").read_only_depends_on or "",
			)
		)

		self.assertEqual(named - states, set())


class TestTheValuesTheBASiteIsBehindOn(FrappeTestCase):
	"""Both would undo a later work item if a migration pass applied them."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.meta = frappe.get_meta("Visa Request")

	def test_the_pam_file_link_still_points_at_the_licence(self):
		"""WI-002233 repointed it; the BA site still says "PAM File"."""
		self.assertEqual(self.meta.get_field("custom_pam_file").options, "PAM License Details")

	def test_the_rejection_reasons_stay_writable(self):
		"""WI-002106 moved both reasons onto the form, where the Processa map reads them.
		The BA site has them read-only, which would leave the map waiting on a reason
		nobody can type."""
		for fieldname in ("operator_rejection_remark", "pam_rejection_remark"):
			with self.subTest(fieldname=fieldname):
				self.assertFalse(self.meta.get_field(fieldname).read_only)


class TestTheListView(FrappeTestCase):
	"""Frappe resolves the list columns from a List View Settings row when one exists and
	ignores the in_list_view flags entirely, so the row is what has to match."""

	def test_the_row_exists(self):
		self.assertTrue(
			frappe.db.exists("List View Settings", "Visa Request"),
			"run bench migrate - add_visa_request_list_view_columns has not been applied",
		)

	def test_the_columns_are_the_ones_the_analyst_configured(self):
		if not frappe.db.exists("List View Settings", "Visa Request"):
			self.skipTest("the patch has not been applied on this site")

		saved = frappe.db.get_value(
			"List View Settings", "Visa Request", ["fields", "total_fields"], as_dict=True
		)

		self.assertEqual(json.loads(saved.fields), BA_COLUMNS)
		self.assertEqual(saved.total_fields, TOTAL_FIELDS)

	def test_the_applicants_name_is_what_the_list_shows(self):
		"""A List View Settings row can only reorder columns the DocType already offers -
		reorder_listview_fields() matches the saved fields against the in_list_view ones
		and adds nothing - so pinning the row was not enough on its own. The BA site does
		this with two Property Setters; this DocType belongs to the app, so it is on the
		field."""
		meta = frappe.get_meta("Visa Request")

		self.assertTrue(meta.get_field("job_applicant_full_name").in_list_view)

	def test_the_applicant_id_is_not(self):
		"""The BA site turns this one off - the list reads as names, not as HR-APP ids."""
		self.assertFalse(frappe.get_meta("Visa Request").get_field("job_applicant").in_list_view)

	def test_the_columns_the_list_can_actually_draw_match_the_ba_site(self):
		in_list_view = [
			field.fieldname
			for field in frappe.get_meta("Visa Request").fields
			if field.in_list_view
		]

		self.assertEqual(sorted(in_list_view), ["job_applicant_full_name", "nationality"])

	def test_every_column_is_a_field_that_exists(self):
		"""Except status_field, which is Frappe's own pseudo-column for the Status
		indicator - a real fieldname that does not exist would render a blank column."""
		meta = frappe.get_meta("Visa Request")
		for column in BA_COLUMNS:
			fieldname = column["fieldname"]
			if fieldname in ("name", "status_field"):
				continue
			with self.subTest(fieldname=fieldname):
				self.assertIsNotNone(meta.get_field(fieldname))


class TestTheJobOfferConnection(FrappeTestCase):
	def test_the_offer_lists_its_visa_requests(self):
		items = [
			item
			for group in (frappe.get_meta("Job Offer").get_dashboard_data().transactions or [])
			for item in (group.get("items") or [])
		]

		self.assertIn("Visa Request", items)

	def test_it_is_not_added_twice(self):
		"""get_dashboard_data() runs on every form load, and the hook appends."""
		meta = frappe.get_meta("Job Offer")
		counts = [
			sum(
				(group.get("items") or []).count("Visa Request")
				for group in (meta.get_dashboard_data().transactions or [])
			)
			for _ in range(3)
		]

		self.assertEqual(counts, [1, 1, 1])

	def test_the_link_field_exists_to_filter_on(self):
		field = frappe.get_meta("Visa Request").get_field("job_offer")

		self.assertIsNotNone(field)
		self.assertEqual(field.options, "Job Offer")

	def test_the_dashboard_says_which_field_to_filter_on(self):
		"""Without it the entry opened the whole Visa Request list unfiltered, and the
		count never loaded at all: get_document_filter() builds {undefined: name}, and
		set_open_count() returns early when data.fieldname is missing."""
		data = frappe.get_meta("Job Offer").get_dashboard_data()

		self.assertEqual(data.fieldname, "job_offer")
		self.assertEqual(data.non_standard_fieldnames.get("Visa Request"), "job_offer")

	def test_the_filter_it_declares_finds_this_offer_s_requests(self):
		"""The filter the client builds from that fieldname, asked of the database."""
		request = frappe.db.get_value(
			"Visa Request", {"job_offer": ["is", "set"]}, ["name", "job_offer"], as_dict=True
		)
		if not request:
			self.skipTest("no Visa Request linked to a Job Offer on this site")

		data = frappe.get_meta("Job Offer").get_dashboard_data()
		found = frappe.get_all("Visa Request", filters={data.fieldname: request.job_offer}, pluck="name")

		self.assertIn(request.name, found)
