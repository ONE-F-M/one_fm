# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002539: the minutes a trip opens on, and the two ways they used to be lost.

Every modal that asks for a drive now seeds one baseline - 15 minutes of transit, 5 of
buffer - and the server's DEFAULT_TRANSIT_MINUTES matches, so the itinerary a modal
prints is the run the blocks get drawn from.

Two separate defects sat behind AC3 and AC4:

* A leg that drives somewhere could be saved as 0 minutes, which the manifest prints as
  an instantaneous drive. It is floored to 1 on the way to the canvas - a floor on what
  is STORED, never a default nobody chose: the Trip Builder still refuses to confirm a
  blank drive, and that guard (WI-002078 AC3.6) is deliberately left standing.
* Editing one minute field reset the other to 0. The browser posted only the key it had
  just changed, and the server refilled the missing one from its own default.
"""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
	DEFAULT_TRANSIT_MINUTES,
	get_merge_preview,
)

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))


class TestTheBaselineIsOneNumber(FrappeTestCase):
	"""AC1 + AC2: 15 transit / 5 buffer, wherever the dispatcher is asked."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_server_and_the_canvas_agree_on_the_drive(self):
		# Two numbers here is the old bug in a new place: the modal would print one
		# itinerary and the blocks would be drawn on another.
		self.assertEqual(DEFAULT_TRANSIT_MINUTES, 15)
		self.assertIn("const DEFAULT_TRANSIT_MIN = 15;", self.canvas)

	def test_the_buffer_baseline_is_five(self):
		self.assertIn("const DEFAULT_BUFFER_MIN = 5;", self.canvas)

	def test_no_assignment_dialog_still_seeds_the_old_numbers(self):
		# AC1/AC2 are worthless if one entry point keeps its own default: the run would
		# be timed differently depending on which way the card was added.
		self.assertNotIn("default: 30, reqd: 1", self.canvas)
		self.assertNotIn("default: 60, reqd: 1", self.canvas)
		self.assertNotIn("vals.transit_min || 30", self.canvas)
		self.assertNotIn("(vals.buffer_min || 15)", self.canvas)

	def test_the_assign_modal_opens_the_trip_builder(self):
		# AC1: the button no longer just drops the block on the lane - it hands the
		# minutes just entered to the Trip Builder's first leg.
		self.assertIn("primary_action_label: __('Open Trip Builder'),", self.canvas)
		self.assertNotIn("primary_action_label: 'Place on Timeline',", self.canvas)
		self.assertIn("self._openMergeTripModal(null, placed, vehicleId, {", self.canvas)

	def test_what_the_modal_collected_outranks_what_the_lane_implies(self):
		self.assertIn("Object.assign(timings, seedTimings || {});", self.canvas)


class TestADriveIsNeverInstant(FrappeTestCase):
	"""AC3: a leg going somewhere never reaches the canvas at 0 minutes."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_floor_is_one_minute(self):
		self.assertIn("const MIN_LEG_TRANSIT_MIN = 1;", self.canvas)

	def test_only_a_leg_with_somewhere_onward_is_floored(self):
		# The last stop of a run has nowhere to drive to and legitimately carries no
		# transit; flooring it would invent a minute and shift the run's end.
		self.assertIn("const drives = !!(stop || {}).next_stop_location;", self.canvas)

	def test_both_stamping_paths_use_it(self):
		# The joining card and every block already on the run - one of the two used to
		# be updated without the other and the pair drifted.
		self.assertIn("transitMinutes: self._legTransit(adj),", self.canvas)
		self.assertIn("item.transitMinutes = self._legTransit(leg);", self.canvas)

	def test_the_blank_drive_guard_is_still_standing(self):
		# The floor must NOT become a way to confirm a trip nobody timed. WI-002078
		# AC3.6 blocks Confirm when a drive has no minutes, and that rule outranks the
		# convenience of never showing a 0.
		server = pathlib.Path(frappe.get_app_path(
			"one_fm", "one_fm", "doctype", "transportation_shipment",
			"transportation_shipment.py"
		)).read_text()
		self.assertIn("Every drive needs its minutes", server)
		self.assertIn('and not stop["transit_minutes"]', server)


class TestTheTwoMinuteFieldsAreIndependent(FrappeTestCase):
	"""AC4: typing in one box never empties the other."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_whole_row_is_posted_not_just_the_edited_box(self):
		self.assertIn(".querySelectorAll('.rp-leg-min')", self.canvas)
		self.assertIn("timings[ship][input.dataset.key] =", self.canvas)

	def test_the_single_key_write_is_gone(self):
		# The defect itself: one key in, the other refilled by the server's default.
		self.assertNotIn("timings[ship][key] = parseInt(this.value, 10) || 0;", self.canvas)

	def test_a_buffer_only_edit_keeps_the_server_default_transit(self):
		# What the browser used to send for a leg it had not timed yet. The server fills
		# the absent key from its own default, which is why the pair has to travel
		# together - this pins the behaviour the client is compensating for.
		from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
			_timings_by_shipment,
		)

		only_buffer = _timings_by_shipment({"leg-2": {"buffer_minutes": 10}})

		self.assertEqual(only_buffer["leg-2"].get("transit_minutes"), None)
		self.assertEqual(only_buffer["leg-2"]["buffer_minutes"], 10)


class TestASoloCardIsARunToo(FrappeTestCase):
	"""AC1's flow needs the Trip Builder to open on ONE card (also WI-002578 AC6/AC7)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def _card(self, **values):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = "Unassigned"
		doc.trip_direction = "Outward"
		doc.update(values)
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_the_preview_builds_a_round_trip_from_one_outward_card(self):
		# camp -> site -> home: the outbound drive and the run back to base, which is
		# exactly the 2-leg itinerary the Trip Builder needs to time a solo drop.
		name = self._card(accommodation="ACC-WI2539", accommodation_name="Mahboula Camp",
						  stop_location="KTech")

		preview = get_merge_preview([name])
		places = [stop["place"] for stop in preview["stops"]]

		self.assertEqual(len(places), 3)
		self.assertEqual(places[0], places[-1], "a run ends where it started")
		self.assertEqual(places[1], "KTech")

	def test_the_last_stop_has_nowhere_onward(self):
		name = self._card(accommodation="ACC-WI2539", accommodation_name="Mahboula Camp",
						  stop_location="KTech")

		preview = get_merge_preview([name])

		self.assertIsNone(preview["stops"][-1]["next_stop_location"])

	def test_an_empty_selection_is_still_refused(self):
		with self.assertRaises(frappe.ValidationError):
			get_merge_preview([])

	def test_confirm_skips_the_merge_for_a_run_of_one(self):
		# merge_trip_shipments needs two cards to mint a trip_group and throws for one,
		# so a solo run applies its preview directly and keeps its own direction.
		self.assertIn("if (shipments.length < 2) {", self.canvas)
		self.assertIn("trip_group: soloTripId,", self.canvas)

	def test_a_run_that_was_never_merged_has_nothing_to_undo(self):
		# The rejected-save rollback used to unmerge whatever the itinerary listed. A
		# solo run was never merged, and its leg keys are not shipment names.
		self.assertIn("if (!merged.merged_shipments || !merged.merged_shipments.length) {",
					  self.canvas)

	def test_edit_trip_timings_is_unblocked_for_a_single_stop(self):
		self.assertNotIn("A run needs a second stop before its legs can be timed.",
						 self.canvas)
