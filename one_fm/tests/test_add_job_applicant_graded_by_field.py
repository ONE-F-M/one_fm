# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The patch adds Graded By to Job Applicant, the field the Job Applicant map assigns its recruiter tasks from."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.add_job_applicant_graded_by_field import NEW_FIELD, execute

CUSTOM_FIELD = f"Job Applicant-{NEW_FIELD}"


class TestAddJobApplicantGradedByField(FrappeTestCase):
	def setUp(self):
		if frappe.db.exists("Custom Field", CUSTOM_FIELD):
			frappe.delete_doc("Custom Field", CUSTOM_FIELD)
		frappe.clear_cache(doctype="Job Applicant")

	def tearDown(self):
		execute()
		frappe.clear_cache(doctype="Job Applicant")

	def test_adds_a_read_only_user_link(self):
		execute()

		field = frappe.db.get_value(
			"Custom Field", CUSTOM_FIELD, ["fieldtype", "options", "read_only", "no_copy"], as_dict=True
		)
		self.assertEqual(
			(field.fieldtype, field.options, field.read_only, field.no_copy), ("Link", "User", 1, 1)
		)

	def test_running_twice_keeps_one_field(self):
		execute()
		execute()

		self.assertEqual(frappe.db.count("Custom Field", {"dt": "Job Applicant", "fieldname": NEW_FIELD}), 1)
