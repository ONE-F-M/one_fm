# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002309: Total Cards Planned / Total Cards Remaining on the schedule header.

The counters live in the page's Vue computed block, so they are extracted and *run*
here rather than asserted against as source text. A source check passes just as
happily when the expression is present and wrong - which is how a canvas fix has been
reported done twice before while the browser still disagreed.
"""

import json
import re
import shutil
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

PAGE_JS = ("one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js")

# Six cards on the board, two of them already dropped on a lane.
CARDS = [{"id": f"TSHIP-{n}"} for n in range(1, 7)]
ASSIGNED = ["TSHIP-1", "TSHIP-2"]


def _computed(js, name):
	"""The body of one computed property, as a callable JS function expression."""
	match = re.search(rf"\n\s*{name}\(\) \{{(.*?)\n\s*\}},", js, re.S)
	if not match:
		raise AssertionError(f"computed {name!r} not found in the page script")
	return "function () {" + match.group(1) + "\n}"


class TestTheCounters(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.js = frappe.read_file(frappe.get_app_path(*PAGE_JS))

	def _run(self, cards=CARDS, assigned=ASSIGNED, filtered=None):
		"""Evaluate the three computed properties against a board state."""
		if not shutil.which("node"):
			self.skipTest("node is not available to run the page script")

		harness = f"""
			const planned = {_computed(self.js, 'totalCardsPlanned')};
			const remaining = {_computed(self.js, 'totalCardsRemaining')};
			const allPlanned = {_computed(self.js, 'allCardsPlanned')};
			const state = {{
				planData: {{ shipment_cards: {json.dumps(cards)} }},
				assignedCards: new Set({json.dumps(assigned)}),
				searchQuery: {json.dumps(filtered or "")},
			}};
			state.totalCardsPlanned = planned.call(state);
			state.totalCardsRemaining = remaining.call(state);
			console.log(JSON.stringify({{
				planned: state.totalCardsPlanned,
				remaining: state.totalCardsRemaining,
				done: allPlanned.call(state),
			}}));
		"""
		out = subprocess.run(
			["node", "-e", harness], capture_output=True, text=True, timeout=30
		)
		self.assertEqual(out.returncode, 0, out.stderr)
		return json.loads(out.stdout)

	def test_it_counts_what_is_on_the_lanes_and_what_is_left(self):
		"""AC1: the two summary metrics."""
		result = self._run()

		self.assertEqual(result["planned"], 2)
		self.assertEqual(result["remaining"], 4)

	def test_the_two_always_account_for_every_card(self):
		result = self._run()

		self.assertEqual(result["planned"] + result["remaining"], len(CARDS))

	def test_a_drop_moves_one_card_from_remaining_to_planned(self):
		"""AC2: assigning a third card increments one and decrements the other."""
		before = self._run()
		after = self._run(assigned=ASSIGNED + ["TSHIP-3"])

		self.assertEqual(after["planned"], before["planned"] + 1)
		self.assertEqual(after["remaining"], before["remaining"] - 1)

	def test_unassigning_moves_it_back(self):
		before = self._run()
		after = self._run(assigned=ASSIGNED[:1])

		self.assertEqual(after["planned"], before["planned"] - 1)
		self.assertEqual(after["remaining"], before["remaining"] + 1)

	def test_searching_does_not_change_the_totals(self):
		"""These are scheduling progress, not a view of the filtered sidebar. A counter
		that drops because somebody typed in the search box is worse than none."""
		self.assertEqual(self._run(), self._run(filtered="mahboula"))

	def test_an_empty_board_reads_zero_and_zero(self):
		result = self._run(cards=[], assigned=[])

		self.assertEqual((result["planned"], result["remaining"]), (0, 0))
		self.assertFalse(result["done"], "nothing planned is not the same as all planned")

	def test_it_says_when_everything_is_placed(self):
		result = self._run(assigned=[c["id"] for c in CARDS])

		self.assertEqual(result["remaining"], 0)
		self.assertTrue(result["done"])


class TestTheCountersAreOnTheHeader(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.js = frappe.read_file(frappe.get_app_path(*PAGE_JS))

	def test_both_metrics_are_rendered_in_the_header_toolbar(self):
		header = re.search(r'<div id="rp-header-right">.*?\n  </div>', self.js, re.S)
		self.assertIsNotNone(header, msg="header toolbar not found")

		self.assertIn("Total Cards Planned", header.group(0))
		self.assertIn("Total Cards Remaining", header.group(0))
