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


class TestTheCanvasWiresTheSharedFilter(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = (CANVAS_DIR / "transportation_schedule.js").read_text()

	def test_both_block_kinds_dim(self):
		self.assertIn("blockDim(entry) ? 'rp-block-dim' : ''", self.canvas)
		self.assertIn(":class=\"{ 'rp-block-dim': blockDim(entry) }\"", self.canvas)
		self.assertIn(".rp-block-dim { opacity: 0.25;", self.canvas)

	def test_text_applies_after_a_pause_and_clearing_is_immediate(self):
		self.assertIn("setTimeout(apply, 300)", self.canvas)
		self.assertIn("this.$watch(key, v => this.queueAppliedText(!v))", self.canvas)
		self.assertIn("clearTimeout(this._filterTimer);", self.canvas.split("beforeUnmount() {", 1)[1])

	def test_the_toolbar_counts_blocks_while_filtering(self):
		self.assertIn('<span v-if="blockFilter.active" class="rp-block-count">{{ blockCountLabel }}</span>',
					  self.canvas)
