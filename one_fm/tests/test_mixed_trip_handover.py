# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002171: one bus drops the incoming shift and collects the outgoing one.

Most of this story was already standing when the work item was written — the merge
writes `Mixed` and a shared group key (AC 3.2), and the leg walk already disembarks
before it boards and holds the peak to the seats (AC 3.3, AC 3.4). What was missing is
the handover itself: whether the two shifts actually meet (AC 3.1), the drive between
two different sites (AC 3.6), and a manifest that says which riders get off and which
get on at a stop rather than at the camp (AC 3.5).
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
	SHIFT_ALIGNMENT_TOLERANCE_SECONDS,
	_shift_alignment,
	get_merge_preview,
)


def _card(direction, start, end):
	return frappe._dict({
		"name": frappe.generate_hash("TS", 6),
		"trip_direction": direction,
		"pre_merge_trip_direction": None,
		"start_time": start,
		"end_time": end,
	})


class TestShiftHandoverAlignment(FrappeTestCase):
	"""AC 3.1: a day shift starting as the night shift ends is one bus run."""

	def test_the_acs_own_example_lines_up(self):
		# Outbound day shift 08:00-20:00 meeting a return night shift 20:00-08:00.
		alignment = _shift_alignment([
			_card("Outward", "08:00:00", "20:00:00"),
			_card("Return", "20:00:00", "08:00:00"),
		])

		self.assertTrue(alignment["aligned"])
		self.assertEqual(alignment["minutes_apart"], 0)

	def test_a_couple_of_hours_either_way_still_counts(self):
		alignment = _shift_alignment([
			_card("Outward", "10:00:00", "22:00:00"),
			_card("Return", "20:00:00", "08:00:00"),
		])

		self.assertEqual(alignment["minutes_apart"], 120)
		self.assertTrue(alignment["aligned"])
		self.assertEqual(SHIFT_ALIGNMENT_TOLERANCE_SECONDS, 2 * 3600)

	def test_shifts_that_do_not_meet_are_reported_not_refused(self):
		# The bus simply waits, which is a decision the dispatcher makes and the buffer
		# minutes record - not an error to block.
		alignment = _shift_alignment([
			_card("Outward", "08:00:00", "20:00:00"),
			_card("Return", "20:00:00", "14:00:00"),
		])

		self.assertFalse(alignment["aligned"])
		self.assertIn("wait", alignment["message"])

	def test_the_gap_is_measured_the_short_way_round_the_clock(self):
		# 23:00 and 01:00 are two hours apart, not twenty-two.
		alignment = _shift_alignment([
			_card("Outward", "23:00:00", "07:00:00"),
			_card("Return", "07:00:00", "01:00:00"),
		])

		self.assertEqual(alignment["minutes_apart"], 120)

	def test_a_run_with_only_one_direction_has_no_handover(self):
		alignment = _shift_alignment([
			_card("Outward", "08:00:00", "20:00:00"),
			_card("Outward", "08:00:00", "20:00:00"),
		])

		self.assertFalse(alignment["applies"])


class TestTheDriveBetweenTwoSites(FrappeTestCase):
	"""AC 3.6: dropping at Site A and collecting at Site B means driving between them."""

	def setUp(self):
		self.drop = self._shipment("Outward", "08:00:00", "20:00:00", "Site A")
		self.collect = self._shipment("Return", "20:00:00", "08:00:00", "Site B")
		self.same_site = self._shipment("Return", "20:00:00", "08:00:00", "Site A")

	def _shipment(self, direction, start, end, stop):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = "Unassigned"
		doc.trip_direction = direction
		doc.start_time = start
		doc.end_time = end
		doc.headcount = 2
		doc.stop_location = stop
		# A run needs a camp: it starts by loading there and ends by going back.
		doc.accommodation = frappe.get_all("Accommodation", limit=1, pluck="name")[0]
		doc.generation_key = frappe.generate_hash("TS-HND", 10)
		doc.flags.ignore_links = True
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_an_untimed_drive_to_another_site_blocks_the_merge(self):
		# Camp, drop at Site A, collect at Site B, home. The drive from A to B is the
		# leg OUT of the Site A row, so that is the row that has to be timed.
		preview = get_merge_preview([self.drop, self.collect])

		self.assertFalse(preview["can_merge"])
		self.assertIn("Site B", preview["handover_message"])

	def test_entering_the_drive_releases_it(self):
		preview = get_merge_preview(
			[self.drop, self.collect],
			timings={"leg-2": {"transit_minutes": 25, "buffer_minutes": 5}},
		)

		self.assertTrue(preview["can_merge"])
		self.assertEqual(preview["handover_message"], "")

	def test_a_handover_at_the_same_site_needs_no_drive(self):
		# The bus is already there: one stop, riders off then on, nothing to drive.
		preview = get_merge_preview([self.drop, self.same_site])

		handover = next(s for s in preview["stops"] if s["place"] == "Site A")
		self.assertEqual(handover["action_type"], "Combined")
		self.assertEqual(preview["handover_message"], "")


class TestTheManifestSaysWhatHappensAtTheStop(FrappeTestCase):
	"""AC 3.5: two explicit sections at a handover, from the plan rather than a copy."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# NOT reload_doc: it commits, which ends the transaction FrappeTestCase wraps
		# every test in, and everything inserted afterwards is written for real.
		# The columns come from `bench migrate`; a site without them skips.
		if not frappe.get_meta("Route Plan Assignment").get_field("action_type"):
			raise cls.skipTest(cls, "run `bench migrate`: action_type missing on Route Plan Assignment")

	def test_the_plan_records_what_happens_at_each_stop(self):
		# The BA's own field, with a third value for a stop where both movements happen.
		field = frappe.get_meta("Route Plan Assignment").get_field("action_type")

		self.assertIsNotNone(field)
		self.assertEqual(
			[o for o in (field.options or "").split("\n") if o],
			["Boarding", "Dropping Off", "Combined"],
		)

	def test_the_camp_frame_is_untouched(self):
		# `employee_action` says what the rider does at the PICKUP CAMP, and the
		# attendance-check lock keys off it. Repointing it would have broken that.
		source = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "doctype", "transportation_manifest", "manifest_sync.py"
		))

		self.assertIn(
			'action = "Dropping Off" if direction == "RETURN" else "Boarding"', source
		)

	def test_the_manifest_keeps_no_second_copy_of_it(self):
		# A stored duplicate goes stale the moment a trip is re-planned.
		self.assertIsNone(
			frappe.get_meta("Transportation Manifest Details").get_field("stop_action")
		)

	def test_the_sheet_reads_it_off_the_plan(self):
		source = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "doctype", "transportation_manifest", "manifest_sheet.py"
		))

		self.assertIn("def _stop_actions(rows)", source)
		self.assertIn('"Route Plan Assignment"', source)

	def test_the_driver_view_already_names_both_sections(self):
		# The manifest page renders one card per visit, so a handover site appears as a
		# drop-off card and a pickup card, each with its own heading.
		source = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_manifest_page",
			"transportation_manifest_page.js"
		))

		self.assertIn("DROPPING OFF EMPLOYEES", source)
		self.assertIn("EMPLOYEES BOARDING", source)
