# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Route Plan canvas vehicle label (WI-001778).

A dispatcher identifies a lane by plate and model, so the lane header and the
right-hand details panel both read "<plate>, <model>". The string is composed in
the page's `vehicleString` method; what is guarded here is that the model reaches
the canvas at all, and that every place naming a vehicle to the dispatcher goes
through the one helper - a stray `vehicle.label` would show the VHL code beside
lanes labelled with a plate.
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

PAGE_JS = ("one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js")
PAGE_PY = ("one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.py")


class TestVehicleLaneLabel(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.js = frappe.read_file(frappe.get_app_path(*PAGE_JS))
		cls.py = frappe.read_file(frappe.get_app_path(*PAGE_PY))

	def test_model_is_a_real_vehicle_field(self):
		self.assertTrue(frappe.get_meta("Vehicle").has_field("model"))

	def test_the_canvas_payload_carries_the_model(self):
		self.assertIn('"model":         v.model or ""', self.py)

	def test_the_canvas_query_selects_the_model(self):
		# The canvas builds its own vehicle list, separate from the manifest's.
		query = re.search(
			r'transport_vehicles = frappe\.get_all\("Vehicle".*?\)', self.py, re.S
		)
		self.assertIsNotNone(query, msg="canvas Vehicle query not found")
		self.assertIn('"model"', query.group(0))

	def test_the_helper_composes_plate_and_model(self):
		helper = re.search(r"vehicleString\(v\) \{.*?\n\s*\},", self.js, re.S)
		self.assertIsNotNone(helper, msg="vehicleString helper not found")
		body = helper.group(0)
		self.assertIn("[v.license_plate, v.model]", body)
		self.assertIn(".filter(Boolean)", body)
		self.assertIn(".join(', ')", body)

	def test_a_lane_is_never_left_unlabelled(self):
		# With neither plate nor model the vehicle code stands in, otherwise a lane
		# would render blank and be undroppable in practice.
		helper = re.search(r"vehicleString\(v\) \{.*?\n\s*\},", self.js, re.S)
		self.assertIn("v.label || v.id", helper.group(0))

	def test_the_lane_header_shows_the_composed_string(self):
		self.assertIn("{{ vehicleString(vehicle) }}", self.js)

	def test_the_details_panel_shows_the_composed_string(self):
		# The panel renders vehicleLabelForItem, which must delegate to the helper.
		self.assertIn("{{ vehicleLabelForItem(selectedItem) }}", self.js)
		resolver = re.search(
			r"vehicleLabelForItem\(item\) \{.*?\n\s*\},", self.js, re.S
		)
		self.assertIsNotNone(resolver, msg="vehicleLabelForItem not found")
		self.assertIn("this.vehicleString(v)", resolver.group(0))

	def test_no_dispatcher_message_names_a_vehicle_by_its_raw_label(self):
		self.assertNotIn("vehicle.label", self.js)

	def test_the_duplicate_plate_line_and_its_styles_are_gone(self):
		# The separate plate line was folded into the header string; leaving its CSS
		# behind would be dead weight.
		self.assertNotIn("rp-gv-lp", self.js)
