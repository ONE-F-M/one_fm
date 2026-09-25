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
PAGE = frappe.get_app_path("one_fm", "grd", "doctype", "preparation", "preparation.js")
PCC = "PCC Attestation"
SELECTOR = '.document-link[data-doctype="PCC Attestation"]'


def _run(category):
	"""Run the SHIPPED function against a fake dashboard and report what it did."""
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
		self.assertEqual(_run("Onboarding")["calls"][0]["state"], False)

	def test_renewal_hides_it(self):
		self.assertEqual(_run("Renewal")["calls"][0]["state"], True)

	def test_offboarding_hides_it(self):
		self.assertEqual(_run("Offboarding")["calls"][0]["state"], True)

	def test_a_preparation_with_no_category_yet_hides_it(self):
		"""Only Onboarding opens a PCC, so an unset Category is not one."""
		self.assertEqual(_run(None)["calls"][0]["state"], True)

	def test_it_touches_that_one_badge_and_nothing_else(self):
		for category in ("Onboarding", "Renewal", "Offboarding", None):
			calls = _run(category)["calls"]
			self.assertEqual(len(calls), 1, category)
			self.assertEqual(calls[0]["selector"], SELECTOR, category)
			self.assertEqual(calls[0]["className"], "hidden", category)


class TestItSurvivesTheRealFormObject(FrappeTestCase):
	"""The bug this replaced.

	`render_links()` does `this.data.frm = this.frm`, and `dashboard.data` IS
	`frm.meta.__dashboard` - so by the time a client refresh handler runs, the whole form
	hangs off the shared meta. The first version deep-copied that to filter it and threw

	    TypeError: Converting circular structure to JSON

	which killed the rest of Preparation's refresh handler with it, including the
	read-only locking applied to a submitted record.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not shutil.which("node"):
			raise cls.failureException("node is needed to run the shipped rule")

	def test_it_does_not_raise_on_a_circular_form(self):
		for category in ("Onboarding", "Renewal", "Offboarding", None):
			self.assertIsNone(_run(category)["threw"], category)

	def test_it_does_not_serialise_the_dashboard_data(self):
		source = frappe.read_file(PAGE)
		block = source.split("function set_pcc_connection_visibility", 1)[1]
		self.assertNotIn("JSON.stringify", block)
		self.assertNotIn("JSON.parse", block)

	def test_it_does_not_rewrite_the_shared_meta(self):
		"""frm.meta.__dashboard is shared by every Preparation open in the session."""
		block = frappe.read_file(PAGE).split("function set_pcc_connection_visibility", 1)[1]
		self.assertNotIn("dashboard.data =", block)
		self.assertNotIn("__dashboard.transactions =", block)

	def test_it_does_not_force_a_re_render(self):
		"""render_links() returns early once data_rendered is set, so the old approach had
		to tear the markup down and rebuild it. Toggling one node needs none of that."""
		block = frappe.read_file(PAGE).split("function set_pcc_connection_visibility", 1)[1]
		self.assertNotIn("data_rendered", block)
		self.assertNotIn("dashboard.refresh()", block)


class TestTheServerSideDashboardIsUnchanged(FrappeTestCase):
	def test_pcc_is_still_offered_to_the_doctype(self):
		"""get_data() runs per DocType and is handed no document, so it cannot see the
		Category - the filter has to be the form's."""
		linked = [doctype for group in get_data()["transactions"] for doctype in group["items"]]
		self.assertIn(PCC, linked)

	def test_the_form_script_filters_on_the_category(self):
		source = frappe.read_file(PAGE)
		self.assertIn('frm.doc.category === "Onboarding"', source)
		# Called on the category change as well as on refresh: an operator switching a
		# Renewal to Onboarding should not have to reload to see the badge.
		self.assertEqual(source.count("set_pcc_connection_visibility(frm);"), 2)
