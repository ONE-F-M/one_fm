# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The pool's text filters survive doubled, leading and trailing spaces.

HR-EMP-01872 is stored as "Samir  Basnet" (two spaces), so typing "samir basnet" in the
Employee name filter matched nothing. The rule is exercised by
``transportation_schedule/test_search_normalize.js`` (``node test_search_normalize.js``),
which reads the shipped helper out of the canvas rather than copying it; what is pinned
here is that the filter and the chips actually go through it.
"""

import pathlib
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

CANVAS_DIR = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule"))
CANVAS = CANVAS_DIR / "transportation_schedule.js"


class TestTheSearchNormaliserSelfCheckPasses(FrappeTestCase):
	def test_the_node_self_check_passes(self):
		check = CANVAS_DIR / "test_search_normalize.js"
		self.assertTrue(check.exists(), "the search-normaliser self-check is missing")
		try:
			result = subprocess.run(
				["node", str(check)], capture_output=True, text=True, timeout=60
			)
		except FileNotFoundError:
			self.skipTest("node is not available on this machine")
		self.assertEqual(
			result.returncode, 0,
			f"node {check.name} failed:\n{result.stdout}\n{result.stderr}",
		)


class TestTheFilterAndChipsUseIt(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_both_sides_of_every_comparison_are_normalised(self):
		# The shared predicate normalises both sides; the node check pins it with a
		# stored double space and a typed single one.
		check = CANVAS_DIR / "test_card_filter.js"
		self.assertTrue(check.exists(), "the card-filter self-check is missing")
		try:
			result = subprocess.run(
				["node", str(check)], capture_output=True, text=True, timeout=60
			)
		except FileNotFoundError:
			self.skipTest("node is not available on this machine")
		self.assertEqual(
			result.returncode, 0,
			f"node {check.name} failed:\n{result.stdout}\n{result.stderr}",
		)

	def test_matching_riders_lead_the_chips_and_the_count_is_unchanged(self):
		self.assertIn("chipEmployees(card).slice(0,3)", self.canvas)
		self.assertIn("card.employees.length > 3", self.canvas)
		self.assertIn("+{{ card.employees.length - 3 }} more", self.canvas)
