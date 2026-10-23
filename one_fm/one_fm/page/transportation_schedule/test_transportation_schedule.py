# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Route Plan canvas backend (Multi-Day Lane Replication).

Focus: the outbound and return legs of one demand share a pair group (the
trip_group hash), yet must stay independently assignable to different vehicles.
_sync_shipment_statuses is the backend save/sync path that must validate BOTH the
shipment identity AND its direction flag so one leg never sweeps the other.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	_normalize_direction,
	_sync_shipment_statuses,
)


def _make_leg(pair_group, direction, status="Unassigned"):
	"""Insert a minimal standing Transportation Shipment leg for one direction."""
	doc = frappe.new_doc("Transportation Shipment")
	doc.status = status
	doc.trip_direction = direction  # "Outward" or "Return"
	doc.pair_group = pair_group
	doc.generation_key = f"{pair_group}|{direction}"
	doc.insert(ignore_permissions=True)
	return doc.name


def _swim_item(name, direction):
	"""A canvas swim item referencing a shipment card, as save_assignments sees it."""
	return {"cardId": f"TSHIP-{name}", "direction": direction}


class TestSyncShipmentStatuses(FrappeTestCase):
	def setUp(self):
		# One demand → a paired Outward + Return card sharing the trip_group hash.
		self.pair = frappe.generate_hash("TRQ-PAIR", 8)
		self.outbound = _make_leg(self.pair, "Outward")
		self.return_leg = _make_leg(self.pair, "Return")

	def _status(self, name):
		return frappe.db.get_value("Transportation Shipment", name, "status")

	def test_normalize_direction_maps_both_vocabularies(self):
		self.assertEqual(_normalize_direction("Outward"), "OUTBOUND")
		self.assertEqual(_normalize_direction("OUTBOUND"), "OUTBOUND")
		self.assertEqual(_normalize_direction("Return"), "RETURN")
		self.assertEqual(_normalize_direction("RETURN"), "RETURN")
		self.assertEqual(_normalize_direction(""), "OUTBOUND")
		self.assertEqual(_normalize_direction(None), "OUTBOUND")

	def test_outbound_placement_leaves_return_unassigned(self):
		# AC1: dropping the outbound card locks only the outbound leg; the paired
		# return card stays Unassigned so it can go to a different vehicle.
		_sync_shipment_statuses([_swim_item(self.outbound, "OUTBOUND")])

		self.assertEqual(self._status(self.outbound), "Assigned")
		self.assertEqual(self._status(self.return_leg), "Unassigned")

	def test_return_placement_is_independent(self):
		# Step 2: the return leg goes to a different bus, independent of the outbound.
		_sync_shipment_statuses([_swim_item(self.return_leg, "RETURN")])

		self.assertEqual(self._status(self.return_leg), "Assigned")
		self.assertEqual(self._status(self.outbound), "Unassigned")

	def test_both_legs_can_be_assigned_to_different_vehicles(self):
		# Outbound on Bus A, return on Bus C — both Assigned, one save.
		_sync_shipment_statuses([
			_swim_item(self.outbound, "OUTBOUND"),
			_swim_item(self.return_leg, "RETURN"),
		])

		self.assertEqual(self._status(self.outbound), "Assigned")
		self.assertEqual(self._status(self.return_leg), "Assigned")

	def test_direction_mismatch_is_not_assigned(self):
		# AC2: companion selection validates the direction flag, not just the
		# trip_group hash. A card resolving to the return shipment but placed with
		# an OUTBOUND flag must NOT flip the return leg to Assigned.
		_sync_shipment_statuses([_swim_item(self.return_leg, "OUTBOUND")])

		self.assertEqual(self._status(self.return_leg), "Unassigned")

	def test_dropping_outbound_reverts_only_outbound(self):
		# Both legs start Assigned in a prior save; a new save drops the outbound
		# only. The return leg (placed in this or another plan) is untouched.
		frappe.db.set_value("Transportation Shipment", self.outbound, "status", "Assigned")
		frappe.db.set_value("Transportation Shipment", self.return_leg, "status", "Assigned")

		_sync_shipment_statuses(
			[_swim_item(self.return_leg, "RETURN")],
			previously_linked={self.outbound, self.return_leg},
		)

		self.assertEqual(self._status(self.outbound), "Unassigned")
		self.assertEqual(self._status(self.return_leg), "Assigned")


class TestAPlacedCardIsNeverReverted(FrappeTestCase):
	"""A direction mismatch is a flag to fix, not a card to send back to the pool."""

	def setUp(self):
		self.pair = frappe.generate_hash("TRQ-KEEP", 8)
		self.leg = _make_leg(self.pair, "Outward", status="Assigned")

	def _read(self, name):
		return frappe.db.get_value(
			"Transportation Shipment", name,
			["status", "trip_direction", "pre_merge_trip_direction"], as_dict=True
		)

	def test_a_card_still_on_the_plan_keeps_its_status(self):
		# The stale-tab shape: the shipment reads Mixed, the browser still says OUTBOUND.
		frappe.db.set_value("Transportation Shipment", self.leg, {
			"trip_direction": "Mixed", "pre_merge_trip_direction": "Outward"
		})

		_sync_shipment_statuses(
			[_swim_item(self.leg, "OUTBOUND")], previously_linked={self.leg}
		)

		kept = self._read(self.leg)
		self.assertEqual(kept.status, "Assigned")
		self.assertEqual(kept.trip_direction, "Mixed")
		self.assertEqual(kept.pre_merge_trip_direction, "Outward")

	def test_a_card_the_plan_dropped_still_reverts(self):
		# What the revert branch is for: the block left the lane.
		frappe.db.set_value("Transportation Shipment", self.leg, {
			"trip_direction": "Mixed", "pre_merge_trip_direction": "Outward"
		})

		_sync_shipment_statuses([], previously_linked={self.leg})

		reverted = self._read(self.leg)
		self.assertEqual(reverted.status, "Unassigned")
		self.assertEqual(reverted.trip_direction, "Outward")
		self.assertIsNone(reverted.pre_merge_trip_direction)

	def test_a_mismatched_card_is_still_not_newly_assigned(self):
		# A mismatch never promotes a card to Assigned, it only stops it being demoted.
		frappe.db.set_value("Transportation Shipment", self.leg, "status", "Unassigned")

		_sync_shipment_statuses([_swim_item(self.leg, "RETURN")])

		self.assertEqual(self._read(self.leg).status, "Unassigned")



class TestTheRowNamesOneShift(FrappeTestCase):
	"""The row's `shift` is matched against Employee Schedule, so it must be a name.

	An OLM stop serving several shifts labels its card with all of them. Sent straight
	to the column that had been carrying a single shift, it overflowed the 140-character
	field and would have been useless as a lookup even if it fit.
	"""

	def test_a_shipment_row_takes_the_shift_from_the_document(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			_shift_by_shipment,
		)

		card = frappe.new_doc("Transportation Shipment")
		card.status = "Unassigned"
		card.trip_direction = "Outward"
		card.operations_shift = frappe.get_all("Operations Shift", limit=1, pluck="name")[0]
		card.flags.ignore_mandatory = True
		card.insert(ignore_permissions=True)

		found = _shift_by_shipment([{"cardId": f"TSHIP-{card.name}"}])

		self.assertEqual(found[card.name], card.operations_shift)

	def test_a_card_serving_several_shifts_names_none_of_them(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			_shift_by_shipment,
		)

		card = frappe.new_doc("Transportation Shipment")
		card.status = "Unassigned"
		card.trip_direction = "Outward"
		card.aggregated_shifts = "A-Afternoon-1, B-Afternoon-1, C-Afternoon-1"
		card.flags.ignore_mandatory = True
		card.insert(ignore_permissions=True)

		self.assertNotIn(card.name, _shift_by_shipment([{"cardId": f"TSHIP-{card.name}"}]))

	def test_the_browsers_label_is_never_written_for_a_shipment_row(self):
		source = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.py"
		))

		self.assertIn('shifts.get(shipment, "") if shipment', source)


class TestTheManifestReadsTheDayInOrder(FrappeTestCase):
	"""A vehicle's trips are listed by when each one leaves.

	Sorted by the trip group hash, a 06:48 run could be listed after an 08:27 one - and
	the vehicle's day then read "08:27 to 07:12", wrapping midnight into a 22h 45m shift
	on the driver's own page.
	"""

	def _row(self, trip, stop, start, end):
		return frappe._dict(
			card_id=f"TSHIP-{trip}-{stop}", trip_group=trip, stop_index=stop,
			start_time=start, end_time=end,
		)

	def test_the_earlier_trip_comes_first_whatever_its_group_is_called(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			manifest_row_order,
		)

		# "MIX-a..." sorts before "MIX-z..." by name, and after it by clock.
		late = self._row("MIX-a", 1, "2026-08-31T05:27:00Z", "2026-08-31T05:43:00Z")
		early = self._row("MIX-z", 1, "2026-08-31T03:48:00Z", "2026-08-31T04:03:00Z")

		ordered = manifest_row_order([late, early])

		self.assertEqual([row.trip_group for row in ordered], ["MIX-z", "MIX-a"])

	def test_the_stops_of_a_trip_follow_the_clock(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			manifest_row_order,
		)

		# Numbered 5 and 4 by the order they were dropped on the lane, which a re-timed
		# run leaves out of step with itself - the live plan has runs like this.
		second = self._row("MIX-a", 4, "2026-08-31T05:43:00Z", "2026-08-31T06:15:00Z")
		first = self._row("MIX-a", 5, "2026-08-31T05:27:00Z", "2026-08-31T05:43:00Z")

		ordered = manifest_row_order([second, first])

		self.assertEqual([row.stop_index for row in ordered], [5, 4])

	def test_a_standalone_row_is_a_run_of_its_own(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			manifest_row_order,
		)

		# No trip group: two of them must not be pooled into one run by an empty key.
		solo_late = frappe._dict(card_id="TSHIP-B", trip_group=None, stop_index=0,
								 start_time="2026-08-31T09:00:00Z", end_time="2026-08-31T09:30:00Z")
		solo_early = frappe._dict(card_id="TSHIP-A", trip_group=None, stop_index=0,
								  start_time="2026-08-31T04:00:00Z", end_time="2026-08-31T04:30:00Z")

		ordered = manifest_row_order([solo_late, solo_early])

		self.assertEqual([row.card_id for row in ordered], ["TSHIP-A", "TSHIP-B"])


class TestWhenTheBusIsWhere(FrappeTestCase):
	"""A row runs from the moment the bus is at its stop to the moment it reaches the
	next one, and the driver's page has to say which of those is which.

	Reading the end as the drop-off put every stop one leg late: a run that left the camp
	at 07:45 and reached 360 Car Park at 08:27 was printed as leaving at 08:27 and
	reaching 360 at 08:58.
	"""

	def test_an_outward_card_sets_its_riders_down_when_the_bus_gets_there(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			visit_times,
		)

		boards, alights = visit_times("08:27", "08:58", "OUTBOUND", camp_departure="07:45")

		self.assertEqual((boards, alights), ("07:45", "08:27"))

	def test_they_board_at_the_camp_which_is_before_any_stop(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			visit_times,
		)

		boards, _ = visit_times("08:58", "09:59", "OUTBOUND", camp_departure="07:45")

		self.assertEqual(boards, "07:45")

	def test_a_return_card_is_collected_at_its_stop_and_carried_home(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			visit_times,
		)

		self.assertEqual(
			visit_times("09:59", "10:30", "RETURN", camp_departure="07:45"),
			("09:59", "10:30"),
		)

	def test_a_run_with_no_camp_leg_recorded_boards_at_its_first_stop(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			visit_times,
		)

		self.assertEqual(visit_times("08:27", "08:58", "OUTBOUND"), ("08:27", "08:27"))


class TestEachCardBoardsAtItsOwnCamp(FrappeTestCase):
	"""A run that loads at two camps has two departures, not one repeated.

	Keyed by the run alone, both camps of 13/52665 printed 07:45 on the driver's page -
	the bus reaches the second at 08:20.
	"""

	def setUp(self):
		self.source = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_schedule",
			"transportation_schedule.py"
		))

	def test_the_departure_is_recorded_per_camp(self):
		self.assertIn('camp_departure[(row.trip_group, place)] = row.start_time', self.source)

	def test_a_card_boards_at_the_camp_it_belongs_to(self):
		self.assertIn(
			"camp_departure.get((row.trip_group, row.origin_location))", self.source
		)

	def test_a_camp_with_no_leg_recorded_falls_back_to_the_run(self):
		self.assertIn("or camp_departure.get(row.trip_group),", self.source)


class TestARunThatStoppedBeingMixedSaysSo(FrappeTestCase):
	"""AC3 has a server half, and it was in the wrong place (WI-002401).

	Taking one stop out of a merged run can leave what remains travelling only one way.
	The canvas re-stamps the blocks straight away, so the colour flips - but a row's
	direction is written from its SHIPMENT, and the shipment was still flagged Mixed. So
	the block came back green on the next page load.
	"""

	def test_the_unmerge_runs_before_the_rows_are_written(self):
		import inspect

		from one_fm.one_fm.page.transportation_schedule import transportation_schedule

		source = inspect.getsource(transportation_schedule.save_assignments)
		self.assertIn("_unmerge_unmixed_placements(items)", source)
		# Before, not after: the row direction is read off the shipment.
		self.assertLess(
			source.index("_unmerge_unmixed_placements(items)"),
			source.index("directions = _shipment_direction_flags(items)"),
		)

	def test_a_card_whose_shipment_disagrees_is_the_one_repaired(self):
		# The old rule only considered cards it had counted as Assigned, which requires
		# the shipment's direction to match the placement - so it skipped every card
		# still flagged Mixed, which is the only kind there was anything to repair.
		import inspect

		from one_fm.one_fm.page.transportation_schedule import transportation_schedule

		source = inspect.getsource(transportation_schedule._unmerge_unmixed_placements)
		self.assertIn('if "MIXED" not in placed_dirs', source)
		self.assertNotIn("assigned", source)

	def test_a_still_mixed_run_keeps_its_flag(self):
		import inspect

		from one_fm.one_fm.page.transportation_schedule import transportation_schedule

		# One MIXED block is enough to say the card is still riding a merged run.
		source = inspect.getsource(transportation_schedule._unmerge_unmixed_placements)
		self.assertIn('placed.setdefault(name, set()).add(', source)


class TestAPlacedBlockCanAlwaysBeOpened(FrappeTestCase):
	"""A placed card is Assigned, so it is not a pool card (WI-002401).

	Re-saving the plan overwrote each row's saved names with empty strings once that
	happened, and with nothing left to build a card from, the detail drawer simply
	refused to open when the block was clicked.
	"""

	def test_the_canvas_keeps_names_it_cannot_look_up(self):
		import pathlib

		canvas = pathlib.Path(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_schedule",
			"transportation_schedule.js")).read_text()
		self.assertIn("_site: card ? card.site : (i._site || ''),", canvas)
		self.assertIn("_shift: card ? card.shift_name : (i._shift || ''),", canvas)
		self.assertNotIn("_site: card ? card.site : '',", canvas)

	def test_the_load_fills_a_blank_copy_from_the_shipment(self):
		# Repairs the rows an older save already blanked, without a patch.
		import inspect

		from one_fm.one_fm.page.transportation_schedule import transportation_schedule

		source = inspect.getsource(transportation_schedule.load_assignments)
		self.assertIn('"_shift":         row.shift or held.get("shift") or ""', source)
		self.assertIn('"_stopLocation":  row.stop_location or held.get("stop_location") or ""',
					  source)
		# One query, not one per row.
		self.assertIn("shipment_meta = {", source)


# --- get_available_rambo_relievers: contextual roster card data ---

import datetime as _dt
from types import SimpleNamespace
from unittest.mock import Mock, patch

from one_fm.one_fm.page.transportation_schedule import transportation_schedule as _ts

_DAY = "2026-03-10"
_HOURS = lambda h, m=0: _dt.timedelta(hours=h, minutes=m)  # noqa: E731


def _at(day, hour, minute=0):
	return _dt.datetime.strptime(day, "%Y-%m-%d") + _dt.timedelta(hours=hour, minutes=minute)


def _emp(name, employee_name=None, shift=None):
	return frappe._dict(
		name=name, employee_name=employee_name or name, designation="Guard",
		cell_number="555", shift=shift,
	)


def _roster(employee, roster_type="Basic", shift="DAY", day=_DAY, start=None, end=None, day_off_ot=0):
	return frappe._dict(
		employee=employee, date=day, roster_type=roster_type, shift=shift,
		start_datetime=start, end_datetime=end, day_off_ot=day_off_ot,
	)


class TestAvailableRamboRelievers(FrappeTestCase):
	SHIFTS = {
		"DAY": (_HOURS(6), _HOURS(18)),
		"NIGHT": (_HOURS(20), _HOURS(6)),
		"OT": (_HOURS(18), _HOURS(22)),
	}

	def _run(self, rambos, rows, **kwargs):
		kwargs.setdefault("shift_name", "DAY")
		kwargs.setdefault("date", _DAY)
		with patch.object(_ts, "_fetch_rambo_employees", return_value=rambos), \
			patch.object(_ts, "_fetch_roster_rows", return_value=rows) as fetch, \
			patch.object(_ts, "_fetch_shift_times", return_value=self.SHIFTS), \
			patch.object(_ts.frappe.db, "get_single_value", return_value=1), \
			patch.object(_ts.frappe, "has_permission", return_value=True) as perm:
			result = _ts.get_available_rambo_relievers(**kwargs)
		return result, fetch, perm

	def test_overlap_helper_is_half_open(self):
		self.assertTrue(_ts._intervals_overlap(1, 5, 4, 8))
		self.assertTrue(_ts._intervals_overlap(1, 10, 3, 4))
		# Touching edges do not overlap.
		self.assertFalse(_ts._intervals_overlap(1, 5, 5, 8))
		self.assertFalse(_ts._intervals_overlap(5, 8, 1, 5))

	def test_trip_window_rolls_a_night_shift_to_the_next_day(self):
		date = frappe.utils.getdate(_DAY)
		start, end = _ts._trip_window(date, _HOURS(20), _HOURS(6), [])
		self.assertEqual(start, _at(_DAY, 20))
		self.assertEqual(end, _at(_DAY, 6) + _dt.timedelta(days=1))

	def test_trip_window_uses_the_earliest_trip_time_including_midnight(self):
		date = frappe.utils.getdate(_DAY)
		start, end = _ts._trip_window(date, _HOURS(6), _HOURS(18), [_HOURS(5, 30), _dt.timedelta(0)])
		self.assertEqual(start, _at(_DAY, 0))
		self.assertEqual(end, _at(_DAY, 18))

	def test_trip_window_is_none_without_times(self):
		date = frappe.utils.getdate(_DAY)
		self.assertIsNone(_ts._trip_window(date, None, _HOURS(18), []))
		self.assertIsNone(_ts._trip_window(date, _HOURS(6), None, []))

	def test_without_a_row_it_checks_general_read_permission(self):
		_result, _fetch, perm = self._run([_emp("E1")], [])
		perm.assert_called_once_with("Transportation Manifest", "read", throw=True)

	def test_with_a_row_it_checks_the_manifest_and_uses_its_date(self):
		manifest = SimpleNamespace(
			schedule_date="2026-04-02",
			check_permission=Mock(),
			transportation_manifest_details=[
				frappe._dict(trip_id="T1", scheduled_time=_dt.timedelta(0)),
				frappe._dict(trip_id="T1", scheduled_time=_HOURS(5, 30)),
				frappe._dict(trip_id="T2", scheduled_time=_HOURS(1)),
			],
		)
		row = frappe._dict(
			parent="MAN-1", operations_shift="DAY", start_time=_HOURS(6), end_time=_HOURS(18),
			trip_id="T1", scheduled_time=_HOURS(5, 30),
		)
		with patch.object(_ts.frappe.db, "get_value", return_value=row), \
			patch.object(_ts.frappe, "get_doc", return_value=manifest) as get_doc:
			# The date argument is ignored in favour of the manifest's.
			_result, fetch, perm = self._run([_emp("E1")], [], date=_DAY, row_name="ROW-1")

		get_doc.assert_called_once_with("Transportation Manifest", "MAN-1")
		manifest.check_permission.assert_called_once_with("read")
		perm.assert_not_called()
		args = fetch.call_args[0]
		self.assertEqual(args[1], frappe.utils.getdate("2026-04-02"))
		# Earliest time of the row's own trip (00:00), not another trip's.
		self.assertEqual(args[2], _at("2026-04-02", 0))

	def test_a_missing_row_is_an_error(self):
		with patch.object(_ts.frappe.db, "get_value", return_value=None):
			with self.assertRaises(frappe.DoesNotExistError):
				_ts.get_available_rambo_relievers(row_name="NOPE")

	def test_old_keys_are_still_returned(self):
		result, _f, _p = self._run([_emp("E1")], [_roster("E1")])
		for key in ("name", "employee_name", "designation", "mobile",
					"shift_name", "shift_start_time", "shift_end_time"):
			self.assertIn(key, result[0])
		self.assertEqual(result[0]["shift_name"], "DAY")
		self.assertEqual(result[0]["shift_start_time"], "06:00")
		self.assertEqual(result[0]["shift_end_time"], "18:00")

	def test_shift_fields_have_no_master_shift_fallback(self):
		result, _f, _p = self._run([_emp("E1", shift="NIGHT")], [])
		entry = result[0]
		self.assertEqual(entry["master_shift"], "NIGHT")
		self.assertIsNone(entry["shift_name"])
		self.assertIsNone(entry["shift_start_time"])
		self.assertIsNone(entry["shift_end_time"])
		self.assertFalse(entry["has_roster"])
		self.assertFalse(entry["is_ot"])
		self.assertFalse(entry["overlap"])

	def test_overtime_row_sets_the_ot_fields(self):
		rows = [
			_roster("E1", "Basic", "DAY", start=_at(_DAY, 6), end=_at(_DAY, 18)),
			_roster("E1", "Over-Time", "OT", start=_at(_DAY, 18), end=_at(_DAY, 22)),
		]
		result, _f, _p = self._run([_emp("E1")], rows, shift_name="NIGHT")
		entry = result[0]
		self.assertTrue(entry["is_ot"])
		self.assertEqual(entry["ot_shift"], "OT")
		self.assertEqual(entry["ot_start_time"], "18:00")
		self.assertEqual(entry["ot_end_time"], "22:00")
		# The Basic fields are not taken from the OT row.
		self.assertEqual(entry["shift_name"], "DAY")

	def test_basic_row_on_a_day_off_ot_counts_as_ot(self):
		rows = [_roster("E1", "Basic", "DAY", day_off_ot=1)]
		result, _f, _p = self._run([_emp("E1")], rows)
		self.assertTrue(result[0]["is_ot"])
		self.assertIsNone(result[0]["ot_shift"])

	def test_overlap_is_flagged_with_a_note_and_nobody_is_dropped(self):
		rows = [_roster("E1", "Basic", "DAY", start=_at(_DAY, 6), end=_at(_DAY, 18))]
		result, _f, _p = self._run([_emp("E1"), _emp("E2")], rows, shift_name="DAY")
		by_name = {r["name"]: r for r in result}
		self.assertEqual(len(result), 2)
		self.assertTrue(by_name["E1"]["overlap"])
		self.assertIn("06:00", by_name["E1"]["overlap_note"])
		self.assertFalse(by_name["E2"]["overlap"])
		self.assertEqual(by_name["E2"]["overlap_note"], "")

	def test_adjacent_shift_does_not_overlap(self):
		# Trip window is 06:00-18:00; the OT row starts exactly when it ends.
		rows = [_roster("E1", "Over-Time", "OT", start=_at(_DAY, 18), end=_at(_DAY, 22))]
		result, _f, _p = self._run([_emp("E1")], rows, shift_name="DAY")
		self.assertFalse(result[0]["overlap"])

	def test_previous_day_night_shift_running_into_the_trip_overlaps(self):
		prev = "2026-03-09"
		rows = [_roster("E1", "Basic", "NIGHT", day=prev,
						start=_at(prev, 20), end=_at(_DAY, 7))]
		result, _f, _p = self._run([_emp("E1")], rows, shift_name="DAY")
		entry = result[0]
		self.assertTrue(entry["overlap"])
		# Yesterday's shift is not today's roster.
		self.assertFalse(entry["has_roster"])
		self.assertIsNone(entry["shift_name"])

	def test_sort_is_non_overlapping_first_then_rostered_then_name(self):
		rambos = [_emp("A", "Zed"), _emp("B", "Amy"), _emp("C", "Bob"), _emp("D", "Cal")]
		rows = [
			_roster("A", "Basic", "DAY", start=_at(_DAY, 6), end=_at(_DAY, 18)),  # overlaps
			_roster("C", "Over-Time", "OT", start=_at(_DAY, 18), end=_at(_DAY, 22)),  # rostered
			_roster("D", "Over-Time", "OT", start=_at(_DAY, 18), end=_at(_DAY, 22)),  # rostered
		]
		result, _f, _p = self._run(rambos, rows, shift_name="DAY")
		self.assertEqual([r["employee_name"] for r in result], ["Bob", "Cal", "Amy", "Zed"])

	def test_trip_window_starts_at_the_covered_shift_when_it_is_earlier(self):
		date = frappe.utils.getdate(_DAY)
		start, end = _ts._trip_window(date, _HOURS(6), _HOURS(18), [_HOURS(6, 30)])
		self.assertEqual(start, _at(_DAY, 6))
		self.assertEqual(end, _at(_DAY, 18))

	def test_trip_window_without_a_covered_shift_ends_at_the_last_stop(self):
		date = frappe.utils.getdate(_DAY)
		self.assertEqual(
			_ts._trip_window(date, None, None, [_HOURS(5, 30), _HOURS(7)]),
			(_at(_DAY, 5, 30), _at(_DAY, 7)),
		)
		# One stop: a zero-length window, not a whole day.
		self.assertEqual(
			_ts._trip_window(date, None, None, [_HOURS(5, 30)]),
			(_at(_DAY, 5, 30), _at(_DAY, 5, 30)),
		)

	def test_overlap_helper_night_shift_crossing_midnight(self):
		night = (_at(_DAY, 20), _at(_DAY, 8) + _dt.timedelta(days=1))
		self.assertTrue(_ts._intervals_overlap(*night, _at("2026-03-11", 5, 30), _at("2026-03-11", 18)))
		self.assertFalse(_ts._intervals_overlap(*night, _at("2026-03-11", 8), _at("2026-03-11", 18)))

	def test_a_user_without_read_on_the_manifest_is_refused(self):
		manifest = SimpleNamespace(
			schedule_date=_DAY,
			check_permission=Mock(side_effect=frappe.PermissionError),
			transportation_manifest_details=[],
		)
		row = frappe._dict(parent="MAN-1", operations_shift="DAY", start_time=_HOURS(6),
						   end_time=_HOURS(18), trip_id="T1", scheduled_time=_HOURS(5, 30))
		with patch.object(_ts.frappe.db, "get_value", return_value=row), \
			patch.object(_ts.frappe, "get_doc", return_value=manifest), \
			patch.object(_ts, "_fetch_rambo_employees") as rambos:
			with self.assertRaises(frappe.PermissionError):
				_ts.get_available_rambo_relievers(row_name="ROW-1")
		rambos.assert_not_called()

	def test_basic_timing_comes_from_the_schedule_not_the_shift_master(self):
		# The schedule says 07:00-15:00 although Operations Shift DAY is 06:00-18:00.
		rows = [_roster("E1", "Basic", "DAY", start=_at(_DAY, 7), end=_at(_DAY, 15))]
		result, _f, _p = self._run([_emp("E1")], rows, shift_name="NIGHT")
		self.assertEqual(result[0]["shift_start_time"], "07:00")
		self.assertEqual(result[0]["shift_end_time"], "15:00")

	def test_three_relievers_against_a_day_shift(self):
		nxt = "2026-03-11"
		rambos = [
			_emp("N", "Nina", shift="MASTER-N"),
			_emp("D", "Dan", shift="MASTER-D"),
			_emp("O", "Omar", shift="MASTER-O"),
		]
		rows = [
			_roster("N", "Basic", "NIGHT", start=_at(_DAY, 20), end=_at(nxt, 8)),
			_roster("D", "Basic", "DAY", start=_at(_DAY, 6), end=_at(_DAY, 18)),
			_roster("D", "Over-Time", "OT", start=_at(_DAY, 18), end=_at(_DAY, 22)),
			_roster("O", "Basic", "DAY", start=_at(_DAY, 6), end=_at(_DAY, 18), day_off_ot=1),
		]
		result, _f, _p = self._run(rambos, rows, shift_name="DAY")
		by_name = {r["name"]: r for r in result}
		self.assertEqual([r["name"] for r in result], ["N", "D", "O"])
		self.assertFalse(by_name["N"]["overlap"])
		self.assertFalse(by_name["N"]["is_ot"])
		self.assertTrue(by_name["D"]["overlap"])
		self.assertTrue(by_name["D"]["is_ot"])
		self.assertTrue(by_name["O"]["overlap"])
		self.assertTrue(by_name["O"]["is_ot"])
		for r in result:
			self.assertEqual(r["master_shift"], "MASTER-" + r["name"])

	def test_the_reliever_context_returns_the_trip_camps_and_passengers(self):
		manifest = SimpleNamespace(
			schedule_date=_DAY,
			check_permission=Mock(),
			transportation_manifest_details=[
				frappe._dict(trip_id="T1", scheduled_time=_HOURS(5), employee="P1",
							 reliever_employee="R1", pickup_accommodation="ACC-01"),
				frappe._dict(trip_id="T1", scheduled_time=_HOURS(6), employee="P2",
							 reliever_employee=None, pickup_accommodation="ACC-01"),
				frappe._dict(trip_id="T1", scheduled_time=_HOURS(7), employee="P3",
							 reliever_employee=None, pickup_accommodation="ACC-02"),
				frappe._dict(trip_id="T2", scheduled_time=_HOURS(8), employee="OTHER",
							 reliever_employee=None, pickup_accommodation="ACC-09"),
			],
		)
		row = frappe._dict(
			parent="MAN-1", operations_shift="DAY", start_time=_HOURS(6), end_time=_HOURS(18),
			trip_id="T1", scheduled_time=_HOURS(5), employee="P1", reliever_employee="R1",
			pickup_accommodation="ACC-01",
		)
		with patch.object(_ts.frappe.db, "get_value", return_value=row), \
			patch.object(_ts.frappe, "get_doc", return_value=manifest):
			*_head, camps, employees = _ts._reliever_context("DAY", _DAY, "ROW-1")
		self.assertEqual(sorted(camps), ["ACC-01", "ACC-02"])
		self.assertEqual(employees, {"P1", "P2", "P3", "R1"})

	def test_the_reliever_context_without_a_row_has_no_trip(self):
		with patch.object(_ts.frappe, "has_permission", return_value=True), \
			patch.object(_ts, "_fetch_shift_times", return_value=self.SHIFTS):
			*_head, camps, employees = _ts._reliever_context("DAY", _DAY, None)
		self.assertEqual(list(camps), [])
		self.assertEqual(set(employees), set())


class TestRelieverSearchSetting(FrappeTestCase):
	"""get_available_rambo_relievers follows Transportation Settings."""

	SHIFTS = TestAvailableRamboRelievers.SHIFTS
	CONTEXT = (
		frappe.utils.getdate(_DAY), _HOURS(6), _HOURS(18), [_HOURS(6)],
		["ACC-01"], {"COVERED", "PAX"},
	)

	def _search(self, flag, pool, rows=(), row_name="ROW-1"):
		with patch.object(_ts, "_reliever_context", return_value=self.CONTEXT), \
			patch.object(_ts.frappe.db, "get_single_value", return_value=flag) as setting, \
			patch.object(_ts, "_fetch_rambo_employees", return_value=[_emp("RAMBO")]) as rambo, \
			patch.object(_ts, "_fetch_shift_working_employees", return_value=pool) as shift_pool, \
			patch.object(_ts, "_fetch_roster_rows", return_value=list(rows)), \
			patch.object(_ts, "_fetch_shift_times", return_value=self.SHIFTS):
			result = _ts.get_available_rambo_relievers(shift_name="DAY", date=_DAY, row_name=row_name)
		return result, setting, rambo, shift_pool

	def test_checked_returns_only_rambo_employees(self):
		result, setting, rambo, shift_pool = self._search(1, [_emp("WORKER")])
		setting.assert_called_once_with(
			"Transportation Settings", "restrict_reliever_search_to_rambo_employees_only"
		)
		self.assertEqual([r["name"] for r in result], ["RAMBO"])
		rambo.assert_called_once()
		shift_pool.assert_not_called()

	def test_unchecked_searches_shift_workers_in_the_trip_camps(self):
		result, _setting, rambo, shift_pool = self._search(0, [_emp("WORKER")])
		self.assertEqual([r["name"] for r in result], ["WORKER"])
		rambo.assert_not_called()
		shift_pool.assert_called_once_with(["ACC-01"], {"COVERED", "PAX"})

	def test_unchecked_without_a_row_returns_nothing(self):
		result, _setting, _rambo, shift_pool = self._search(0, [_emp("WORKER")], row_name=None)
		self.assertEqual(result, [])
		shift_pool.assert_not_called()

	def test_unchecked_drops_overlapping_employees_and_keeps_the_sort_order(self):
		pool = [_emp("A", "Zed"), _emp("B", "Amy"), _emp("C", "Bob"), _emp("D", "Cal")]
		rows = [
			_roster("A", "Basic", "DAY", start=_at(_DAY, 6), end=_at(_DAY, 18)),  # overlaps
			_roster("C", "Over-Time", "OT", start=_at(_DAY, 18), end=_at(_DAY, 22)),
			_roster("D", "Over-Time", "OT", start=_at(_DAY, 18), end=_at(_DAY, 22)),
		]
		result, *_rest = self._search(0, pool, rows)
		self.assertEqual([r["employee_name"] for r in result], ["Bob", "Cal", "Amy"])
		self.assertFalse(any(r["overlap"] for r in result))

	def test_checked_still_lists_an_overlapping_rambo_with_a_warning(self):
		rows = [_roster("RAMBO", "Basic", "DAY", start=_at(_DAY, 6), end=_at(_DAY, 18))]
		result, *_rest = self._search(1, [], rows)
		self.assertEqual([r["name"] for r in result], ["RAMBO"])
		self.assertTrue(result[0]["overlap"])


class TestFetchShiftWorkingEmployees(FrappeTestCase):
	"""The unchecked-setting query, against real Employee and Accommodation Checkin rows."""

	PREFIX = "ZZ-RELIEVER-"

	def _employee(self, key, status="Active", shift_working=1, rambo=0):
		# Plain column insert: the Employee table of a test site may lack unrelated
		# custom columns that a full Document insert would try to write.
		values = {
			"name": self.PREFIX + key, "employee_name": "Zz " + key, "status": status,
			"shift_working": shift_working, "owner": "Administrator",
			"modified_by": "Administrator", "creation": "2026-01-01 00:00:00",
			"modified": "2026-01-01 00:00:00",
		}
		if frappe.db.has_column("Employee", "custom_is_rambo_reliever"):
			values["custom_is_rambo_reliever"] = rambo
		Employee = frappe.qb.DocType("Employee")
		frappe.qb.into(Employee).columns(*values.keys()).insert(*values.values()).run()
		return values["name"]

	def _checkin(self, employee, camp, creation, kind="IN"):
		values = {
			"name": frappe.generate_hash(length=12), "employee": employee,
			"accommodation": camp, "type": kind, "owner": "Administrator",
			"modified_by": "Administrator", "creation": creation, "modified": creation,
		}
		Checkin = frappe.qb.DocType("Accommodation Checkin Checkout")
		frappe.qb.into(Checkin).columns(*values.keys()).insert(*values.values()).run()

	def setUp(self):
		if not frappe.db.has_column("Employee", "shift_working"):
			self.skipTest("Employee.shift_working is not present on this site")
		self.in_camp = self._employee("INCAMP")
		self.non_rambo_worker = self._employee("WORKER", rambo=0)
		self.rambo = self._employee("RAMBO", rambo=1)
		self.other_camp = self._employee("OTHER")
		self.inactive = self._employee("INACTIVE", status="Inactive")
		self.not_shift = self._employee("NOSHIFT", shift_working=0)
		self.covered = self._employee("COVERED")
		self.passenger = self._employee("PAX")
		self.moved = self._employee("MOVED")
		for emp in (self.in_camp, self.non_rambo_worker, self.rambo, self.inactive,
					self.not_shift, self.covered, self.passenger):
			self._checkin(emp, "ACC-RELIEVER-A", "2026-03-01 08:00:00")
		self._checkin(self.other_camp, "ACC-RELIEVER-B", "2026-03-01 08:00:00")
		# Latest IN decides the live camp: this one moved out of camp A.
		self._checkin(self.moved, "ACC-RELIEVER-A", "2026-03-01 08:00:00")
		self._checkin(self.moved, "ACC-RELIEVER-B", "2026-03-02 08:00:00")
		# An OUT check-in never counts as the live camp.
		self._checkin(self.other_camp, "ACC-RELIEVER-A", "2026-03-03 08:00:00", kind="OUT")

	def _names(self, camps, exclude=()):
		rows = _ts._fetch_shift_working_employees(camps, set(exclude))
		return [r.name for r in rows if r.name.startswith(self.PREFIX)]

	def test_returns_shift_workers_in_the_camp_whether_or_not_they_are_rambo(self):
		names = self._names(["ACC-RELIEVER-A"], [self.covered, self.passenger])
		self.assertIn(self.non_rambo_worker, names)
		self.assertIn(self.rambo, names)
		self.assertIn(self.in_camp, names)

	def test_leaves_out_other_camps_inactive_non_shift_covered_and_passengers(self):
		names = self._names(["ACC-RELIEVER-A"], [self.covered, self.passenger])
		for excluded in (self.other_camp, self.inactive, self.not_shift,
						 self.covered, self.passenger, self.moved):
			self.assertNotIn(excluded, names)

	def test_returns_the_same_columns_as_the_rambo_query(self):
		rows = _ts._fetch_shift_working_employees(["ACC-RELIEVER-A"], set())
		row = next(r for r in rows if r.name == self.non_rambo_worker)
		for key in ("name", "employee_name", "designation", "cell_number", "shift"):
			self.assertIn(key, row)

	def test_no_camps_returns_nothing(self):
		self.assertEqual(_ts._fetch_shift_working_employees([], set()), [])
