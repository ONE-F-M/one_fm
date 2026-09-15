# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""An OLM card says which shift it serves, and works a window a shift really works.

An OLM site routes every shift to one shared stop, so one card can carry the staff of
several. It used to group them by the HOUR a shift starts: a 06:30 shift and a 06:59 one
landed on one card whose window was min(start)..max(end) - a window nobody works - and
whose Operations Shift was blank, which the board printed as "Ad-hoc".
"""

import frappe
from frappe.tests.utils import FrappeTestCase

SOURCE = frappe.get_app_path(
	"one_fm", "one_fm", "doctype", "transportation_shipment", "shipment_generator.py"
)
CANVAS = frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.py"
)


class TestTheGrouping(FrappeTestCase):
	def setUp(self):
		self.source = frappe.read_file(SOURCE)

	def test_shifts_are_grouped_on_their_own_window(self):
		self.assertIn(
			'group_key = (stop_location, str(shift_doc.start_time), str(shift_doc.end_time))',
			self.source,
		)

	def test_the_start_hour_is_no_longer_a_key(self):
		# The bug itself: two different windows sharing an hour became one card.
		self.assertNotIn("time_key = start_dt.hour", self.source)

	def test_the_card_no_longer_stretches_to_cover_the_group(self):
		# min(start)/max(end) described a window no shift worked.
		self.assertNotIn('if shift_doc.start_time and (not grp["start"]', self.source)

	def test_the_group_token_carries_the_window(self):
		self.assertIn('"group_token": f"GROUP-{start_key}-{end_key}"', self.source)


class TestNamingTheShift(FrappeTestCase):
	def setUp(self):
		self.source = frappe.read_file(SOURCE)

	def test_a_card_serving_one_shift_links_it(self):
		self.assertIn('"operations_shift": named[0] if len(named) == 1 else None', self.source)

	def test_a_card_serving_several_lists_them_all(self):
		# Different roles finishing together share a window; no single link is truthful,
		# but "Ad-hoc" is a lie either way.
		self.assertIn('"aggregated_shifts": ", ".join(named)', self.source)

	def test_the_field_exists_to_hold_them(self):
		field = frappe.get_meta("Transportation Shipment").get_field("aggregated_shifts")
		if not field:
			self.skipTest("run `bench migrate`: aggregated_shifts not on this site yet")

		self.assertEqual(field.fieldtype, "Small Text")

	def test_the_board_reads_it_before_falling_back(self):
		self.assertIn(
			's.operations_shift or s.aggregated_shifts or "Ad-hoc"', frappe.read_file(CANVAS)
		)


class TestTheExistingCardsAreCarriedOver(FrappeTestCase):
	"""Without the patch the next generation builds every OLM journey a second time."""

	def setUp(self):
		self.source = frappe.read_file(frappe.get_app_path(
			"one_fm", "patches", "v15_0", "rekey_olm_shipments_on_shift_window.py"
		))

	def test_the_patch_rekeys_from_the_window_the_card_already_stores(self):
		self.assertIn('GROUP-{start}-{end}', self.source)
		self.assertIn('"pair_group": pair', self.source)

	def test_a_card_that_cannot_be_rekeyed_is_left_alone(self):
		# It is about to become two cards; guessing one of them would strand riders.
		self.assertIn("stranded.append((card.name, card.status))", self.source)

	def test_it_is_registered_to_run(self):
		self.assertIn(
			"one_fm.patches.v15_0.rekey_olm_shipments_on_shift_window",
			frappe.read_file(frappe.get_app_path("one_fm", "patches.txt")),
		)
