# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002595: the PCC Attestation badge belongs to onboarding only.

A Police Clearance Certificate is asked of somebody joining. A Renewal or an Offboarding
never opens one, and the badge sent operators looking for a step that is not part of their
process.
"""

import json
import shutil
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.preparation.preparation_dashboard import get_data

HARNESS = frappe.get_app_path("one_fm", "tests", "js", "pcc_connection_visibility_harness.js")
PCC = "PCC Attestation"


def _visibility(category):
	"""Run the SHIPPED filter and report what the Connections panel is left holding."""
	out = subprocess.run(
		["node", HARNESS, json.dumps({"category": category})],
		capture_output=True,
		text=True,
		env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
		check=True,
	)
	return json.loads(out.stdout)


class TestThePCCBadgeFollowsTheCategory(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not shutil.which("node"):
			raise cls.failureException("node is needed to run the shipped rule")

	def test_onboarding_shows_it(self):
		self.assertIn(PCC, _visibility("Onboarding")["items"])

	def test_renewal_hides_it(self):
		self.assertNotIn(PCC, _visibility("Renewal")["items"])

	def test_offboarding_hides_it(self):
		self.assertNotIn(PCC, _visibility("Offboarding")["items"])

	def test_a_preparation_with_no_category_yet_hides_it(self):
		"""Only Onboarding opens a PCC, so an unset Category is not one."""
		self.assertNotIn(PCC, _visibility(None)["items"])

	def test_every_other_badge_survives_the_filter(self):
		for category in ("Onboarding", "Renewal", "Offboarding"):
			items = _visibility(category)["items"]
			for doctype in (
				"Work Permit",
				"Medical Insurance",
				"Residency",
				"PACI",
				"Fingerprint Appointment",
				"Medical Appointment",
			):
				self.assertIn(doctype, items, f"{doctype} vanished on {category}")

	def test_the_shared_meta_is_left_alone(self):
		"""frm.meta.__dashboard is shared by every Preparation open in the session.

		Filtering it in place would hide the badge on the next Onboarding record opened.
		"""
		self.assertIn(PCC, _visibility("Renewal")["meta_items"])

	def test_the_rendered_links_are_dropped_before_re_rendering(self):
		"""The links are on the page before a client refresh handler runs, and
		render_links() returns early once data_rendered is set."""
		result = _visibility("Renewal")
		self.assertIn("empty", result["calls"])
		self.assertIn("refresh", result["calls"])
		self.assertFalse(result["data_rendered"])


class TestTheServerSideDashboardIsUnchanged(FrappeTestCase):
	def test_pcc_is_still_offered_to_the_doctype(self):
		"""get_data() runs per DocType and is handed no document, so it cannot see the
		Category - the filter has to be the form's."""
		linked = [doctype for group in get_data()["transactions"] for doctype in group["items"]]
		self.assertIn(PCC, linked)

	def test_the_form_script_filters_on_the_category(self):
		source = frappe.read_file(
			frappe.get_app_path("one_fm", "grd", "doctype", "preparation", "preparation.js")
		)
		self.assertIn("set_pcc_connection_visibility(frm)", source)
		# Called on the category change as well as on refresh: an operator switching a
		# Renewal to Onboarding should not have to reload to see the badge.
		self.assertEqual(source.count("set_pcc_connection_visibility(frm);"), 2)
