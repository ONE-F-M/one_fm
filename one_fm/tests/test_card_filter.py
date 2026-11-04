# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""One set of filters drives the unassigned pool and the schedule blocks.

The predicate is exercised by ``transportation_schedule/test_card_filter.js``
(``node test_card_filter.js``), which reads the shipped ``cardMatchesFilters`` and
``blockMatchesFilters`` out of the canvas rather than copying them.
"""

import pathlib
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

CANVAS_DIR = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule"))


class TestCardFilterSelfCheckPasses(FrappeTestCase):
	def test_the_node_self_check_passes(self):
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
