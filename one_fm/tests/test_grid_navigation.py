# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The transportation schedule's navigation pad.

The pure helpers (``panWindow``, ``snapScrollTop``, ``workWindow``) are exercised by
``transportation_schedule/test_grid_navigation.js`` (``node test_grid_navigation.js``),
which reads the shipped helpers out of the canvas rather than copying them. What is
pinned here is that the pad is wired to them and that the Work / 24h buttons anchor on
``planStart + 3h``.
"""

import pathlib
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

CANVAS_DIR = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule"))
CANVAS = CANVAS_DIR / "transportation_schedule.js"


class TestTheGridNavigationSelfCheckPasses(FrappeTestCase):
	def test_the_node_self_check_passes(self):
		check = CANVAS_DIR / "test_grid_navigation.js"
		self.assertTrue(check.exists(), "the grid navigation self-check is missing")
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


class TestThePadIsWiredIn(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def _method(self, name):
		return self.canvas.split(f"            {name}(", 1)[1].split("\n            },", 1)[0]

	def test_work_and_24h_anchor_on_plan_start_plus_three_hours(self):
		self.assertIn("workWindow(this.planStart.getTime())", self._method("showWorkHours"))
		body = self._method("show24h")
		self.assertIn("this.planStart.getTime() + (3 * NAV_HOUR_MS)", body)
		self.assertNotIn("setUTCHours", body)
		self.assertNotIn("setUTCHours", self._method("showWorkHours"))

	def test_every_button_is_bound_to_its_edge_flag(self):
		for flag in ("navAtLeft", "navAtRight", "navAtTop", "navAtBottom", "navAtHome"):
			self.assertIn(f':disabled="{flag}"', self.canvas)
			self.assertIn(f"            {flag}() {{", self.canvas)

	def test_the_template_only_calls_methods_without_a_leading_underscore(self):
		for call in ("navVertical(-1, $event)", "navVertical(1, $event)", "navPanHoldStart(-1)",
				"navPanHoldStart(1)", "navPanHoldStop()", "navCenter()", 'navWake"'):
			self.assertIn(call, self.canvas)
		for name in ("navTween", "navPan", "navPanHoldStart", "navPanHoldStop", "navVertical", "navCenter"):
			self.assertIn(f"            {name}(", self.canvas)

	def test_the_pad_does_not_swallow_a_drop(self):
		self.assertIn("'rp-navpad-dragging': draggingCard || isDraggingBlock", self.canvas)
		self.assertIn(".rp-navpad.rp-navpad-dragging", self.canvas)
		self.assertIn("pointer-events: none", self.canvas.split(".rp-navpad.rp-navpad-dragging", 1)[1][:160])

	def test_reduced_motion_is_respected_in_js_and_css(self):
		self.assertIn("(prefers-reduced-motion: reduce)", self._method("navReducedMotion"))
		self.assertIn("@media (prefers-reduced-motion: reduce)", self.canvas)

	def test_the_pad_has_no_inline_style_and_its_strings_are_translated(self):
		pad = self.canvas.split('<div class="rp-navpad"', 1)[1].split("</div>", 1)[0]
		self.assertNotIn("style=", pad)
		self.assertNotIn('title="', pad.replace(':title="', ""))
		self.assertEqual(pad.count(":title=\"__("), 5)

	def test_listeners_and_timers_are_cleaned_up(self):
		tail = self.canvas.split("beforeUnmount() {", 1)[1].split("}).mount(", 1)[0]
		for needle in ("removeEventListener('scroll'", "clearTimeout(this._navIdleTimer)",
				"this.navPanHoldStop()", "this.navTweenCancel()"):
			self.assertIn(needle, tail)
