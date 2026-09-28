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


def _sections(nationality, then_nationality=None, answered=None):
	"""Run the SHIPPED gate and report what the page would reveal, and what it would send."""
	args = {"nationality": nationality}
	if then_nationality is not None:
		args["then_nationality"] = then_nationality
	if answered:
		args["answered_visa"], args["answered_visa_type"] = answered
	out = subprocess.run(
		["node", HARNESS, json.dumps(args)],
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

	def test_changing_to_kuwaiti_takes_the_question_away_again(self):
		"""A candidate can reach the visa question and then go back and correct their
		nationality. The question was asked once and never re-asked, so it stayed on
		screen."""
		shown = _sections("Indian", then_nationality="Kuwaiti")["shown"]
		self.assertNotIn(".visa", shown)
		self.assertNotIn(".visa_type", shown)
		self.assertIn(".in_kuwait", shown)

	def test_an_answer_already_given_is_cleared_when_the_question_goes(self):
		"""The submit reads the checked radio and the visa type straight off the page, so a
		hidden answer still travels to the backend - a Kuwaiti applicant would arrive
		carrying a visa answer behind a question they can no longer see."""
		result = _sections("Indian", then_nationality="Kuwaiti", answered=("yes", "Work Visa"))
		self.assertIsNone(result["answers"]["visa"])
		self.assertIsNone(result["answers"]["visa_type"])

	def test_an_answer_is_left_alone_while_the_question_still_applies(self):
		"""Clearing it on every pass would wipe what a non-Kuwaiti candidate just typed."""
		result = _sections("Indian", answered=("yes", "Work Visa"))
		self.assertEqual(result["answers"]["visa"], "yes")
		self.assertEqual(result["answers"]["visa_type"], "Work Visa")

	def test_the_page_clears_it_rather_than_only_hiding_it(self):
		page = frappe.read_file(PAGE)
		block = page.split("apply_visa_gate: function", 1)[1].split("\n  },", 1)[0]
		self.assertIn("$(\"#visa input[type='radio']\").prop('checked', false);", block)
		self.assertIn("$(\".visa_type\").val('');", block)

	def test_changing_away_from_kuwaiti_brings_it_back(self):
		shown = _sections("Kuwaiti", then_nationality="Indian")["shown"]
		self.assertIn(".visa", shown)

	def test_it_survives_going_back_and_forth(self):
		self.assertNotIn(".visa", _sections("Kuwaiti", then_nationality="Kuwaiti")["shown"])
		self.assertIn(".visa", _sections("Indian", then_nationality="Nepalese")["shown"])

	def test_the_nationality_handler_re_asks_the_gate(self):
		"""Only once the flow has reached that step: before then there is nothing to
		re-show, and showing it would jump the candidate past the questions in between."""
		page = frappe.read_file(PAGE)
		block = page.split("on_change_nationality: function", 1)[1].split("\n  },", 1)[0]
		self.assertIn("if(me.visa_step_reached){", block)
		self.assertIn("me.apply_visa_gate();", block)

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
