# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002425 and WI-002432: the Visa Cancellation Request, and one live one per visa.

The DocType is the BA site's, field for field; the rules on top of it are this app's. The
lifecycle is the Visa Cancellation process map and is deliberately not tested here - nothing
in this app decides which state a request moves to next.
"""

import json
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.visa_management.doctype.visa_cancellation_request.visa_cancellation_request import (
	REJECTED_STATE,
	has_workflow_state_column,
	is_standing,
	live_cancellation_filters,
)

DOCTYPE = "Visa Cancellation Request"
SEEDED = "WI-002425-VCR-"
VISA_REQUEST = "WI-002425-VR-"

SHIPPED = Path(frappe.get_app_path("one_fm")) / "visa_management" / "doctype" / \
	"visa_cancellation_request" / "visa_cancellation_request.json"


def _clear():
	frappe.db.delete(DOCTYPE, {"name": ["like", SEEDED + "%"]})
	frappe.db.delete("Visa Request", {"name": ["like", VISA_REQUEST + "%"]})


def _visa_request(suffix, workflow_state="Completed", visa_expiry_date=None, job_applicant=None):
	"""A Visa Request row written without the controller: it demands a passport, an
	eligible age and a Job Offer, and none of that is what these rules read."""
	doc = frappe.new_doc("Visa Request")
	doc.name = VISA_REQUEST + suffix
	doc.workflow_state = workflow_state
	doc.visa_expiry_date = visa_expiry_date
	doc.job_applicant = job_applicant
	doc.job_applicant_full_name = "WI-002425 Applicant"
	doc.passport_number = "P-" + suffix
	doc.visa_reference_number = "V-" + suffix
	doc.db_insert()
	return doc.name


def _cancellation(suffix, visa_request, workflow_state=None, docstatus=0):
	doc = frappe.new_doc(DOCTYPE)
	doc.name = SEEDED + suffix
	doc.visa_request_id = visa_request
	doc.docstatus = docstatus
	if workflow_state and has_workflow_state_column():
		doc.set("workflow_state", workflow_state)
	doc.db_insert()
	return doc.name


class TestTheDocTypeMatchesTheBASite(FrappeTestCase):
	"""WI-002425. Read from the shipped JSON as well as the meta: the meta only catches up
	on the next migrate, and what this guards is what the app ships."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.shipped = json.loads(SHIPPED.read_text())
		cls.by_name = {f["fieldname"]: f for f in cls.shipped["fields"]}

	def test_it_carries_every_field_the_ba_site_has(self):
		"""Named one by one, so a field missed on a later pass names itself rather than
		showing up as an off-by-one."""
		ba_fields = [
			"section_break_4abb", "amended_from", "visa_request_id", "pro_operator",
			"column_break_jmap", "job_applicant_full_name", "grd_operator",
			"passport_details_section", "passport_copy", "passport_number",
			"passport_holder_of", "column_break_kzef", "passport_issued_on",
			"passport_expires_on", "moi_details_section", "visa_cancellation_date",
			"pam_details_section", "pam_reference_number",
			"attach_work_permit_cancellation_document", "column_break_bixx",
			"visa_application_date", "visa_details_section", "visa_reference_number",
			"visa_issue_date", "visa_expiry_date", "column_break_lcrq", "visa_document",
			"section_break_fbvp", "pro_officer_rejection_remark",
		]
		for fieldname in ba_fields:
			with self.subTest(fieldname=fieldname):
				self.assertIn(fieldname, self.by_name)

	def test_the_ba_field_order_is_kept(self):
		"""The two fields this app adds - the reason and the hidden workflow_state the
		process map writes - are left out; everything else is in the BA site's order."""
		order = [
			f for f in self.shipped["field_order"]
			if f not in ("cancellation_reason", "workflow_state")
		]

		self.assertEqual(order[:7], [
			"section_break_4abb", "amended_from", "visa_request_id", "pro_operator",
			"column_break_jmap", "job_applicant_full_name", "grd_operator",
		])
		self.assertEqual(order[-1], "pro_officer_rejection_remark")

	def test_it_is_submittable_like_the_ba_site(self):
		self.assertEqual(self.shipped["is_submittable"], 1)

	def test_the_pro_officer_remark_came_over(self):
		"""WI-002427 is deferred, but the field it acts on is part of the DocType and
		migrates with it."""
		field = self.by_name["pro_officer_rejection_remark"]

		self.assertEqual(field["fieldtype"], "Small Text")
		self.assertEqual(field["label"], "PRO Officer Rejection Remark")

	def test_it_names_records_the_way_the_ba_site_does(self):
		"""They do it with a Document Naming Rule record; declared here instead so the
		names travel with the code and a fresh site does not hash-name."""
		self.assertEqual(self.shipped["autoname"], "VCR-OFM-.#####")

	def test_it_carries_the_workflow_state_the_process_map_writes(self):
		"""The Visa Cancellation process map records where a request has got to in
		workflow_state, and its deploy readiness check refuses to deploy without the field.

		On the BA site it is a Custom Field, created incidentally by the stray inactive
		workflow on their DocType. Nothing recreates it here - Processa imports Workflow
		States, Action Masters and Server Scripts but never a Workflow record, and it is
		a Workflow being saved that makes Frappe create this field. So it is declared on
		the DocType, with the same shape Visa Request's has.
		"""
		field = self.by_name["workflow_state"]

		self.assertEqual(field["fieldtype"], "Link")
		self.assertEqual(field["options"], "Workflow State")
		self.assertEqual(field["hidden"], 1)
		# The process map moves a submitted request between states.
		self.assertEqual(field["allow_on_submit"], 1)
		self.assertEqual(field["no_copy"], 1)

	def test_it_points_back_at_the_visa_it_cancels(self):
		field = self.by_name["visa_request_id"]

		self.assertEqual(field["fieldtype"], "Link")
		self.assertEqual(field["options"], "Visa Request")


class TestOneLiveCancellationPerVisa(FrappeTestCase):
	"""WI-002432."""

	def setUp(self):
		_clear()
		self.visa = _visa_request("A")

	def tearDown(self):
		_clear()

	def _applying(self):
		doc = frappe.new_doc(DOCTYPE)
		doc.name = SEEDED + "APPLYING"
		doc.visa_request_id = self.visa
		return doc

	def test_a_second_one_is_refused(self):
		_cancellation("1", self.visa)

		with self.assertRaises(frappe.ValidationError):
			self._applying().validate_no_live_cancellation()

	def test_the_message_points_at_the_one_standing(self):
		_cancellation("1", self.visa)

		with self.assertRaises(frappe.ValidationError) as raised:
			self._applying().validate_no_live_cancellation()

		self.assertIn(SEEDED + "1", str(raised.exception))

	def test_a_rejected_one_frees_the_visa(self):
		"""The story's escape hatch, and the state the process map configures."""
		if not has_workflow_state_column():
			self.skipTest("no workflow_state on Visa Cancellation Request on this site yet")
		_cancellation("1", self.visa, workflow_state=REJECTED_STATE)

		self._applying().validate_no_live_cancellation()

	def test_one_that_has_not_entered_the_process_still_blocks(self):
		"""A cancellation the popup or the expiry job has just raised carries no state at
		all. Asking the database for "state != rejected" is NULL for those rows, so a
		filtered query stops finding exactly the drafts most likely to be duplicated."""
		_cancellation("1", self.visa, workflow_state=None)

		with self.assertRaises(frappe.ValidationError):
			self._applying().validate_no_live_cancellation()

	def test_a_cancelled_one_frees_the_visa(self):
		_cancellation("1", self.visa, docstatus=2)

		self._applying().validate_no_live_cancellation()

	def test_another_visa_is_unaffected(self):
		other = _visa_request("B")
		_cancellation("1", other)

		self._applying().validate_no_live_cancellation()

	def test_an_existing_request_is_never_re_checked(self):
		"""Re-checking on every save would make it unsaveable - it would find itself."""
		_cancellation("1", self.visa)

		doc = self._applying()
		doc.name = SEEDED + "1"
		doc.set("__islocal", False)

		doc.validate_no_live_cancellation()

	def test_only_the_rejected_state_stops_one_standing(self):
		"""The escape hatch on its own, so it is covered on a site whose workflow has not
		arrived yet - and so the NULL case is stated rather than implied."""
		self.assertFalse(is_standing(REJECTED_STATE))
		self.assertTrue(is_standing(None))
		self.assertTrue(is_standing("Draft"))
		self.assertTrue(is_standing("Pending by PRO"))

	def test_the_state_is_never_asked_of_the_database(self):
		"""`workflow_state != 'Visa Cancellation Rejected'` is NULL in SQL wherever the
		state is NULL, which is every cancellation that has not entered the process."""
		filters = live_cancellation_filters(self.visa)

		self.assertNotIn("workflow_state", [f[0] for f in filters])
		self.assertIn(["visa_request_id", "=", self.visa], filters)
		self.assertIn(["docstatus", "!=", 2], filters)

	def test_an_unnamed_document_does_not_switch_the_rule_off(self):
		"""`name != NULL` matches nothing in SQL, which would silently allow every
		duplicate."""
		filters = live_cancellation_filters(self.visa, exclude=None)

		self.assertIn(["name", "!=", ""], filters)

	def test_the_rejected_state_is_one_the_site_really_has(self):
		"""It is configured by the Visa Cancellation process map rather than by this app,
		so a rename there would switch the escape hatch off silently."""
		self.assertTrue(frappe.db.exists("Workflow State", REJECTED_STATE))
