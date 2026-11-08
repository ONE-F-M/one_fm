# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The Transportation Schedule timeline can group its lanes by location or type.

The rule (``groupLaneRows``) is exercised by
``transportation_schedule/test_lane_grouping.js`` (``node test_lane_grouping.js``),
which reads the shipped function out of the canvas rather than copying it. What is
pinned here is that the node check passes and that the canvas wires the control, the
header and the scroll-preserving watcher.
"""

import pathlib
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

CANVAS_DIR = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule"))
CANVAS = CANVAS_DIR / "transportation_schedule.js"


class TestTheLaneGroupingSelfCheckPasses(FrappeTestCase):
	def test_the_node_self_check_passes(self):
		check = CANVAS_DIR / "test_lane_grouping.js"
		self.assertTrue(check.exists(), "the lane-grouping self-check is missing")
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


class TestTheCanvasWiresLaneGrouping(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_control_offers_none_location_and_type(self):
		self.assertIn('v-model="laneGroupBy" class="rp-filter-select rp-lane-groupby"', self.canvas)
		self.assertIn("laneGroupBy: '',", self.canvas)
		self.assertIn('<option value="location">', self.canvas)
		self.assertIn('<option value="type">', self.canvas)

	def test_headers_do_not_carry_a_vehicle_id(self):
		header = self.canvas.split('class="rp-lane-group-header"', 1)[1].split("</div>", 1)[0]
		self.assertIn(":data-group-key", header)
		self.assertNotIn("data-vehicle-id", header)
		self.assertIn("{{ vehicleString(vehicle) }}", self.canvas)

	def test_the_watcher_leaves_zoom_and_selection_alone(self):
		watcher = self.canvas.split("laneGroupBy() {", 1)[1].split("        methods: {", 1)[0]
		self.assertIn("area.scrollTop", watcher)
		for forbidden in ("scrollIntoView", "windowStart", "windowEnd", "selectedItem ="):
			self.assertNotIn(forbidden, watcher)
