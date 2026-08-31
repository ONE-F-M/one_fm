# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002151: a run is timed forward from a stated departure, not backwards from a shift.

The trip modal used to place the first stop by backing into the shift time the card is
scheduled on. The dispatcher now states when the vehicle leaves and every arrival is
calculated forward from it, with the driver's QOA report time derived from the same
departure and a `(+1 Day)` badge wherever a leg crosses midnight.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
	QOA_BUFFER_FIELD,
	_departure_seconds,
	build_itinerary,
	day_offset,
	get_merge_preview,
	qoa_buffer_minutes,
	walk_legs,
)
from one_fm.operations.doctype.route_plan.route_plan import card_rows
from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	_camp_place_for,
	_stamp_leg_details,
)
from one_fm.patches.v15_0.add_transportation_qoa_buffer_to_hr_settings import (
	execute as add_qoa_buffer_field,
)

HOUR = 3600


class TestTheRunWalksForward(FrappeTestCase):
	"""AC 1.1: arrival = departure + buffer + transit, cascading down the run."""

	LEGS = [(30, 10), (20, 5), (15, 0)]  # (transit, buffer) per stop

	def test_a_stated_departure_drives_the_first_stop(self):
		walked = walk_legs(self.LEGS, anchor=12 * HOUR, departure=6 * HOUR)

		# Leaves at 06:00, arrives 10 buffer + 30 transit later.
		self.assertEqual(walked[0], (6 * HOUR, 6 * HOUR + 40 * 60))

	def test_every_later_stop_is_driven_from_the_one_before(self):
		walked = walk_legs(self.LEGS, anchor=12 * HOUR, departure=6 * HOUR)

		# A leg departs when the bus is released from the stop before it, and its buffer
		# is dwell inside the leg - so Arrival = Departure + Buffer + Transit reads
		# literally, which is how the process owner's sample itinerary is walked.
		first_arrival = walked[0][1]
		self.assertEqual(walked[1][0], first_arrival)
		self.assertEqual(walked[1][1], walked[1][0] + (5 + 20) * 60)

	def test_editing_a_leg_high_up_moves_everything_after_it(self):
		slower = [(30, 10), (60, 5), (15, 0)]

		base = walk_legs(self.LEGS, anchor=12 * HOUR, departure=6 * HOUR)
		moved = walk_legs(slower, anchor=12 * HOUR, departure=6 * HOUR)

		self.assertEqual(moved[0], base[0])                             # untouched
		self.assertEqual(moved[2][1] - base[2][1], 40 * 60)             # +40 min downstream

	def test_without_a_departure_it_still_backs_into_the_shift_time(self):
		# Every caller that has no departure to give keeps the old reading, which is what
		# lets a run that nobody has re-timed sit exactly where it always did.
		walked = walk_legs(self.LEGS, anchor=12 * HOUR)

		self.assertEqual(walked[0][1], 12 * HOUR)
		self.assertEqual(walked[0][0], 12 * HOUR - 40 * 60)


class TestMidnightRollover(FrappeTestCase):
	"""AC 1.6: a leg that crosses midnight says which day it lands on."""

	def test_a_run_inside_one_day_has_no_offset(self):
		self.assertEqual(day_offset(23 * HOUR), 0)

	def test_a_leg_past_midnight_rolls_the_day(self):
		self.assertEqual(day_offset(24 * HOUR + 30 * 60), 1)

	def test_the_walk_carries_past_midnight_rather_than_wrapping(self):
		walked = walk_legs([(0, 0), (90, 0)], anchor=0, departure=23 * HOUR)

		self.assertGreater(walked[1][1], 24 * HOUR)
		self.assertEqual(day_offset(walked[1][1]), 1)

	def test_a_missing_stamp_has_no_offset(self):
		self.assertEqual(day_offset(None), 0)


class TestTheStatedDepartureIsRead(FrappeTestCase):
	"""The modal sends a clock string; a Time column hands back a timedelta."""

	def test_a_clock_string_is_read(self):
		self.assertEqual(_departure_seconds("05:30"), 5 * HOUR + 30 * 60)
		self.assertEqual(_departure_seconds("05:30:45"), 5 * HOUR + 30 * 60 + 45)

	def test_a_blank_means_nothing_was_stated(self):
		self.assertIsNone(_departure_seconds(""))
		self.assertIsNone(_departure_seconds(None))

	def test_rubbish_is_not_mistaken_for_midnight(self):
		# Falling back to 0 would silently move a run to midnight.
		self.assertIsNone(_departure_seconds("not a time"))


class TestTheQoaBuffer(FrappeTestCase):
	"""AC 1.2: the driver's report-time buffer, read from HR Settings in one place."""

	def test_it_reads_what_hr_configured(self):
		add_qoa_buffer_field()
		frappe.db.set_single_value("HR Settings", QOA_BUFFER_FIELD, 45)

		self.assertEqual(qoa_buffer_minutes(), 45)

	def test_unset_means_no_buffer_rather_than_a_guess(self):
		add_qoa_buffer_field()
		frappe.db.set_single_value("HR Settings", QOA_BUFFER_FIELD, 0)

		# QOA Time then equals the departure time, which changes nothing on any trip.
		self.assertEqual(qoa_buffer_minutes(), 0)

	def test_it_is_named_apart_from_the_manifest_qoa(self):
		# `qoa_status` / `qoa_reason` on the manifest are a pass/fail attendance check and
		# have nothing to do with a report time. The two must not collide in a field list.
		self.assertTrue(QOA_BUFFER_FIELD.startswith("custom_transportation_"))


class TestTheRunEndsAtTheCamp(FrappeTestCase):
	"""AC 1.5, literally now that a run is its stops: the last one is the base camp."""

	def _card(self, camp, site, direction):
		return frappe._dict({
			"name": frappe.generate_hash("TS", 6),
			"accommodation": camp, "accommodation_name": camp, "stop_location": site,
			"headcount": 2, "trip_direction": direction, "pre_merge_trip_direction": None,
		})

	def test_every_run_finishes_back_at_the_camp_it_started_from(self):
		stops = build_itinerary([
			self._card("Camp 1", "Site A", "Outward"),
			self._card("Camp 1", "Site A", "Return"),
		])

		self.assertEqual(stops[-1]["kind"], "home")
		self.assertEqual(stops[-1]["place"], "Camp 1")

	def test_a_plain_outbound_run_still_drives_home_empty(self):
		# The sheet shows it too: the last row is the camp with nobody aboard.
		stops = build_itinerary([self._card("Camp 1", "Site A", "Outward")])

		self.assertEqual(stops[-1]["kind"], "home")
		self.assertEqual(stops[-1]["drop_off_count"], 0)

	def test_a_run_with_no_camp_has_nowhere_to_go_home_to(self):
		stops = build_itinerary([frappe._dict({
			"name": "X", "accommodation": None, "accommodation_name": None,
			"stop_location": "Site A", "headcount": 2,
			"trip_direction": "Outward", "pre_merge_trip_direction": None,
		})])

		self.assertFalse([s for s in stops if s["kind"] == "home"])


class TestThePreviewTheModalDraws(FrappeTestCase):
	"""End to end on real shipment records: what the trip modal is handed."""

	def setUp(self):
		add_qoa_buffer_field()
		frappe.db.set_single_value("HR Settings", QOA_BUFFER_FIELD, 45)
		self.outward = self._shipment("Outward", "08:00:00", "20:00:00")
		self.back = self._shipment("Return", "20:00:00", "08:00:00")

	def _shipment(self, direction, start, end):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = "Unassigned"
		doc.trip_direction = direction
		doc.start_time = start
		doc.end_time = end
		doc.headcount = 2
		doc.stop_location = "Site Stop"
		doc.accommodation = frappe.get_all("Accommodation", limit=1, pluck="name")[0]
		doc.generation_key = frappe.generate_hash("TS-FWD", 10)
		doc.flags.ignore_links = True
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def _preview(self, **kwargs):
		return get_merge_preview([self.outward, self.back], **kwargs)

	def test_it_seeds_the_departure_the_run_would_have_left_on(self):
		# Nothing moves until the dispatcher says otherwise.
		preview = self._preview()

		self.assertEqual(preview["departure"], preview["default_departure"])

	def test_a_stated_departure_moves_the_whole_run(self):
		stated = self._preview(departure="05:30")

		self.assertEqual(stated["departure"], "05:30")
		self.assertEqual(stated["stops"][0]["departs"], "05:30")

	def test_qoa_is_shown_only_on_the_leg_that_leaves_the_camp(self):
		stops = self._preview(departure="05:30")["stops"]

		# 05:30 less the 45 minute buffer HR configured.
		self.assertEqual(stops[0]["qoa_time"], "04:45")
		self.assertIsNone(stops[1]["qoa_time"])

	def test_the_time_the_modal_seeds_its_field_with_carries_seconds(self):
		# A Frappe Time control refuses "09:00" outright.
		self.assertEqual(self._preview(departure="05:30")["departure_input"], "05:30:00")

	def test_a_second_leg_out_of_the_same_camp_does_not_report_again(self):
		# Riders from two cards at one camp board together once, so only the first leg
		# actually departs it. The saved assignment row is stamped by the same rule.
		second = self._shipment("Outward", "09:00:00", "21:00:00")
		stops = get_merge_preview([self.outward, second])["stops"]

		self.assertTrue(stops[0]["is_accommodation_origin"])
		self.assertFalse(stops[1]["is_accommodation_origin"])
		self.assertIsNone(stops[1]["qoa_time"])

	def test_each_stop_names_itself_and_where_the_bus_goes_next(self):
		stops = self._preview()["stops"]

		# A row is a place the bus stops at now. "Next stop" is where it goes from here,
		# and "shift location" is where the riders it serves are headed - which is a
		# different thing the moment a run collects from several camps before dropping
		# anyone.
		for here, onward in zip(stops, stops[1:]):
			self.assertEqual(here["next_stop_location"], onward["place"])
		self.assertIsNone(stops[-1]["next_stop_location"])
		self.assertEqual(stops[0]["kind"], "camp")
		self.assertEqual(stops[-1]["kind"], "home")

	def test_the_modal_is_told_the_run_ends_at_the_camp(self):
		preview = self._preview()

		self.assertTrue(preview["ends_at_base_camp"])
		self.assertEqual(preview["route_message"], "")

	def test_the_shift_the_canvas_applies_is_a_duration_not_an_instant(self):
		# The blocks are moved by the difference between the two, so the browser never
		# has to rebuild a moment in time from a clock string - and an untouched run
		# yields a shift of exactly zero, so nothing on the board moves.
		untouched = self._preview()
		self.assertEqual(
			untouched["departure_seconds"] - untouched["default_departure_seconds"], 0
		)

		stated = self._preview(departure="05:30")
		self.assertEqual(stated["departure_seconds"], 5 * HOUR + 30 * 60)
		self.assertEqual(
			stated["departure_seconds"] - stated["default_departure_seconds"],
			5 * HOUR + 30 * 60 - untouched["departure_seconds"],
		)


class TestTheProcessOwnersSampleItinerary(FrappeTestCase):
	"""The two runs in Transport.xlsx, walked leg by leg.

	The sheet is the process owner's statement of how the cascade should read, so it is
	replayed here rather than paraphrased: if the walk ever drifts from it, these fail.
	"""

	def _clock(self, seconds):
		seconds = int(seconds) % 86400
		return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}"

	def _walk(self, departure, legs):
		hh, mm = departure.split(":")
		walked = walk_legs(legs, anchor=0, departure=int(hh) * HOUR + int(mm) * 60)
		return [(self._clock(d), self._clock(a)) for d, a in walked]

	def test_scenario_one_camp_to_site_and_back(self):
		# 09:00 out with 10 buffer + 50 transit, arriving 10:00 for a 10:00 shift start,
		# then the same again back to the camp for 11:00.
		self.assertEqual(
			self._walk("09:00", [(50, 10), (50, 10)]),
			[("09:00", "10:00"), ("10:00", "11:00")],
		)

	def test_scenario_two_three_camps_two_sites_and_a_collection(self):
		walked = self._walk("08:00", [(15, 5), (10, 5), (5, 1), (4, 0), (5, 5), (8, 2)])

		self.assertEqual(walked, [
			("08:00", "08:20"),   # Accommodation 1 -> Accommodation 2
			("08:20", "08:35"),   # Accommodation 2 -> Accommodation 3
			("08:35", "08:41"),   # Accommodation 3 -> Grand Hayat
			("08:41", "08:45"),   # Grand Hayat     -> 360 Car Park
			("08:45", "08:55"),   # 360 Car Park    -> Khaldiya
			("08:55", "09:05"),   # Khaldiya        -> Accommodation 1
		])

	def test_every_departure_is_the_previous_arrival(self):
		walked = self._walk("08:00", [(15, 5), (10, 5), (5, 1), (4, 0), (5, 5), (8, 2)])

		for previous, current in zip(walked, walked[1:]):
			self.assertEqual(current[0], previous[1])

	def test_the_report_time_the_sample_uses_is_a_quarter_hour(self):
		# 09:00 departure reports 08:45; 08:20 reports 08:05; 08:35 reports 08:20.
		add_qoa_buffer_field()

		self.assertEqual(
			frappe.db.get_default(QOA_BUFFER_FIELD)
			or frappe.get_meta("HR Settings").get_field(QOA_BUFFER_FIELD).default,
			"15",
		)


class TestEachLegRecordsItsOwnFacts(FrappeTestCase):
	"""The BA's Route Plan Assignment fields, written on save.

	A row that carries only a timestamp cannot answer what the trip modal showed - where
	the leg started, the driver's report time, how full the bus was leaving that stop,
	whether it rolled past midnight - and the manifest and every later reader need those.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# NOT reload_doc: it commits, which ends the transaction FrappeTestCase wraps
		# every test in, and everything inserted afterwards is written for real.
		# The columns come from `bench migrate`; a site without them skips.
		if not frappe.get_meta("Route Plan Assignment").get_field("stop_index"):
			raise cls.skipTest(cls, "run `bench migrate`: stop_index missing on Route Plan Assignment")

	def setUp(self):
		locations = frappe.get_all("Location", limit=1, pluck="name")
		if not locations:
			self.skipTest("no Location on this site to hang a stop on")
		self.site = locations[0]
		camps = frappe.get_all("Accommodation", limit=1, pluck="name")
		if not camps:
			self.skipTest("no Accommodation on this site for the run to depart")
		self.camp = camps[0]
		add_qoa_buffer_field()
		frappe.db.set_single_value("HR Settings", QOA_BUFFER_FIELD, 15)
		self.drop = self._shipment("Outward", "08:00:00")
		self.collect = self._shipment("Return", "20:00:00")

	def _shipment(self, direction, start):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = "Unassigned"
		doc.trip_direction = direction
		doc.start_time = start
		doc.end_time = "20:00:00" if direction == "Outward" else "08:00:00"
		doc.stop_location = self.site
		doc.accommodation = self.camp
		# Riders, not just a number: the controller derives headcount from this table on
		# every save, so a fixture that only sets the field is a card carrying nobody -
		# and the seat walk now reads the shipment rather than the stored row (#6818).
		for n in range(4):
			doc.append("transportation_shipment_employee", {
				"employee_id": f"{direction[:3].upper()}-{n:02d}",
				"employee_name": f"Rider {n}",
			})
		doc.generation_key = frappe.generate_hash("TS-LEG", 10)
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def _plan(self, leg_timings=None):
		"""The card rows of a saved run - the stops the bus makes that carry a card."""
		return card_rows(self._doc(leg_timings).assignments)

	def _doc(self, leg_timings=None):
		"""A handover: 4 dropped and 4 collected at the same site, on one vehicle."""
		vehicle = frappe.get_all("Vehicle", filters={"transport_stop_vehicle": 1},
								 limit=1, pluck="name")
		if not vehicle:
			self.skipTest("no transport vehicle on this site")
		doc = frappe.new_doc("Route Plan")
		doc.title = frappe.generate_hash("RP-LEG", 8)
		for index, shipment in enumerate((self.drop, self.collect), start=1):
			doc.append("assignments", {
				"card_id": f"TSHIP-{shipment}",
				"transportation_shipment": shipment,
				"vehicle": vehicle[0],
				"direction": "OUTBOUND" if index == 1 else "RETURN",
				"trip_group": "RUN-1",
				"stop_index": index,
				"headcount": 4,
				"stop_location": self.site,
				"start_time": "2026-08-18T05:00:00.000Z",
				"end_time": "2026-08-18T06:00:00.000Z",
			})
		_stamp_leg_details(doc, leg_timings)
		return doc

	def test_the_camp_the_bus_loads_at_is_a_row_of_its_own(self):
		# The plan lists every stop of the run, so the table reads like the sheet. The
		# camp is a stop no card is filed against, and before this it had no row at all.
		camp = [
			row for row in self._doc().assignments
			if row.is_camp_leg and not row.is_home_leg
		]

		self.assertEqual(len(camp), 1)
		self.assertEqual(camp[0].action_type, "Boarding")
		# The camp is the first thing the bus does, before any site.
		self.assertEqual(camp[0].stop_index, 1)

	def test_a_camp_row_carries_no_riders_of_its_own(self):
		# It describes a stop, it is not a placement: a headcount here would be counted a
		# second time by everything that sums the column.
		camp = next(row for row in self._doc().assignments
					if row.is_camp_leg and not row.is_home_leg)

		self.assertEqual(camp.headcount, 0)

	def test_the_camp_row_keeps_the_minutes_typed_against_it(self):
		# The whole point: the drive out of the camp had nowhere to be recorded, so the
		# Trip Builder took the numbers and the plan forgot them.
		place = _camp_place_for(frappe._dict(accommodation=self.camp, accommodation_name=None))
		camp = next(
			row for row in self._doc({"RUN-1": {"camps": {place: {
				"transit_minutes": 25, "buffer_minutes": 5,
			}}}}).assignments
			if row.is_camp_leg and not row.is_home_leg
		)

		self.assertEqual((camp.transit_minutes, camp.buffer_minutes), (25, 5))

	def test_the_camp_row_keeps_the_departure_the_dispatcher_stated(self):
		# It cannot be read back off the blocks: the first block is the first SITE, which
		# the bus reaches after the camp leg, so a reload would guess it wrong.
		camp = next(
			row for row in self._doc({"RUN-1": {
				"departure": "2026-08-18T04:30:00.000Z", "camps": {},
			}}).assignments
			if row.is_camp_leg and not row.is_home_leg
		)

		self.assertEqual(camp.start_time, "2026-08-18T04:30:00.000Z")

	def test_the_ride_home_is_a_row_of_its_own(self):
		# The last thing the bus does, and the only leg nothing is dropped at - so the
		# drawer had nothing to show for the drive back and the run appeared to end at
		# its last site.
		if not frappe.get_meta("Route Plan Assignment").get_field("is_home_leg"):
			self.skipTest("run `bench migrate`: is_home_leg missing on Route Plan Assignment")

		home = [row for row in self._doc({"RUN-1": {
			"arrival": "2026-08-18T09:30:00.000Z",
			"home": {"transit_minutes": 26, "buffer_minutes": 0},
		}}).assignments if row.is_home_leg]

		self.assertEqual(len(home), 1)
		self.assertEqual(home[0].end_time, "2026-08-18T09:30:00.000Z")
		self.assertEqual(home[0].transit_minutes, 26)
		self.assertEqual(home[0].headcount, 0)

	def test_the_camp_row_names_the_journey_it_belongs_to(self):
		# Optional link, per the dispatcher: the row can be traced back to a card without
		# ever standing in for one.
		camp = next(row for row in self._doc().assignments
					if row.is_camp_leg and not row.is_home_leg)

		self.assertEqual(camp.trip_group, "RUN-1")
		self.assertIn(camp.transportation_shipment, (self.drop, self.collect))

	def test_a_stop_that_sheds_and_takes_on_is_combined(self):
		# Both movements happen at one place, which is what a handover is.
		self.assertEqual({row.action_type for row in self._plan()}, {"Combined"})

	def test_the_counts_are_split_by_which_way_the_riders_go(self):
		dropped, collected = self._plan()

		self.assertEqual((dropped.drop_off_count, dropped.boarding_count), (4, 0))
		self.assertEqual((collected.drop_off_count, collected.boarding_count), (0, 4))

	def test_occupancy_is_walked_disembark_first(self):
		# Both cards are served at the same place, so both rows describe that one stop:
		# 4 off, then 4 on, leaving 4 aboard. The bus never holds 8, which is the point -
		# and it is the same walk the seat check and the trip modal use.
		dropped, collected = self._plan()

		self.assertEqual(dropped.current_passenger_count, 4)
		self.assertEqual(collected.current_passenger_count, 4)
		self.assertEqual(dropped.stop_index, collected.stop_index)
		self.assertEqual(dropped.action_type, "Combined")

	def test_only_the_leg_that_leaves_the_camp_reports(self):
		dropped, collected = self._plan()

		self.assertTrue(dropped.is_accommodation_origin)
		self.assertFalse(collected.is_accommodation_origin)
		self.assertIsNone(collected.qoa_time)

	def test_the_report_time_is_the_departure_less_the_hr_buffer(self):
		dropped, _collected = self._plan()

		# 05:00Z is 08:00 in Kuwait; 15 minutes before that is 07:45.
		self.assertEqual(str(dropped.qoa_time), "07:45:00")

	def test_the_seat_count_is_recorded_against_the_leg(self):
		dropped, _collected = self._plan()

		self.assertGreater(dropped.max_passenger_capacity, 0)

	def test_the_shift_it_serves_is_recorded(self):
		dropped, _collected = self._plan()

		self.assertEqual(str(dropped.shift_start_time), "8:00:00")


class TestTheManifestPrintsTheCascade(FrappeTestCase):
	"""WI-002151's manifest AC: what a driver reads has to be what the modal calculated."""

	def _source(self, *path):
		return frappe.read_file(frappe.get_app_path("one_fm", *path))

	def test_a_stop_prints_its_scheduled_arrival(self):
		# It printed an outward leg's DEPARTURE before, and in UTC. end_time is when the
		# bus reaches this leg's stop whichever way its riders travel.
		source = self._source("one_fm", "doctype", "transportation_manifest", "manifest_sync.py")

		self.assertIn("time_str = _time_field(_local_seconds(a_row.end_time))", source)
		self.assertNotIn(
			'time_str = a_row.end_time if direction == "RETURN" else a_row.start_time', source
		)

	def test_the_driver_report_time_reaches_the_sheet(self):
		source = self._source("one_fm", "doctype", "transportation_manifest", "manifest_sheet.py")

		self.assertIn('"qoa_time"', source)
		self.assertIn("action_type", source)
