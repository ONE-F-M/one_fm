# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002771: the visas issued against a licence's quota, before anybody has arrived."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.pam_license_details.pam_license_details import (
	VISA_COMPLETED,
	visas_issued_by_quota,
)

FIELDNAME = "number_of_visas_issued"
SOURCE = frappe.get_app_path(
	"one_fm", "grd", "doctype", "pam_license_details", "pam_license_details.py"
)


class TestWhatCounts(FrappeTestCase):
	def test_only_a_completed_request_is_a_visa(self):
		"""Anything earlier is an application, not a visa."""
		block = frappe.read_file(SOURCE).split("def visas_issued_by_quota", 1)[1]
		self.assertIn('["workflow_state", "=", VISA_COMPLETED]', block)
		self.assertEqual(VISA_COMPLETED, "Completed")

	def test_it_reads_the_request_not_an_employee(self):
		"""At this point there is no employee: the visa has been issued and the person has
		not arrived, which is the whole reason the figure is separate from the registered
		headcount beside it."""
		block = frappe.read_file(SOURCE).split("def visas_issued_by_quota", 1)[1]
		self.assertIn("custom_pam_file", block)
		self.assertIn("custom_pam_designation_list", block)
		self.assertNotIn("under_company_residency", block)

	def test_a_cancelled_visa_is_not_an_issued_one(self):
		"""The story's last criterion: a completed cancellation takes the visa back out of
		this count and returns it to the available quota."""
		block = frappe.read_file(SOURCE).split("def visas_issued_by_quota", 1)[1]
		self.assertIn("cancelled_visa_requests", block)
		self.assertIn("if request[\"name\"] in released:", block)

	def test_it_reuses_the_cancellation_rule_rather_than_restating_it(self):
		"""One definition of "this visa has been given back", shared with WI-002744."""
		block = frappe.read_file(SOURCE).split("def visas_issued_by_quota", 1)[1]
		self.assertIn(
			"from one_fm.visa_management.doctype.visa_request.visa_request import", block
		)

	def test_a_designation_in_no_quota_counts_against_no_row(self):
		"""Not against the first one - a visa in the wrong quota reads as headroom that is
		not there."""
		block = frappe.read_file(SOURCE).split("def visas_issued_by_quota", 1)[1]
		self.assertIn("if not quota_type:", block)
		self.assertIn("continue", block)

	def test_a_request_naming_no_designation_is_not_asked_for(self):
		block = frappe.read_file(SOURCE).split("def visas_issued_by_quota", 1)[1]
		self.assertIn('["custom_pam_designation_list", "is", "set"]', block)

	def test_it_runs_against_this_site(self):
		self.assertIsInstance(visas_issued_by_quota(None, None), dict)


class TestWhenItIsRecounted(FrappeTestCase):
	def setUp(self):
		self.source = frappe.read_file(SOURCE)

	def test_a_visa_request_moving_state_recounts_the_licence(self):
		"""Without this the figure only moved when somebody saved an Employee - and the
		whole point of it is the gap before an employee exists."""
		block = self.source.split("def update_quota_from_visa_request", 1)[1]
		self.assertIn('doc.has_value_changed(fieldname)', block)
		self.assertIn('"workflow_state", "custom_pam_file", "custom_pam_designation_list"', block)

	def test_a_request_re_pointed_at_another_licence_moves_both(self):
		block = self.source.split("def update_quota_from_visa_request", 1)[1]
		self.assertIn('before.get("custom_pam_file") if before else None', block)

	def test_a_completed_cancellation_gives_the_visa_back(self):
		block = self.source.split("def update_quota_from_visa_cancellation", 1)[1]
		self.assertIn("visa_request_id", block)
		self.assertIn("recount_license_quota(license_name)", block)

	def test_both_hooks_are_registered(self):
		from one_fm import hooks

		self.assertIn(
			"one_fm.grd.doctype.pam_license_details.pam_license_details.update_quota_from_visa_request",
			hooks.doc_events["Visa Request"]["on_update"],
		)
		self.assertIn(
			"one_fm.grd.doctype.pam_license_details.pam_license_details.update_quota_from_visa_cancellation",
			hooks.doc_events["Visa Cancellation Request"]["on_update"],
		)

	def test_the_row_recount_writes_both_figures_in_one_pass(self):
		"""Registered and issued move together; two writes per row would be two chances to
		leave the pair disagreeing."""
		block = self.source.split("def recount_quota_rows", 1)[1]
		self.assertIn('"registered_numbers_of_employees": counts[quota_type]', block)
		self.assertIn('"number_of_visas_issued": str(issued.get(quota_type, 0))', block)

	def test_saving_a_licence_derives_it(self):
		self.assertIn("self.set_quota_visas_issued()", self.source)


class TestTheFieldIsDerived(FrappeTestCase):
	def test_nobody_types_it(self):
		definition = json.loads(
			frappe.read_file(
				frappe.get_app_path(
					"one_fm",
					"grd",
					"doctype",
					"quota_classification",
					"quota_classification.json",
				)
			)
		)
		field = next(f for f in definition["fields"] if f["fieldname"] == FIELDNAME)
		self.assertEqual(field["read_only"], 1)


class TestTheFieldsItReadsExist(FrappeTestCase):
	def test_the_visa_request_names_a_licence_and_a_designation(self):
		meta = frappe.get_meta("Visa Request")
		self.assertEqual(meta.get_field("custom_pam_file").options, "PAM License Details")
		self.assertEqual(
			meta.get_field("custom_pam_designation_list").options, "PAM Designation List"
		)

	def test_the_cancellation_names_its_visa_request(self):
		self.assertEqual(
			frappe.get_meta("Visa Cancellation Request").get_field("visa_request_id").options,
			"Visa Request",
		)
