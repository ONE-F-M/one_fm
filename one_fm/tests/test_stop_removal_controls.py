# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""taking stops off a lane - one, several, or the whole run.

The drawer could only ever remove the ONE stop that was selected. A run being taken
apart went a stop at a time, each removal its own save.

The three controls differ only in which block ids they collect; everything after that -
a run that may now travel one way, a card with nothing left on any lane going back to
the pool, the plan being written - is identical, and used to live inside
removeSelectedFromLane alone. A second copy that forgot _resyncTripDirection would leave
a run flagged MIXED after the stop that made it mixed had gone, so there is one path.

Both of the WI's notes fall out of the existing save rather than needing new code:
save_assignments rewrites the Route Plan's assignment rows, and _sync_shipment_statuses
reverts every shipment the plan just dropped back to Unassigned. This file pins that
those two still hold, so a future change to the removal path cannot quietly strand a
card as Assigned with no block on any lane.
"""

import inspect
import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	_sync_shipment_statuses,
)

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))


class TestTheThreeRemovalControls(FrappeTestCase):
	"""AC1: one stop, several stops, or the entire trip block."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_every_control_goes_through_one_removal_path(self):
		self.assertIn("_removeItems(itemIds) {", self.canvas)
		for control in ("removeSelectedFromLane", "removeCheckedStops", "removeEntireTrip"):
			self.assertIn(f"{control}(", self.canvas)
		# Three calls into it, one per control.
		self.assertEqual(self.canvas.count("this._removeItems("), 2)
		self.assertEqual(self.canvas.count("self._removeItems("), 1)

	def test_the_old_single_stop_body_is_gone(self):
		# Left in place it would have been a second, diverging copy of the same rules.
		self.assertNotIn("// Remove only the selected block, not both directions", self.canvas)

	def test_a_run_left_one_way_is_resynced_for_every_trip_touched(self):
		# A multi-stop removal can empty stops from more than one run at once, so the
		# direction resync is per trip rather than on a single tripId.
		self.assertIn("trips.forEach((tripId) => this._resyncTripDirection(tripId));",
					  self.canvas)

	def test_a_card_returns_to_the_pool_only_when_nothing_of_it_is_left(self):
		# A card placed in BOTH directions keeps its sidebar entry while one leg stands.
		self.assertIn("if (!this.swimItems.some(i => i.cardId === cardId)) {", self.canvas)

	def test_removing_the_whole_trip_is_confirmed_first(self):
		# It can take a dozen stops off the board and there is no undo.
		self.assertIn("frappe.confirm(", self.canvas)
		self.assertIn("removeEntireTrip() {", self.canvas)

	def test_the_multi_select_is_offered_in_the_drawer(self):
		self.assertIn('type="checkbox" class="rp-stop-check"', self.canvas)
		self.assertIn('@click.stop="toggleStopChecked(stop.item.id)"', self.canvas)

	def test_ticking_a_stop_does_not_also_select_it(self):
		# The stop card's own click means "act on this one"; without .stop the tick
		# would do both and the footer buttons would change under the cursor.
		self.assertIn('@click.stop="toggleStopChecked', self.canvas)

	def test_the_buttons_appear_only_when_they_would_do_something(self):
		self.assertIn('v-if="checkedStopIds.length > 0"', self.canvas)
		self.assertIn('v-if="selectedTripStops.length > 1"', self.canvas)


class TestTicksCannotLeakBetweenRuns(FrappeTestCase):
	"""A tick left on one run must never be swept up by a removal made on another."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_action_reads_the_scoped_list_not_the_raw_set(self):
		self.assertIn("const removed = this._removeItems(this.checkedStopIds);", self.canvas)
		self.assertNotIn("this._removeItems([...this.selectedStopIds])", self.canvas)

	def test_the_scope_is_the_run_the_drawer_is_showing(self):
		self.assertIn("checkedStopIds() {", self.canvas)
		self.assertIn("return this.selectedTripStops", self.canvas)

	def test_closing_the_drawer_drops_the_ticks(self):
		self.assertIn("this.selectedStopIds.clear();", self.canvas)

	def test_the_ticks_are_cleared_after_a_removal(self):
		# Otherwise the next run opened would show a count for stops that no longer exist.
		body = self.canvas.split("_removeItems(itemIds) {", 1)[1].split("\n            },", 1)[0]
		self.assertIn("this.selectedStopIds.clear();", body)


class TestRemovalStillReachesTheDocuments(FrappeTestCase):
	"""The WI's two notes: the Route Plan and the shipment status both follow the save."""

	def _card(self, **values):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = "Assigned"
		doc.trip_direction = "Outward"
		doc.update(values)
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_a_dropped_card_reverts_to_unassigned(self):
		# "Removing Stops should update Transportation Shipment doctype and change the
		# status to Unassigned." The plan carried it; after the removal it places
		# nothing, so the sync sends it back to the pool.
		name = self._card()

		_sync_shipment_statuses([], previously_linked={name})

		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "status"), "Unassigned"
		)

	def test_a_card_still_on_a_lane_is_left_alone(self):
		# Removing one stop of a run must not send the stops beside it back to the pool.
		name = self._card()

		_sync_shipment_statuses(
			[{"cardId": f"TSHIP-{name}", "direction": "OUTBOUND"}],
			previously_linked={name},
		)

		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "status"), "Assigned"
		)

	def test_the_removal_writes_the_plan_immediately(self):
		# "Removing Stops should update Route Plan doctype instantly." The removal path
		# ends in persistAssignments, which posts the whole board straight away.
		canvas = CANVAS.read_text()
		body = canvas.split("_removeItems(itemIds) {", 1)[1].split("\n            },", 1)[0]
		self.assertIn("this.persistAssignments();", body)

	def test_the_plan_rewrites_its_rows_from_what_is_left(self):
		from one_fm.one_fm.page.transportation_schedule import transportation_schedule

		source = inspect.getsource(transportation_schedule.save_assignments)
		self.assertIn("doc.assignments = []", source)
		self.assertIn("_sync_shipment_statuses(items, previously_linked)", source)
