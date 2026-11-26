# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The lobby board page: its rules run in node, its markup is checked here."""

import pathlib
import re
import subprocess

from frappe.tests.utils import FrappeTestCase

PAGE_DIR = pathlib.Path(__file__).parent
PAGE = PAGE_DIR / "transportation_schedules_board.js"


class TestBoardRules(FrappeTestCase):
	def test_the_node_self_check_passes(self):
		check = PAGE_DIR / "test_board_rules.js"
		try:
			result = subprocess.run(["node", str(check)], capture_output=True, text=True, timeout=60)
		except FileNotFoundError:
			self.skipTest("node is not available on this machine")
		self.assertEqual(result.returncode, 0, f"{result.stdout}\n{result.stderr}")


class TestBoardMarkup(FrappeTestCase):
	def setUp(self):
		self.source = PAGE.read_text()

	def test_no_inline_style_attributes(self):
		self.assertNotIn('style="', self.source)

	def test_no_link_is_rendered_on_the_board(self):
		self.assertNotIn("<a ", self.source)

	def test_camp_and_theme_live_in_the_query_string(self):
		self.assertIn('url.searchParams.set("camp", this.camp)', self.source)
		self.assertIn('url.searchParams.set("theme", this.theme)', self.source)
		self.assertIn("history.replaceState", self.source)

	def test_the_title_is_not_departures(self):
		self.assertIn('__("Transportation Schedules")', self.source)
		self.assertIn("جدول مواعيد النقل", self.source)
		self.assertNotIn('__("Departures")', self.source)

	def test_no_camp_is_hardcoded(self):
		for camp in ("Mahboula", "Farwaniya", "Mangaf", "ACC-0"):
			self.assertNotIn(camp, self.source)

	def test_the_wordmark_takes_the_text_colour(self):
		self.assertIn('fill="currentColor"', self.source)
		self.assertNotRegex(self.source, r'fill="#')

	def test_passenger_names_never_go_below_15px(self):
		self.assertRegex(self.source, r"--tsb-t-name: clamp\(15px,")

	def test_each_duration_is_one_constant(self):
		for name in ("WINDOW_MINUTES", "DEPARTED_GRACE_MINUTES", "BOARDING_LEAD_MINUTES", "ROTATE_MS", "POLL_MS"):
			self.assertEqual(len(re.findall(rf"const {name} = ", self.source)), 1, name)
