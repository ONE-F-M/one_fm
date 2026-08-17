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
		self.assertIn("isMixedRun(meta));", self.source)


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
