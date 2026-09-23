# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002725: a Kuwaiti candidate is not asked about a visa they do not need."""

import json
import shutil
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

HARNESS = frappe.get_app_path("one_fm", "tests", "js", "careers_visa_gate_harness.js")
PAGE = frappe.get_app_path("one_fm", "templates", "pages", "job_application.js")


def _sections(nationality):
	"""Run the SHIPPED gate and report which sections the page would reveal."""
	out = subprocess.run(
		["node", HARNESS, json.dumps({"nationality": nationality})],
		capture_output=True,
		text=True,
		env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
		check=True,
	)
	return json.loads(out.stdout)


class TestWhatTheCandidateIsAsked(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not shutil.which("node"):
			raise cls.failureException("node is needed to run the shipped rule")

	def test_a_kuwaiti_is_not_asked_about_a_visa(self):
		shown = _sections("Kuwaiti")["shown"]
		self.assertNotIn(".visa", shown)
		self.assertNotIn(".visa_type", shown)

	def test_a_kuwaiti_is_still_asked_whether_they_are_in_kuwait(self):
		"""Where somebody is now is a separate question from whether they may work here,
		and it stays mandatory."""
		self.assertIn(".in_kuwait", _sections("Kuwaiti")["shown"])

	def test_everybody_else_is_asked_about_a_visa_as_before(self):
		for nationality in ("Nepalese", "Indian", "Egyptian"):
			shown = _sections(nationality)["shown"]
			self.assertIn(".visa", shown, nationality)
			# The in-Kuwait question comes after they answer it, as it always has.
			self.assertNotIn(".in_kuwait", shown, nationality)

	def test_a_candidate_who_has_chosen_nothing_yet_is_treated_as_not_kuwaiti(self):
		"""The safe way round: the question can be skipped, never silently required."""
		self.assertIn(".visa", _sections(None)["shown"])

	def test_surrounding_whitespace_does_not_defeat_the_rule(self):
		self.assertTrue(_sections(" Kuwaiti ")["is_kuwaiti"])


class TestItIsOneGate(FrappeTestCase):
	def setUp(self):
		self.source = frappe.read_file(PAGE)

	def test_nothing_reveals_the_visa_question_behind_the_gate(self):
		"""Three call sites used to reveal it directly - three places for this to be
		forgotten. The only remaining reveal is inside the gate itself."""
		self.assertEqual(self.source.count('$(".visa").removeClass'), 1)

	def test_every_former_call_site_goes_through_it(self):
		# The two license paths and the no-license path.
		self.assertEqual(self.source.count("me.show_visa_or_skip();"), 3)

	def test_the_nationality_it_matches_is_the_one_the_records_use(self):
		"""`Kuwaiti` is what the Nationality master and Employee.one_fm_nationality hold;
		a different spelling here matches nobody and switches the rule off."""
		self.assertIn('=== "Kuwaiti"', self.source)
		self.assertTrue(frappe.db.exists("Nationality", "Kuwaiti"))


class TestTheServerSideIsUnchanged(FrappeTestCase):
	def test_a_missing_visa_answer_writes_nothing(self):
		"""A Kuwaiti now sends no visa answer at all, so the applicant must not be
		recorded as having been refused one."""
		source = frappe.read_file(
			frappe.get_app_path("one_fm", "templates", "pages", "job_application.py")
		)
		self.assertIn("if visa and visa_type:", source)
