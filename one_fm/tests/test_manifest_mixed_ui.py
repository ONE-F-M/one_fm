# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002074: how the digital manifest renders a merged run.

Asserted against the page source. The manifest page is a rendered-HTML page rather than a
component tree, so what it emits is the only contract there is to hold - and these are the
strings a driver reads off the screen.
"""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

PAGE = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_manifest_page", "transportation_manifest_page.js"
))
MERGE_COLOUR = "#819171"


class TestTheMixedHeader(FrappeTestCase):
	def setUp(self):
		self.source = PAGE.read_text()

	def test_a_merged_run_is_badged_mixed(self):
		self.assertIn("MIXED", self.source)
		self.assertIn("mfst-mixed-badge", self.source)

	def test_the_badge_uses_the_colour_the_story_names(self):
		self.assertIn(f"background: {MERGE_COLOUR}", self.source)

	def test_the_badge_carries_the_stop_and_passenger_totals(self):
		# First criterion: total combined stop counts and cumulative passenger totals.
		self.assertIn("mixedStopCount(pr)", self.source)
		self.assertIn("mixedPassengerCount(pr, shipmentEmployees)", self.source)

	def test_the_badge_only_shows_on_a_merged_run(self):
		self.assertIn("isMixedRun(meta) ?", self.source)

	def test_a_run_is_merged_when_its_manifest_says_so(self):
		# The header field WI-002072 writes is what decides it.
		self.assertIn('meta.trip_direction', self.source)
		self.assertIn('"mixed"', self.source)

	def test_passengers_are_counted_once_across_stops(self):
		# A worker dropped and later collected is one passenger, not two.
		self.assertIn("const seen = new Set()", self.source)


class TestTheAttendanceTrigger(FrappeTestCase):
	def setUp(self):
		self.source = PAGE.read_text()

	def test_a_merged_run_triggers_only_from_the_first_depart(self):
		# Second criterion: the button belongs in the very first DEPART card and nowhere
		# else, so a driver cannot start a check at a pickup they have not reached.
		self.assertIn("seq === 1 && !activeStop", self.source)

	def test_an_ordinary_run_keeps_the_camp_by_camp_walk(self):
		# The per-camp sequential unlock is not a bug; a merged run is the exception.
		self.assertIn("seq === (activeStop || 0) + 1", self.source)

	def test_the_two_rules_are_chosen_between_not_merged(self):
		self.assertIn("isMixed", self.source)

	def test_the_depart_card_is_told_which_run_it_is_on(self):
		self.assertIn(
			"renderDepartCard(time, camp, activeStop, manifestName, vehicleLabel, isMixed)",
			self.source,
		)
		# The merged branch owns the origin card and passes true; the camp-by-camp branch
		# is never a merged run and passes false, so the two rules cannot cross over.
		self.assertIn("o.activeStop, o.manifestName, o.vehicleLabel, true", self.source)
		self.assertIn("renderDepartCard(firstTimeISO, cg, activeStop, manifestName, pr.label, false)", self.source)


class TestTheStopLabels(FrappeTestCase):
	def setUp(self):
		self.source = PAGE.read_text()

	def test_boarding_blocks_say_employees_boarding(self):
		# Fifth criterion, verbatim - the driver reads the same words on every block.
		self.assertIn("EMPLOYEES BOARDING", self.source)

	def test_drop_off_blocks_say_dropping_off_employees(self):
		self.assertIn("DROPPING OFF EMPLOYEES", self.source)

	def test_the_label_follows_what_happens_at_the_stop(self):
		self.assertIn(
			'isDropoff ? "DROPPING OFF EMPLOYEES" : "EMPLOYEES BOARDING"', self.source
		)

	def test_the_old_count_first_wording_is_gone(self):
		# "Dropping off 4 employees" varied with the count and buried the action.
		self.assertNotIn('"Dropping off"', self.source)
		self.assertNotIn('"Picking up"', self.source)


class TestDriveTimeConnectors(FrappeTestCase):
	"""Third criterion: connector badges between consecutive stops. Already built for the
	camp-by-camp view; asserted here so a merged run cannot lose them."""

	def setUp(self):
		self.source = PAGE.read_text()

	def test_stops_are_joined_by_a_transit_badge(self):
		self.assertIn("renderTransit(", self.source)

	def test_the_gap_is_measured_between_consecutive_stops(self):
		self.assertIn("calcTransit(prevTime,", self.source)


class TestThePageIsGivenWhatItNeeds(FrappeTestCase):
	"""The gap the reporter found, and the one the source assertions above could not see.

	Every criterion here is gated on the page knowing the run is merged and knowing which
	way each card's own riders travel. Neither was in the payload, so the MIXED badge never
	rendered, the merged attendance rule never applied, and every stop was drawn twice -
	once as PICK UP and once as DROP OFF - while the assertions on the page source all
	passed. These check the data actually arrives.
	"""

	def setUp(self):
		self.plan = frappe.db.get_value("Route Plan", {"status": "Active"}, "name")
		if not self.plan:
			self.skipTest("No Active Route Plan on this site")

	def _payload(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			get_manifest_data_for_plan,
		)
		return get_manifest_data_for_plan(self.plan)["route_data"]

	def test_every_vehicle_is_told_its_run_direction(self):
		for label, meta in self._payload()["vehicleMeta"].items():
			with self.subTest(vehicle=label):
				self.assertIn("trip_direction", meta)
				self.assertIn("trip_group", meta)

	def test_a_merged_vehicle_reports_mixed(self):
		merged = frappe.get_all(
			"Transportation Manifest", filters={"trip_direction": "Mixed"},
			fields=["vehicle_no"], limit_page_length=1,
		)
		if not merged:
			self.skipTest("No merged manifest on this site")

		meta = self._payload()["vehicleMeta"].get(merged[0].vehicle_no)
		if not meta:
			self.skipTest("That vehicle is not on the active plan")

		self.assertEqual(str(meta["trip_direction"]).lower(), "mixed")

	def test_every_card_says_which_way_its_own_riders_travel(self):
		payload = self._payload()
		own = payload["shipmentOwnDirections"]

		self.assertTrue(own, "shipmentOwnDirections is empty")
		for label in (s["label"] for s in payload["request"]["model"]["shipments"]):
			with self.subTest(label=label):
				self.assertIn(label, own)

	def test_that_answer_is_never_mixed(self):
		# "Mixed" is how a card is scheduled. The page has to draw either a drop-off or a
		# boarding, so a third value leaves it drawing both.
		for label, direction in self._payload()["shipmentOwnDirections"].items():
			with self.subTest(label=label):
				self.assertIn(direction, ("OUTBOUND", "RETURN"))

	def test_a_merged_card_keeps_the_direction_it_was_generated_for(self):
		from one_fm.operations.doctype.route_plan.route_plan import _card_direction

		payload = self._payload()
		for label, direction in payload["shipmentOwnDirections"].items():
			if not label.endswith("_MIXED"):
				continue
			with self.subTest(label=label):
				self.assertIn(direction, ("OUTBOUND", "RETURN"))
				self.assertEqual(direction, _card_direction("Mixed", direction.title().replace("Outbound", "Outward")))


class TestTheMergedItinerary(FrappeTestCase):
	"""AC3: one chronological list, not an outbound pass followed by a return pass."""

	def setUp(self):
		self.source = PAGE.read_text()

	def test_a_merged_run_has_its_own_itinerary(self):
		self.assertIn("function renderMixedItinerary(o) {", self.source)
		self.assertIn("if (isMixed) {", self.source)

	def test_each_card_contributes_one_stop_not_two(self):
		# The filter used to enumerate OUTBOUND and RETURN, so MIXED matched neither and
		# both the pickup visit and the drop-off visit survived.
		self.assertIn("const own = stop.ownDirection || stop.direction;", self.source)
		self.assertIn('if (own === "OUTBOUND" && stop.type === "pickup") return;', self.source)
		self.assertIn('if (own === "RETURN" && stop.type === "dropoff") return;', self.source)

	def test_a_merged_stop_does_not_also_get_a_synthetic_return(self):
		# On a merged run the collection is a real card of its own.
		self.assertIn('stop.direction !== "MIXED"', self.source)

	def test_the_list_is_ordered_by_time_with_the_drop_off_first_on_a_tie(self):
		self.assertIn('(a.type === "dropoff" ? 0 : 1) - (b.type === "dropoff" ? 0 : 1)', self.source)

	def test_only_the_riders_being_set_down_leave_the_origin(self):
		self.assertIn('const into = stop.type === "dropoff" ? boarding : returning;', self.source)

	def test_the_badge_counts_the_stops_the_driver_works(self):
		# It read pr.route.stops, which does not exist - so the badge would have said
		# "0 stops · 0 passengers" even once it rendered.
		self.assertNotIn("pr.route.stops", self.source)
		self.assertIn("function mixedItineraryStops(pr) {", self.source)

	def test_the_trip_header_is_neither_outbound_nor_return(self):
		self.assertIn('const dirClass = isMixed ? "mixed"', self.source)
		self.assertIn(".mfst-trip-group.mixed", self.source)

	def test_the_header_uses_the_merge_colour(self):
		self.assertIn(f"--mfst-mixed: {MERGE_COLOUR}", self.source)
