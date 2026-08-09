# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Transportation Manifest page payload (WI-001766).

The manifest identifies the assigned bus as "<plate>, <model>" so a driver or
field supervisor does not have to look up the vehicle master on site. The string
itself is composed in the page's `vehicleString` helper; what is guarded here is
that the model actually reaches the frontend, since a dropped field would leave
the helper silently rendering the plate alone.
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

PAGE_JS = ("one_fm", "one_fm", "page", "transportation_manifest_page", "transportation_manifest_page.js")
BACKEND_PY = (
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.py",
)


def _read(parts):
	return frappe.read_file(frappe.get_app_path(*parts))


class TestManifestVehicleString(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.js = _read(PAGE_JS)
		cls.py = _read(BACKEND_PY)

	def test_model_is_a_real_vehicle_field(self):
		# The whole feature rests on this fieldname; ERPNext renaming it would
		# otherwise surface as a blank model rather than an error.
		self.assertTrue(frappe.get_meta("Vehicle").has_field("model"))

	def test_the_backend_fetches_the_model(self):
		# Vehicle metadata for the manifest is batch-fetched once; the model has to
		# be in that field list or vehicleMeta never carries it. The list spans
		# several lines, hence the inline DOTALL.
		self.assertRegex(
			self.py, r'(?s)fields=\[\s*"name",\s*"license_plate".*?"model".*?\]',
		)

	def test_the_model_is_published_in_vehicle_meta(self):
		self.assertIn('"model": v_doc.get("model", "")', self.py)

	def test_the_page_composes_plate_and_model(self):
		self.assertIn("function vehicleString(meta)", self.js)
		self.assertIn("[meta.license_plate, meta.model]", self.js)

	def test_blank_parts_are_filtered_so_no_orphaned_comma(self):
		helper = re.search(r"function vehicleString\(meta\) \{.*?\n\t\}", self.js, re.S)
		self.assertIsNotNone(helper, msg="vehicleString helper not found")
		self.assertIn(".filter(Boolean)", helper.group(0))
		self.assertIn('.join(", ")', helper.group(0))

	def test_both_render_points_show_the_composed_string(self):
		# The AC asks for it in the header strip and in the vehicle detail block.
		self.assertIn('<span class="mfst-tab-plate">${escHtml(vstr)}</span>', self.js)
		self.assertIn('<div class="mfst-vehicle-plate">${escHtml(vstr)}</div>', self.js)

	def test_the_plate_is_no_longer_rendered_on_its_own(self):
		self.assertNotIn("escHtml(meta.license_plate)", self.js)
