# Copyright (c) 2026, oneaborance and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from one_fm.operations.doctype.route_plan.route_plan import (
	_date_ranges_overlap,
	_detect_retention_conflict,
	_format_lock_date,
	_format_lock_until,
	_is_multiday_lock,
	_iso_time_of_day,
	_iso_to_date,
	_peak_concurrent_headcount,
	_row_date_range,
	_row_direction,
	_row_time_window,
	_time_windows_overlap,
	_trips_share_the_road,
	_windows_overlap,
)

DAY = "2026-07-20"
NEXT_DAY = "2026-07-21"


def _shipment(name, *, retention=0, from_date=DAY, to_date=DAY,
			  start="08:00:00", end="14:00:00", source=None):
	"""Build an in-memory retention-window dict as _get_shipment_windows returns."""
	return frappe._dict({
		"name": name,
		"requires_vehicle_retention": retention,
		"from_date": from_date,
		"to_date": to_date,
		"start_time": start,
		"end_time": end,
		"source_docname": source,
	})


class TestRetentionOverlapLogic(FrappeTestCase):
	"""TR4-7: pure date-range × daily-time overlap detection, no fixtures needed."""

	def test_date_ranges_overlap_true_and_false(self):
		self.assertTrue(_date_ranges_overlap(DAY, DAY, DAY, DAY))
		self.assertTrue(_date_ranges_overlap("2026-07-18", "2026-07-22", DAY, DAY))
		self.assertFalse(_date_ranges_overlap(DAY, DAY, NEXT_DAY, NEXT_DAY))

	def test_date_ranges_open_ended_bounds_always_overlap(self):
		# A standing card with no from/to date is active on every calendar day.
		self.assertTrue(_date_ranges_overlap(None, None, DAY, DAY))
		self.assertTrue(_date_ranges_overlap(DAY, None, "2030-01-01", "2030-01-01"))

	def test_time_windows_overlap_when_they_intersect(self):
		# Retention 08:00-14:00 vs grocery run 11:30-12:30 -> overlap.
		self.assertTrue(_time_windows_overlap("08:00:00", "14:00:00", "11:30:00", "12:30:00"))

	def test_time_windows_touching_edges_do_not_overlap(self):
		# A return leg that starts exactly when the lock releases is allowed.
		self.assertFalse(_time_windows_overlap("08:00:00", "14:00:00", "14:00:00", "16:00:00"))

	def test_time_windows_disjoint_do_not_overlap(self):
		self.assertFalse(_time_windows_overlap("08:00:00", "14:00:00", "15:00:00", "16:00:00"))

	def test_windows_overlap_requires_both_date_and_time(self):
		lock = _shipment("A", retention=1)
		# Same time window but a different day -> no overlap.
		other_other_day = _shipment("B", from_date=NEXT_DAY, to_date=NEXT_DAY,
									 start="11:30:00", end="12:30:00")
		self.assertFalse(_windows_overlap(lock, other_other_day))
		# Same day, overlapping time -> overlap.
		other_same_day = _shipment("B", start="11:30:00", end="12:30:00")
		self.assertTrue(_windows_overlap(lock, other_same_day))


class TestRetentionConflictDetection(FrappeTestCase):
	"""TR4-7: which co-assigned shipment set trips the STANDBY lock."""

	def test_retention_blocks_overlapping_adhoc_drop(self):
		# The acceptance-criteria scenario: a fingerprint retention lock (08:00-14:00)
		# and a grocery run at 11:30 land on the same vehicle.
		fingerprint = _shipment("SHIP-FP", retention=1, source="TRQ-FINGERPRINT")
		grocery = _shipment("SHIP-GROC", start="11:30:00", end="12:30:00")
		shipment_map = {"SHIP-FP": fingerprint, "SHIP-GROC": grocery}

		conflict = _detect_retention_conflict({"SHIP-FP", "SHIP-GROC"}, shipment_map)
		self.assertIsNotNone(conflict)
		self.assertEqual(conflict.name, "SHIP-FP")

	def test_no_conflict_when_times_are_disjoint(self):
		fingerprint = _shipment("SHIP-FP", retention=1)
		evening = _shipment("SHIP-EVE", start="15:00:00", end="18:00:00")
		shipment_map = {"SHIP-FP": fingerprint, "SHIP-EVE": evening}
		self.assertIsNone(_detect_retention_conflict({"SHIP-FP", "SHIP-EVE"}, shipment_map))

	def test_no_conflict_when_dates_are_disjoint(self):
		fingerprint = _shipment("SHIP-FP", retention=1)
		next_week = _shipment("SHIP-NW", from_date="2026-07-27", to_date="2026-07-27",
							   start="11:30:00", end="12:30:00")
		shipment_map = {"SHIP-FP": fingerprint, "SHIP-NW": next_week}
		self.assertIsNone(_detect_retention_conflict({"SHIP-FP", "SHIP-NW"}, shipment_map))

	def test_lone_retention_card_never_conflicts_with_itself(self):
		# A single retention card (even placed on two rows) collapses to one name.
		fingerprint = _shipment("SHIP-FP", retention=1)
		self.assertIsNone(_detect_retention_conflict({"SHIP-FP"}, {"SHIP-FP": fingerprint}))

	def test_two_non_retention_overlaps_do_not_trip_the_lock(self):
		# Without a retention flag there is no STANDBY hold to enforce here.
		a = _shipment("SHIP-A", start="08:00:00", end="14:00:00")
		b = _shipment("SHIP-B", start="11:30:00", end="12:30:00")
		self.assertIsNone(_detect_retention_conflict({"SHIP-A", "SHIP-B"}, {"SHIP-A": a, "SHIP-B": b}))

	def test_two_overlapping_retention_trips_conflict(self):
		# "Any overlapping drop" is blocked, including another retention trip.
		a = _shipment("SHIP-A", retention=1)
		b = _shipment("SHIP-B", retention=1, start="11:30:00", end="12:30:00")
		conflict = _detect_retention_conflict({"SHIP-A", "SHIP-B"}, {"SHIP-A": a, "SHIP-B": b})
		self.assertIsNotNone(conflict)


class TestLockUntilLabel(FrappeTestCase):
	def test_formats_afternoon_time_as_12_hour(self):
		self.assertEqual(_format_lock_until("14:00:00"), "02:00 PM")

	def test_formats_morning_time_as_12_hour(self):
		self.assertEqual(_format_lock_until("08:30:00"), "08:30 AM")

	def test_blank_time_yields_empty_label(self):
		self.assertEqual(_format_lock_until(None), "")


class TestDatetimeLockLogic(FrappeTestCase):
	"""TR-8: the DATE part of start_time/end_time drives the multi-day lock."""

	def _row(self, start, end):
		return frappe._dict({"start_time": start, "end_time": end})

	def test_iso_to_date_parses_zulu_stamp(self):
		# Only the calendar date is extracted from the timeline timestamp.
		self.assertEqual(_iso_to_date("2026-07-20T06:00:00Z"), getdate("2026-07-20"))
		self.assertEqual(_iso_to_date("2026-07-15T06:00:00.000Z"), getdate("2026-07-15"))
		self.assertIsNone(_iso_to_date(""))

	def test_is_multiday_lock_true_when_end_date_after_start(self):
		self.assertTrue(_is_multiday_lock(self._row("2026-07-15T06:00:00Z", "2026-07-20T07:00:00Z")))

	def test_is_multiday_lock_false_for_single_day(self):
		# Same-day start/end is an ordinary trip, not a block-out lock.
		self.assertFalse(_is_multiday_lock(self._row("2026-07-20T06:00:00Z", "2026-07-20T07:00:00Z")))

	def test_row_date_range(self):
		r = self._row("2026-07-15T06:00:00Z", "2026-07-20T07:00:00Z")
		self.assertEqual(_row_date_range(r), (getdate("2026-07-15"), getdate("2026-07-20")))

	def test_format_lock_date(self):
		self.assertEqual(_format_lock_date(getdate("2026-07-15")), "15-07-2026")
		self.assertEqual(_format_lock_date(None), "")


class TestRoutePlanRetentionSave(FrappeTestCase):
	"""TR4-7: the before-save hook rejects the drop end to end on the plan."""

	def _make_shipment(self, retention, *, start, end, source=None,
					   from_date=DAY, to_date=DAY):
		"""Insert a minimal Transportation Shipment, bypassing Trip Request rules."""
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = "Unassigned"
		doc.trip_direction = "Outward"
		doc.routing_type_badge = "Direct"
		doc.requires_vehicle_retention = retention
		doc.from_date = from_date
		doc.to_date = to_date
		doc.start_time = start
		doc.end_time = end
		if source:
			doc.source_doctype = "Trip Request"
			doc.source_docname = source
		doc.flags.ignore_validate = True
		# source_docname is a Dynamic Link to a Trip Request that this unit test
		# does not provision, so skip link existence checks for the fixture.
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def _make_plan(self, rows):
		"""Build (not insert) a Route Plan with the given assignment rows.

		Vehicle links and mandatory checks are skipped so the retention hook — which
		runs first in the controller validate() — is what the save exercises.
		"""
		doc = frappe.new_doc("Route Plan")
		doc.title = frappe.generate_hash("RP-TEST", 8)
		doc.status = "Draft"
		doc.effective_from = DAY
		for row in rows:
			doc.append("assignments", row)
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		return doc

	def test_save_blocks_overlapping_drop_on_retained_vehicle(self):
		lock = self._make_shipment(1, start="08:00:00", end="14:00:00", source="TRQ-FINGERPRINT")
		grocery = self._make_shipment(0, start="11:30:00", end="12:30:00")

		plan = self._make_plan([
			{"card_id": f"TSHIP-{lock}", "transportation_shipment": lock,
			 "vehicle": "VHL-0002", "direction": "OUTBOUND"},
			{"card_id": f"TSHIP-{grocery}", "transportation_shipment": grocery,
			 "vehicle": "VHL-0002", "direction": "OUTBOUND"},
		])

		with self.assertRaises(frappe.ValidationError) as cm:
			plan.insert(ignore_permissions=True)
		message = str(cm.exception)
		self.assertIn("VHL-0002", message)
		self.assertIn("locked on STANDBY", message)
		self.assertIn("TRQ-FINGERPRINT", message)
		self.assertIn("02:00 PM", message)

	def test_save_allows_non_overlapping_drop(self):
		lock = self._make_shipment(1, start="08:00:00", end="14:00:00", source="TRQ-FINGERPRINT")
		evening = self._make_shipment(0, start="15:00:00", end="18:00:00")

		plan = self._make_plan([
			{"card_id": f"TSHIP-{lock}", "transportation_shipment": lock,
			 "vehicle": "VHL-0002", "direction": "OUTBOUND"},
			{"card_id": f"TSHIP-{evening}", "transportation_shipment": evening,
			 "vehicle": "VHL-0002", "direction": "OUTBOUND"},
		])
		# No overlap -> save succeeds without raising.
		plan.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Route Plan", plan.name))

	def test_save_allows_overlap_on_different_vehicles(self):
		lock = self._make_shipment(1, start="08:00:00", end="14:00:00", source="TRQ-FINGERPRINT")
		grocery = self._make_shipment(0, start="11:30:00", end="12:30:00")

		plan = self._make_plan([
			{"card_id": f"TSHIP-{lock}", "transportation_shipment": lock,
			 "vehicle": "VHL-0002", "direction": "OUTBOUND"},
			{"card_id": f"TSHIP-{grocery}", "transportation_shipment": grocery,
			 "vehicle": "VHL-0009", "direction": "OUTBOUND"},
		])
		# The grocery run overlaps in time but sits on a different vehicle.
		plan.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Route Plan", plan.name))


class TestRoutePlanDatetimeLockSave(FrappeTestCase):
	"""TR-8: a multi-day lock (DATE span of start_time/end_time) blocks the vehicle."""

	def _make_shipment(self):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = "Unassigned"
		doc.trip_direction = "Outward"
		doc.routing_type_badge = "Direct"
		doc.flags.ignore_validate = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def _make_plan(self, rows):
		doc = frappe.new_doc("Route Plan")
		doc.title = frappe.generate_hash("RP-TEST", 8)
		doc.status = "Draft"
		doc.effective_from = today()
		for row in rows:
			doc.append("assignments", row)
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		return doc

	def _row(self, shipment, vehicle, *, start_iso, end_iso, trip=None):
		"""A run whose DATE span is the lock lifespan and TIME is the daily trip."""
		return {"card_id": f"TSHIP-{shipment}", "transportation_shipment": shipment,
				"vehicle": vehicle, "direction": "OUTBOUND", "trip_group": trip,
				"start_time": start_iso, "end_time": end_iso}

	def test_multiday_lock_blocks_overlapping_run(self):
		# AC3: a multi-day lock blocks any run landing inside those days, even a
		# short daily one at a different time.
		lock_ship = self._make_shipment()
		run_ship = self._make_shipment()
		lock_end_day = add_days(today(), 5)

		plan = self._make_plan([
			self._row(lock_ship, "VHL-0005",
					  start_iso=f"{today()}T06:00:00Z", end_iso=f"{lock_end_day}T07:00:00Z"),
			self._row(run_ship, "VHL-0005",
					  start_iso=f"{today()}T08:00:00Z", end_iso=f"{today()}T09:00:00Z"),
		])
		with self.assertRaises(frappe.ValidationError) as cm:
			plan.insert(ignore_permissions=True)
		self.assertIn("VHL-0005", str(cm.exception))

	def test_single_day_runs_do_not_block(self):
		# Two ordinary single-day runs may share a vehicle (normal multi-trip).
		a = self._make_shipment()
		b = self._make_shipment()

		plan = self._make_plan([
			self._row(a, "VHL-0005",
					  start_iso=f"{today()}T06:00:00Z", end_iso=f"{today()}T07:00:00Z"),
			self._row(b, "VHL-0005",
					  start_iso=f"{today()}T08:00:00Z", end_iso=f"{today()}T09:00:00Z"),
		])
		plan.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Route Plan", plan.name))

	def test_expired_lock_frees_the_vehicle(self):
		# A lock whose last day is before today no longer blocks new drops.
		lock_ship = self._make_shipment()
		run_ship = self._make_shipment()

		plan = self._make_plan([
			self._row(lock_ship, "VHL-0005",
					  start_iso=f"{add_days(today(), -5)}T06:00:00Z",
					  end_iso=f"{add_days(today(), -2)}T07:00:00Z"),
			self._row(run_ship, "VHL-0005",
					  start_iso=f"{today()}T08:00:00Z", end_iso=f"{today()}T09:00:00Z"),
		])
		plan.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Route Plan", plan.name))

	def test_same_trip_stops_are_exempt(self):
		# Two stops chained into one trip legitimately share the locked vehicle.
		lock_ship = self._make_shipment()
		stop_ship = self._make_shipment()
		lock_end_day = add_days(today(), 5)

		plan = self._make_plan([
			self._row(lock_ship, "VHL-0005",
					  start_iso=f"{today()}T06:00:00Z", end_iso=f"{lock_end_day}T07:00:00Z",
					  trip="TRIP-A"),
			self._row(stop_ship, "VHL-0005",
					  start_iso=f"{today()}T08:00:00Z", end_iso=f"{today()}T09:00:00Z",
					  trip="TRIP-A"),
		])
		plan.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Route Plan", plan.name))

	def test_lock_on_different_vehicle_does_not_block(self):
		lock_ship = self._make_shipment()
		run_ship = self._make_shipment()
		lock_end_day = add_days(today(), 5)

		plan = self._make_plan([
			self._row(lock_ship, "VHL-0005",
					  start_iso=f"{today()}T06:00:00Z", end_iso=f"{lock_end_day}T07:00:00Z"),
			self._row(run_ship, "VHL-0009",
					  start_iso=f"{today()}T08:00:00Z", end_iso=f"{today()}T09:00:00Z"),
		])
		plan.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Route Plan", plan.name))


class TestRowDirection(FrappeTestCase):
	"""MA4-13: direction normalization used by the capacity/single-vehicle clusters."""

	def test_outbound_and_blank_normalize_to_outbound(self):
		self.assertEqual(_row_direction(frappe._dict({"direction": "OUTBOUND"})), "OUTBOUND")
		self.assertEqual(_row_direction(frappe._dict({"direction": ""})), "OUTBOUND")
		self.assertEqual(_row_direction(frappe._dict({"direction": None})), "OUTBOUND")

	def test_return_variants_normalize_to_return(self):
		self.assertEqual(_row_direction(frappe._dict({"direction": "RETURN"})), "RETURN")
		self.assertEqual(_row_direction(frappe._dict({"direction": " return "})), "RETURN")


class TestRoutePlanCapacitySave(FrappeTestCase):
	"""MA4-13: combined headcount of a merged trip_group leg cannot exceed seats-1.

	Uses a real 4-seat vehicle (legal passenger capacity = 3 after reserving the
	driver seat) so the validation reads a genuine Vehicle.seats value.
	"""

	VEHICLE = "VHL-L-0022"  # 4 seats -> 3 legal passenger seats
	SEATS = 4

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Vehicle", cls.VEHICLE):
			raise cls.skipTest(cls, f"Fixture vehicle {cls.VEHICLE} missing on this site")

	def _make_plan(self, rows):
		doc = frappe.new_doc("Route Plan")
		doc.title = frappe.generate_hash("RP-CAP", 8)
		doc.status = "Draft"
		doc.effective_from = today()
		for row in rows:
			doc.append("assignments", row)
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		return doc

	def _row(self, vehicle, *, trip, direction="OUTBOUND", headcount, card=None):
		return {
			"card_id": card or frappe.generate_hash("CARD", 8),
			"vehicle": vehicle,
			"direction": direction,
			"trip_group": trip,
			"trip_name": trip,
			"headcount": headcount,
		}

	def test_merged_camps_exceeding_seats_are_blocked(self):
		# Two camps on one outbound run: 3 + 2 = 5 > 3 legal seats.
		plan = self._make_plan([
			self._row(self.VEHICLE, trip="TRIP-MB-MG", headcount=3),
			self._row(self.VEHICLE, trip="TRIP-MB-MG", headcount=2),
		])
		with self.assertRaises(frappe.ValidationError) as cm:
			plan.insert(ignore_permissions=True)
		message = str(cm.exception)
		self.assertIn(self.VEHICLE, message)
		self.assertIn("short 2 seat", message)  # 5 - 3

	def test_merged_camps_within_seats_are_allowed(self):
		# 2 + 1 = 3 <= 3 legal seats.
		plan = self._make_plan([
			self._row(self.VEHICLE, trip="TRIP-OK", headcount=2),
			self._row(self.VEHICLE, trip="TRIP-OK", headcount=1),
		])
		plan.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Route Plan", plan.name))

	def test_outbound_and_return_of_one_trip_are_counted_separately(self):
		# Same trip_group but opposite directions are two physical runs, so each
		# 3-seat leg is fine even though they'd overflow if summed together.
		plan = self._make_plan([
			self._row(self.VEHICLE, trip="TRIP-BOTH", direction="OUTBOUND", headcount=3),
			self._row(self.VEHICLE, trip="TRIP-BOTH", direction="RETURN", headcount=3),
		])
		plan.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Route Plan", plan.name))

	def test_standalone_rows_are_weighed_too(self):
		# WI-002000: a drop with no trip_group used to be skipped by the backend
		# entirely. It is a trip of its own now, so an overloaded one is caught
		# server-side instead of resting on the canvas check alone.
		plan = self._make_plan([
			{"card_id": frappe.generate_hash("C", 8), "vehicle": self.VEHICLE,
			 "direction": "OUTBOUND", "headcount": 20},
		])
		with self.assertRaises(frappe.ValidationError) as cm:
			plan.insert(ignore_permissions=True)

		self.assertIn("short 17 seat", str(cm.exception))  # 20 - 3


def _trip(key, *, headcount, start, end, direction="OUTBOUND",
		  live_from="2026-07-20", live_to="2026-07-20"):
	"""An in-memory logical trip as _logical_trips() builds them.

	``start``/``end`` are ``HH:MM`` clock times, turned into seconds past
	midnight the way a row's timestamps are read.
	"""
	def secs(label):
		hours, minutes = label.split(":")
		return int(hours) * 3600 + int(minutes) * 60

	start_secs, end_secs = secs(start), secs(end)
	if end_secs <= start_secs:
		end_secs += 24 * 60 * 60

	return frappe._dict({
		"key": ("VHL-TEST", key, direction),
		"vehicle": "VHL-TEST",
		"direction": direction,
		"headcount": headcount,
		"start": start_secs,
		"end": end_secs,
		"live_from": getdate(live_from) if live_from else None,
		"live_to": getdate(live_to) if live_to else None,
	})


class TestTheDailyWindowOfARow(FrappeTestCase):
	"""WI-002000: the clock time is what decides overlap; the date half of a
	Route Plan Assignment timestamp is the multi-day lock lifespan (TR-8)."""

	def test_the_clock_time_is_read_off_the_stamp(self):
		self.assertEqual(_iso_time_of_day("2026-07-20T06:30:15.000Z"), 6 * 3600 + 30 * 60 + 15)

	def test_a_missing_stamp_has_no_time(self):
		self.assertIsNone(_iso_time_of_day(None))
		self.assertIsNone(_iso_time_of_day(""))

	def test_the_same_hour_on_two_different_days_reads_the_same(self):
		"""Otherwise a run repeating daily under a multi-day lock would never be
		seen to overlap anything."""
		self.assertEqual(
			_iso_time_of_day("2026-07-24T13:45:00.000Z"),
			_iso_time_of_day("2026-07-30T13:45:00.000Z"),
		)

	def test_a_row_with_no_times_spans_the_whole_day(self):
		"""It could be running at any hour, so it is never taken for a finished run."""
		self.assertEqual(
			_row_time_window(frappe._dict(start_time=None, end_time=None)), (0, 86400)
		)

	def test_a_run_over_midnight_carries_past_the_day_boundary(self):
		start, end = _row_time_window(
			frappe._dict(start_time="2026-07-20T22:00:00Z", end_time="2026-07-21T01:00:00Z")
		)

		self.assertEqual(start, 22 * 3600)
		self.assertEqual(end, 25 * 3600)


class TestWhichTripsShareTheRoad(FrappeTestCase):
	"""WI-002000 AC1/AC3: only trips running at the same time carry each other's
	passengers."""

	def test_a_finished_run_does_not_meet_the_next_one(self):
		"""AC1: Trip 401 ends 05:10, Trip 402 starts 07:00."""
		self.assertFalse(_trips_share_the_road(
			_trip("T401", headcount=25, start="04:00", end="05:10"),
			_trip("T402", headcount=10, start="07:00", end="08:30"),
		))

	def test_two_hours_apart_is_still_apart(self):
		"""AC3: S101 ends 06:00, S102 starts 08:00."""
		self.assertFalse(_trips_share_the_road(
			_trip("S101", headcount=25, start="05:00", end="06:00"),
			_trip("S102", headcount=25, start="08:00", end="10:00"),
		))

	def test_a_bus_can_turn_straight_around(self):
		"""Touching windows are not an overlap, or a 10:00 departure could never
		follow a run that lands at 10:00."""
		self.assertFalse(_trips_share_the_road(
			_trip("A", headcount=25, start="08:00", end="10:00"),
			_trip("B", headcount=10, start="10:00", end="11:00"),
		))

	def test_overlapping_windows_do_share(self):
		"""AC2: 08:00-10:00 against a card whose window reaches into it."""
		self.assertTrue(_trips_share_the_road(
			_trip("A", headcount=25, start="08:00", end="10:00"),
			_trip("B", headcount=10, start="09:00", end="11:00"),
		))

	def test_a_run_past_midnight_meets_the_early_morning(self):
		self.assertTrue(_trips_share_the_road(
			_trip("NIGHT", headcount=20, start="22:00", end="01:00"),
			_trip("DAWN", headcount=10, start="00:30", end="02:00"),
		))

	def test_runs_live_in_different_months_never_meet(self):
		"""Same hour, but the multi-day lifespans do not overlap."""
		self.assertFalse(_trips_share_the_road(
			_trip("JUNE", headcount=25, start="08:00", end="10:00",
				  live_from="2026-06-01", live_to="2026-06-30"),
			_trip("JULY", headcount=25, start="08:00", end="10:00",
				  live_from="2026-07-01", live_to="2026-07-31"),
		))

	def test_the_two_directions_of_one_journey_never_meet(self):
		"""The same bus going out and coming back is not two buses (MA4-13). Held
		even with no times recorded, where both default to the whole day."""
		out = _trip("TRIP-BOTH", headcount=3, start="00:00", end="00:00")
		ret = _trip("TRIP-BOTH", headcount=3, start="00:00", end="00:00", direction="RETURN")
		out.start, out.end = 0, 86400
		ret.start, ret.end = 0, 86400

		self.assertFalse(_trips_share_the_road(out, ret))

	def test_two_different_trips_do_meet_across_directions(self):
		"""A return leg of one journey can still collide with another journey's
		outbound run — that is a real double-booking, not the same bus."""
		self.assertTrue(_trips_share_the_road(
			_trip("JOURNEY-A", headcount=10, start="08:00", end="10:00", direction="RETURN"),
			_trip("JOURNEY-B", headcount=10, start="09:00", end="11:00"),
		))


class TestPeakConcurrentHeadcount(FrappeTestCase):
	def test_trips_apart_in_time_are_not_pooled(self):
		"""AC1/AC3: the lane total is irrelevant; only what is aboard at once."""
		peak = _peak_concurrent_headcount([
			_trip("T401", headcount=25, start="04:00", end="05:10"),
			_trip("T402", headcount=25, start="07:00", end="08:30"),
		])

		self.assertEqual(peak, 25)

	def test_overlapping_trips_are_summed(self):
		"""AC2: 25 aboard from 08:00-10:00 plus 10 more from 09:00."""
		peak = _peak_concurrent_headcount([
			_trip("A", headcount=25, start="08:00", end="10:00"),
			_trip("B", headcount=10, start="09:00", end="11:00"),
		])

		self.assertEqual(peak, 35)

	def test_an_empty_lane_peaks_at_nothing(self):
		self.assertEqual(_peak_concurrent_headcount([]), 0)


class TestRoutePlanTimeWindowCapacitySave(FrappeTestCase):
	"""WI-002000 end to end, on a real 4-seat vehicle (3 legal passenger seats)."""

	VEHICLE = "VHL-L-0022"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Vehicle", cls.VEHICLE):
			raise cls.skipTest(cls, f"Fixture vehicle {cls.VEHICLE} missing on this site")

	def _make_plan(self, rows):
		doc = frappe.new_doc("Route Plan")
		doc.title = frappe.generate_hash("RP-TW", 8)
		doc.status = "Draft"
		doc.effective_from = today()
		for row in rows:
			doc.append("assignments", row)
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		return doc

	def _row(self, *, trip=None, headcount, start, end, direction="OUTBOUND", day=DAY):
		return {
			"card_id": frappe.generate_hash("CARD", 8),
			"vehicle": self.VEHICLE,
			"direction": direction,
			"trip_group": trip,
			"trip_name": trip,
			"headcount": headcount,
			"start_time": f"{day}T{start}:00.000Z",
			"end_time": f"{day}T{end}:00.000Z",
		}

	def test_a_second_trip_later_in_the_day_is_allowed(self):
		"""AC1, the whole point: the 05:10 run is over by the time the 07:00 one
		leaves, and both fill the bus. The old lane-wide sum rejected this."""
		plan = self._make_plan([
			self._row(trip="TRIP-401", headcount=3, start="04:00", end="05:10"),
			self._row(trip="TRIP-402", headcount=3, start="07:00", end="08:30"),
		])

		plan.insert(ignore_permissions=True)

		self.assertTrue(frappe.db.exists("Route Plan", plan.name))

	def test_concurrent_trips_are_summed_and_blocked(self):
		"""AC2: 2 aboard 08:00-10:00 plus 2 more from 09:00 is 4 on a 3-seater."""
		plan = self._make_plan([
			self._row(trip="TRIP-A", headcount=2, start="08:00", end="10:00"),
			self._row(trip="TRIP-B", headcount=2, start="09:00", end="11:00"),
		])

		with self.assertRaises(frappe.ValidationError) as cm:
			plan.insert(ignore_permissions=True)
		message = str(cm.exception)

		self.assertIn("Total overlapping passengers (4)", message)
		self.assertIn("vehicle limit (3)", message)

	def test_separate_trips_are_each_still_held_to_the_seats(self):
		"""AC3's tail: separate trips are not merged, but neither is let off."""
		plan = self._make_plan([
			self._row(trip="S101", headcount=1, start="05:00", end="06:00"),
			self._row(trip="S102", headcount=9, start="08:00", end="10:00"),
		])

		with self.assertRaises(frappe.ValidationError) as cm:
			plan.insert(ignore_permissions=True)

		self.assertIn("short 6 seat", str(cm.exception))  # 9 - 3, the S102 run alone

	def test_the_stops_of_one_trip_still_sum(self):
		"""MA4-13 must survive: two camps on one run ride together even though
		their stops are sequential rather than overlapping."""
		plan = self._make_plan([
			self._row(trip="TRIP-MERGED", headcount=2, start="04:45", end="06:00"),
			self._row(trip="TRIP-MERGED", headcount=2, start="06:50", end="07:20"),
		])

		with self.assertRaises(frappe.ValidationError) as cm:
			plan.insert(ignore_permissions=True)

		self.assertIn("short 1 seat", str(cm.exception))  # 4 - 3

	def test_the_limit_follows_the_vehicles_driver_seat_flag(self):
		"""WI-002000 AC4/AC5: the same 4 passengers on the same 4-seater are an
		overload when the seat count includes the driver and a full bus when it does
		not. Nothing about the limit is decided here — the fleet record decides."""
		rows = [self._row(trip="TRIP-FULL", headcount=4, start="08:00", end="09:00")]
		was = frappe.db.get_value(
			"Vehicle", self.VEHICLE,
			["custom_includes_driver_seat", "custom_max_passenger_capacity"], as_dict=True,
		)
		self.addCleanup(
			frappe.db.set_value, "Vehicle", self.VEHICLE, dict(was), update_modified=False
		)

		frappe.db.set_value(
			"Vehicle", self.VEHICLE,
			{"custom_includes_driver_seat": 1, "custom_max_passenger_capacity": 3},
			update_modified=False,
		)
		with self.assertRaises(frappe.ValidationError):
			self._make_plan(rows).insert(ignore_permissions=True)

		frappe.db.set_value(
			"Vehicle", self.VEHICLE,
			{"custom_includes_driver_seat": 0, "custom_max_passenger_capacity": 4},
			update_modified=False,
		)
		plan = self._make_plan(rows)
		plan.insert(ignore_permissions=True)

		self.assertTrue(frappe.db.exists("Route Plan", plan.name))

	def test_a_vehicle_that_has_never_been_derived_still_gets_a_limit(self):
		"""A stored 0 would wave every drop through, so the formula is applied on
		the spot from the seat count and the flag."""
		was = frappe.db.get_value("Vehicle", self.VEHICLE, "custom_max_passenger_capacity")
		self.addCleanup(
			frappe.db.set_value, "Vehicle", self.VEHICLE,
			"custom_max_passenger_capacity", was, update_modified=False,
		)
		frappe.db.set_value(
			"Vehicle", self.VEHICLE,
			{"custom_includes_driver_seat": 1, "custom_max_passenger_capacity": 0},
			update_modified=False,
		)

		with self.assertRaises(frappe.ValidationError) as cm:
			self._make_plan([
				self._row(trip="TRIP-FULL", headcount=4, start="08:00", end="09:00")
			]).insert(ignore_permissions=True)

		self.assertIn("short 1 seat", str(cm.exception))  # 4 - (4 seats - driver)

	def test_a_lane_full_of_short_runs_is_fine(self):
		"""Four back-to-back full loads across the day: 12 passengers on a bus
		that seats 3, and every one of them legitimate."""
		plan = self._make_plan([
			self._row(trip=f"TRIP-{hour}", headcount=3, start=f"{hour:02d}:00", end=f"{hour:02d}:45")
			for hour in (5, 8, 13, 20)
		])

		plan.insert(ignore_permissions=True)

		self.assertTrue(frappe.db.exists("Route Plan", plan.name))


class TestTheCanvasAgreesWithTheBackend(FrappeTestCase):
	"""The driver's seat is reserved on both sides (WI-002000).

	The canvas compared against the full seat count while the save reserved a
	seat, so a last-seat run passed the drop and was refused on save. Pinned on
	the source because a page script has no server-side entry point to exercise.
	"""

	def canvas(self):
		return frappe.read_file(
			frappe.get_app_path(
				"one_fm", "one_fm", "page", "transportation_schedule",
				"transportation_schedule.js",
			)
		)

	def test_every_seat_comparison_goes_through_the_passenger_limit(self):
		import re

		source = self.canvas()
		# A comparison straight against .seats is the bug this closes; the helper
		# and the display strings are what may still mention it.
		offenders = [
			line.strip()
			for line in source.splitlines()
			if re.search(r"[<>]=?\s*[\w.]*\.seats\b", line) or re.search(r"\.seats\s*[<>]=?", line)
		]

		self.assertEqual(offenders, [])

	def test_the_helper_reads_the_vehicles_own_limit(self):
		"""Not a rule in the code: the Vehicle record says whether its seat count
		includes the driver, and Max Passenger Capacity is the answer."""
		self.assertIn("vehicle.max_passenger_capacity", self.canvas())

	def test_the_refusal_names_the_limit_it_applied(self):
		"""Telling a dispatcher "30-seater" while blocking at 29 is what made this
		look like a bug rather than a reserved seat."""
		source = self.canvas()

		self.assertIn("capacityMessage(", source)
		self.assertIn("it takes {2} passengers", source)


class TestRoutePlanSingleVehicleSave(FrappeTestCase):
	"""MA4-13 AC2: a journey leg (trip_group + direction) must run on one vehicle."""

	def _make_plan(self, rows):
		doc = frappe.new_doc("Route Plan")
		doc.title = frappe.generate_hash("RP-SV", 8)
		doc.status = "Draft"
		doc.effective_from = today()
		for row in rows:
			doc.append("assignments", row)
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		return doc

	def test_split_leg_across_vehicles_is_blocked(self):
		plan = self._make_plan([
			{"card_id": "C1", "vehicle": "VHL-0005", "direction": "OUTBOUND",
			 "trip_group": "TRIP-SPLIT", "trip_name": "TRIP-SPLIT", "headcount": 5},
			{"card_id": "C2", "vehicle": "VHL-0009", "direction": "OUTBOUND",
			 "trip_group": "TRIP-SPLIT", "trip_name": "TRIP-SPLIT", "headcount": 5},
		])
		with self.assertRaises(frappe.ValidationError) as cm:
			plan.insert(ignore_permissions=True)
		self.assertIn("TRIP-SPLIT", str(cm.exception))

	def test_opposite_directions_may_use_different_vehicles(self):
		# Outbound and return of one trip are independently assignable.
		plan = self._make_plan([
			{"card_id": "C1", "vehicle": "VHL-0005", "direction": "OUTBOUND",
			 "trip_group": "TRIP-IND", "trip_name": "TRIP-IND", "headcount": 5},
			{"card_id": "C2", "vehicle": "VHL-0009", "direction": "RETURN",
			 "trip_group": "TRIP-IND", "trip_name": "TRIP-IND", "headcount": 5},
		])
		plan.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Route Plan", plan.name))
