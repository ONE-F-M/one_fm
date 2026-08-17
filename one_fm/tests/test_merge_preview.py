# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002078: what the Merge Trip modal is shown before anyone confirms.

The preview is computed on the server so the seat count an operator sees is the one the
Route Plan save will judge them by. A second implementation in the browser would drift,
and the modal would promise a merge the save then refuses.
"""

import pathlib
import re

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.operations.doctype.route_plan.route_plan import leg_occupancy

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))
MERGE_COLOUR = "#819171"


class TestLegOccupancy(FrappeTestCase):
	"""The shared walk. Route Plan validation and the modal both read this."""

	def _stops(self, *pairs):
		return [{"headcount": n, "boards": boards} for n, boards in pairs]

	def test_a_drop_then_a_board_never_ride_together(self):
		peak, _worst, per_leg = leg_occupancy(self._stops((12, False), (12, True)))

		self.assertEqual(peak, 12)
		self.assertEqual(per_leg, [0, 12])

	def test_two_outward_loads_do_ride_together(self):
		peak, _worst, _per_leg = leg_occupancy(self._stops((10, False), (10, False)))

		self.assertEqual(peak, 20)

	def test_the_loop_from_the_criteria(self):
		# Camp -> drop 10 -> drop 12 -> board 10 -> Camp. 32 carried, 22 at the peak.
		peak, worst, per_leg = leg_occupancy(
			self._stops((10, False), (12, False), (10, True))
		)

		self.assertEqual(peak, 22)
		self.assertEqual(worst, 1)
		self.assertEqual(per_leg, [12, 0, 10])

	def test_the_peak_can_fall_later_in_the_run(self):
		peak, worst, _per_leg = leg_occupancy(self._stops((5, True), (9, True)))

		self.assertEqual(peak, 14)
		self.assertEqual(worst, 2)

	def test_an_empty_run_peaks_at_nothing(self):
		self.assertEqual(leg_occupancy([]), (0, 1, []))

	def test_disembarking_is_applied_before_boarding(self):
		# Both at one stop: 10 off then 10 on never exceeds 10.
		peak, _worst, _per_leg = leg_occupancy(self._stops((10, False), (10, True)))

		self.assertEqual(peak, 10)


class TestTheCanvasSpeaksMixed(FrappeTestCase):
	def setUp(self):
		self.source = CANVAS.read_text()

	def test_the_merge_colour_is_the_one_the_story_names(self):
		self.assertIn(f"--rp-color-mixed: {MERGE_COLOUR}", self.source)

	def test_a_merged_block_paints_itself_with_it(self):
		# Without this a merged block borrowed whichever direction was dropped first.
		self.assertIn("item.direction === 'MIXED'", self.source)
		self.assertIn("--rp-color-mixed", self.source)

	def test_the_legend_offers_mixed(self):
		self.assertIn('class="rp-legend-item rp-legend-mixed">Mixed<', self.source)

	def test_mixed_sits_between_return_and_conflict(self):
		order = [
			m.group(1) for m in re.finditer(r'class="rp-legend-item rp-legend-(\w+)"', self.source)
		]

		self.assertEqual(order[:4], ["out", "ret", "mixed", "conflict"])

	def test_the_legend_badge_is_styled(self):
		self.assertIn(".rp-legend-mixed", self.source)

	def test_the_dark_theme_covers_it_too(self):
		self.assertIn("rp-dark .rp-legend-mixed", self.source)


class TestMergePreviewShape(FrappeTestCase):
	"""The endpoint's contract, exercised without touching real shipments."""

	def test_it_is_whitelisted_for_the_canvas_to_call(self):
		# The canvas reaches it over frappe.call, so it has to be whitelisted or the modal
		# gets a PermissionError instead of a preview.
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			get_merge_preview,
			merge_trip_shipments,
		)

		frappe.is_whitelisted(get_merge_preview)
		frappe.is_whitelisted(merge_trip_shipments)

	def test_merging_needs_more_than_one_card(self):
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			get_merge_preview,
		)

		with self.assertRaises(frappe.ValidationError):
			get_merge_preview(["TS-only-one"])

	def test_minutes_are_read_defensively(self):
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import _minutes

		self.assertEqual(_minutes(None), 0)
		self.assertEqual(_minutes(""), 0)
		self.assertEqual(_minutes("15"), 15)
		self.assertEqual(_minutes(-5), 0)          # a negative wait would run the clock backwards
		self.assertEqual(_minutes("not a number"), 0)
