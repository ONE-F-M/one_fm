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
		doc.generation_key = frappe.generate_hash("TS-HND", 10)
		doc.flags.ignore_links = True
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_an_untimed_drive_to_another_site_blocks_the_merge(self):
		preview = get_merge_preview([self.drop, self.collect],
									timings={self.collect: {"transit_minutes": 0, "buffer_minutes": 0}})

		self.assertFalse(preview["can_merge"])
		self.assertIn("Site B", preview["handover_message"])
		self.assertTrue(preview["stops"][1]["needs_drive"])
		self.assertTrue(preview["stops"][1]["untimed_handover"])

	def test_entering_the_drive_releases_it(self):
		preview = get_merge_preview([self.drop, self.collect],
									timings={self.collect: {"transit_minutes": 25, "buffer_minutes": 5}})

		self.assertTrue(preview["can_merge"])
		self.assertEqual(preview["handover_message"], "")
		self.assertFalse(preview["stops"][1]["untimed_handover"])

	def test_a_handover_at_the_same_site_needs_no_drive(self):
		# The bus is already there; the AC's rule is about Site A to Site B.
		preview = get_merge_preview([self.drop, self.same_site],
									timings={self.same_site: {"transit_minutes": 0, "buffer_minutes": 0}})

		self.assertFalse(preview["stops"][1]["needs_drive"])
		self.assertTrue(preview["can_merge"])


class TestTheManifestSaysWhatHappensAtTheStop(FrappeTestCase):
	"""AC 3.5: two explicit sections at a handover, from stored data not a guess."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# The column is new, so a site that has not migrated yet has it in the JSON but
		# not in the schema. Syncing here proves the definition is loadable.
		frappe.reload_doc("one_fm", "doctype", "transportation_manifest_details")

	def test_the_row_records_the_stop_frame_as_well_as_the_camp_frame(self):
		meta = frappe.get_meta("Transportation Manifest Details")

		self.assertIsNotNone(meta.get_field("stop_action"))
		self.assertIsNotNone(meta.get_field("employee_action"))

	def test_the_two_frames_are_opposites(self):
		# An outward rider boards at the camp and is dropped at the site; a return rider
		# is dropped at the camp and boards at the site. Recording only one of the two is
		# what left the manifest unable to describe a handover.
		source = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "doctype", "transportation_manifest", "manifest_sync.py"
		))

		self.assertIn(
			'action = "Dropping Off" if direction == "RETURN" else "Boarding"', source
		)
		self.assertIn(
			'stop_action = "Boarding" if direction == "RETURN" else "Dropping Off"', source
		)

	def test_the_printed_sheet_carries_it(self):
		source = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "doctype", "transportation_manifest", "manifest_sheet.py"
		))

		self.assertIn('"stop_action": row.stop_action', source)

	def test_the_driver_view_already_names_both_sections(self):
		# The manifest page renders one card per visit, so a handover site appears as a
		# drop-off card and a pickup card, each with its own heading.
		source = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_manifest_page",
			"transportation_manifest_page.js"
		))

		self.assertIn("DROPPING OFF EMPLOYEES", source)
		self.assertIn("EMPLOYEES BOARDING", source)
