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
	_ends_at_base_camp,
	day_offset,
	get_merge_preview,
	qoa_buffer_minutes,
	walk_legs,
)
from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
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
	"""AC 1.5: a mixed run has to finish by taking its return riders home."""

	def _card(self, direction):
		return frappe._dict({
			"name": frappe.generate_hash("TS", 6),
			"trip_direction": direction,
			"pre_merge_trip_direction": None,
		})

	def test_a_mixed_run_ending_on_a_return_leg_is_accepted(self):
		self.assertTrue(_ends_at_base_camp([self._card("Outward"), self._card("Return")]))

	def test_a_mixed_run_ending_on_an_outward_leg_is_refused(self):
		# It would leave the return riders at a site with the bus driving away.
		self.assertFalse(_ends_at_base_camp([self._card("Return"), self._card("Outward")]))

	def test_a_plain_outbound_run_is_left_alone(self):
		# A drop-off run legitimately finishes at a site; holding it to this would refuse
		# every multi-stop outbound run on the board.
		self.assertTrue(_ends_at_base_camp([self._card("Outward"), self._card("Outward")]))

	def test_a_plain_return_run_is_left_alone(self):
		self.assertTrue(_ends_at_base_camp([self._card("Return"), self._card("Return")]))


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

	def test_each_leg_names_where_it_comes_from_and_goes_to(self):
		stops = self._preview()["stops"]

		# An outward leg loads at its camp; a return leg loads at the site it collects
		# from. "Next stop" is the following leg's origin, not this card's own site -
		# a run that collects from three camps before dropping anyone needs the two to
		# be different columns.
		self.assertEqual(stops[1]["origin_location"], stops[1]["stop_location"])
		self.assertEqual(stops[0]["next_stop_location"], stops[1]["origin_location"])
		self.assertEqual(stops[0]["shift_location"], stops[0]["stop_location"])

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
		frappe.reload_doc("one_fm", "doctype", "route_plan_assignment")

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
		doc.headcount = 4
		doc.stop_location = self.site
		doc.accommodation = self.camp
		doc.generation_key = frappe.generate_hash("TS-LEG", 10)
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def _plan(self):
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
		_stamp_leg_details(doc)
		return doc.assignments

	def test_a_stop_that_sheds_and_takes_on_is_combined(self):
		# Both movements happen at one place, which is what a handover is.
		self.assertEqual({row.action_type for row in self._plan()}, {"Combined"})

	def test_the_counts_are_split_by_which_way_the_riders_go(self):
		dropped, collected = self._plan()

		self.assertEqual((dropped.drop_off_count, dropped.boarding_count), (4, 0))
		self.assertEqual((collected.drop_off_count, collected.boarding_count), (0, 4))

	def test_occupancy_is_walked_disembark_first(self):
		# 4 off before 4 on, so the bus never holds 8 - the same walk the seat check uses.
		dropped, collected = self._plan()

		self.assertEqual(dropped.current_passenger_count, 0)
		self.assertEqual(collected.current_passenger_count, 4)

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
