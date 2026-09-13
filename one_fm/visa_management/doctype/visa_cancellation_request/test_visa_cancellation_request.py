# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002425: the Visa Cancellation Request DocType, as the BA site has it.

Read from the shipped JSON rather than from the meta: the meta only catches up on the next
migrate, and what this guards is what the app ships.

The lifecycle is the Visa Cancellation process map and is deliberately not tested here -
nothing in this app decides which state a request moves to next.
"""

import json
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

SHIPPED = Path(frappe.get_app_path("one_fm")) / "visa_management" / "doctype" / \
	"visa_cancellation_request" / "visa_cancellation_request.json"


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
		order = [f for f in self.shipped["field_order"] if f != "cancellation_reason"]

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

	def test_it_points_back_at_the_visa_it_cancels(self):
		field = self.by_name["visa_request_id"]

		self.assertEqual(field["fieldtype"], "Link")
		self.assertEqual(field["options"], "Visa Request")
