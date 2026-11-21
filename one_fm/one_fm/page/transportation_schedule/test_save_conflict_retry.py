# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The board and the manifest stop losing races with themselves.

Both pages write a document that the whole screen shares - the Route Plan behind the
canvas, the Transportation Manifest behind every chip on the sheet - and both write it
by reading it whole, changing it and saving it. Two of those overlapping meant the
slower request had opened the document before the quicker one committed, so Frappe
refused it with TimestampMismatchError: "Document has been modified after you have
opened it. Please refresh to get the latest document."

On production (RP-2026-06-1754678, 2026-09-10 10:52) that is exactly what happened -
a save committed at 10:52:41 while the next one was already in flight, and the one
that lost surfaced the popup at 10:52:57. The dispatcher then had to reload before the
next card would come off a lane, because the board reloads the plan whenever a save
fails and the reload put the removed card back.

Neither write has anything to merge: replaying it against the current document is the
state the operator asked for. These tests pin the replay down.
"""

import json
import threading
import time
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	SAVE_CONFLICT_ATTEMPTS,
	retry_on_stale_timestamp,
	save_assignments,
)


def _conflict():
	"""Raise the error Frappe raises when `modified` moved under a save."""
	raise frappe.TimestampMismatchError("Document has been modified after you have opened it")


class TestRetryOnStaleTimestamp(FrappeTestCase):
	"""The replay itself, with no document involved."""

	def setUp(self):
		# FrappeTestCase isolates each test inside one transaction, and the real
		# rollback would take the test's own fixtures with it. The full-rollback
		# behaviour is asserted separately, on the call rather than its effect.
		patcher = patch.object(frappe.db, "rollback")
		self.rollback = patcher.start()
		self.addCleanup(patcher.stop)

	def test_a_write_that_loses_the_race_is_replayed(self):
		attempts = []

		def write():
			attempts.append(1)
			if len(attempts) == 1:
				_conflict()
			return "saved"

		self.assertEqual(retry_on_stale_timestamp(write), "saved")
		self.assertEqual(len(attempts), 2)

	def test_a_write_that_wins_outright_runs_once(self):
		attempts = []

		def write():
			attempts.append(1)
			return "saved"

		self.assertEqual(retry_on_stale_timestamp(write), "saved")
		self.assertEqual(len(attempts), 1)
		self.rollback.assert_not_called()

	def test_the_conflict_popup_never_reaches_the_browser(self):
		# msgprint QUEUES the popup text and then raises, so the message outlives the
		# exception: a retry that succeeds would still deliver "Document has been
		# modified after you have opened it" to the page. AC1 says that prompt must be
		# gone, so the replay has to drop the queued message too.
		attempts = []

		def write():
			attempts.append(1)
			if len(attempts) == 1:
				frappe.local.message_log.append("the conflict popup")
				_conflict()
			return "saved"

		frappe.local.message_log = []
		self.assertEqual(retry_on_stale_timestamp(write), "saved")
		self.assertEqual(frappe.local.message_log, [])

	def test_the_rollback_is_a_full_rollback_not_a_savepoint(self):
		# MariaDB runs REPEATABLE READ here, so rolling back to a savepoint would hand
		# the retry the same stale snapshot it just failed on and it would fail again.
		# Only a full rollback opens a new transaction, and with it a new snapshot.
		attempts = []

		def write():
			attempts.append(1)
			if len(attempts) == 1:
				_conflict()
			return "saved"

		retry_on_stale_timestamp(write)

		self.rollback.assert_called_once()
		self.assertEqual(self.rollback.call_args.kwargs.get("save_point"), None)
		self.assertEqual(self.rollback.call_args.args, ())

	def test_a_deadlock_is_replayed_too(self):
		# Two saves locking vehicles in a different order: MariaDB kills one, and the
		# replay redoes it from a fresh read.
		attempts = []

		def write():
			attempts.append(1)
			if len(attempts) == 1:
				raise frappe.QueryDeadlockError("Deadlock found when trying to get lock")
			return "saved"

		self.assertEqual(retry_on_stale_timestamp(write), "saved")
		self.assertEqual(len(attempts), 2)
		self.rollback.assert_called_once()

	def test_a_document_that_stays_contended_still_raises(self):
		# Replaying forever would hide a document somebody really is fighting over.
		# Once the attempts are spent the operator gets the error and the reload advice.
		attempts = []

		def write():
			attempts.append(1)
			_conflict()

		with self.assertRaises(frappe.TimestampMismatchError):
			retry_on_stale_timestamp(write)

		self.assertEqual(len(attempts), SAVE_CONFLICT_ATTEMPTS)

	def test_the_last_attempt_leaves_the_message_for_the_operator(self):
		# The popup is only swallowed when a retry follows it. The final failure keeps
		# its message, or the page would fail silently.
		def write():
			frappe.local.message_log.append("the conflict popup")
			_conflict()

		frappe.local.message_log = []
		with self.assertRaises(frappe.TimestampMismatchError):
			retry_on_stale_timestamp(write)

		self.assertEqual(frappe.local.message_log[-1], "the conflict popup")

	def test_an_unrelated_failure_is_not_replayed(self):
		# Only a lost race is safe to repeat. A validation the plan actually failed
		# must reach the operator on the first attempt.
		attempts = []

		def write():
			attempts.append(1)
			frappe.throw("Vehicle is on STANDBY")

		with self.assertRaises(frappe.ValidationError):
			retry_on_stale_timestamp(write)

		self.assertEqual(len(attempts), 1)
		self.rollback.assert_not_called()


class TestSaveAssignmentsSurvivesAConcurrentWriter(FrappeTestCase):
	"""AC1 end to end: the card comes off the lane even when a save got there first."""

	def setUp(self):
		plan = frappe.new_doc("Route Plan")
		plan.title = frappe.generate_hash("WI-002538", 8)
		plan.effective_from = frappe.utils.today()
		plan.status = "Draft"
		plan.insert(ignore_permissions=True)
		self.plan = plan.name

		# As above: the real rollback would discard this plan along with the failed
		# attempt. Inside the one test transaction the replay still re-reads the row
		# and sees the interfering write, which is the behaviour under test.
		patcher = patch.object(frappe.db, "rollback")
		patcher.start()
		self.addCleanup(patcher.stop)

	def _save(self, items):
		return save_assignments(
			plan_name=self.plan,
			swim_items=json.dumps(items),
			assigned_cards=json.dumps([]),
		)

	def _rows(self):
		return frappe.get_all(
			"Route Plan Assignment",
			filters={"route_plan": self.plan},
			fields=["card_id"],
			order_by="idx",
		)

	def test_the_removal_persists_when_another_save_committed_first(self):
		vehicle = frappe.get_all("Vehicle", limit=1, pluck="name")
		if not vehicle:
			self.skipTest("no Vehicle on this site")

		def card(card_id, start):
			return {"cardId": card_id, "vehicleId": vehicle[0], "direction": "OUTBOUND",
					"start": f"2026-08-18T{start}:00.000Z", "end": "2026-08-18T09:00:00.000Z"}

		self._save([card("CARD-A", "06:00"), card("CARD-B", "07:00")])
		row_a = frappe.db.get_value("Route Plan Assignment",
									{"route_plan": self.plan, "card_id": "CARD-A"}, "name")

		from one_fm.operations.doctype.route_plan import route_plan

		real_get_doc = frappe.get_doc
		real_apply = route_plan.apply_plan_changes
		interfered = []
		attempts = []

		def get_doc_then_interfere(*args, **kwargs):
			doc = real_get_doc(*args, **kwargs)
			if args[:2] == ("Route Plan Assignment", row_a) and not interfered:
				interfered.append(True)
				# Somebody else's save lands on the same record between this read and our
				# save: its `modified` moves and this copy is stale.
				frappe.db.set_value("Route Plan Assignment", row_a, "buffer_minutes", 9)
			return doc

		def counted_apply(*args, **kwargs):
			attempts.append(1)
			return real_apply(*args, **kwargs)

		frappe.local.message_log = []
		with patch.object(frappe, "get_doc", side_effect=get_doc_then_interfere), \
			patch.object(route_plan, "apply_plan_changes", side_effect=counted_apply):
			# CARD-A is retimed and CARD-B taken off the lane.
			result = self._save([card("CARD-A", "06:30")])

		self.assertTrue(interfered, "the test never simulated a competing save")
		# Two attempts means the first save really was rejected and replayed. Without
		# this the test would still pass if the conflict never fired at all.
		self.assertEqual(len(attempts), 2, f"expected one replay, saved {len(attempts)}x")
		self.assertEqual(result["status"], "ok")
		# The board asked for one card on the lane, and one card is what is stored -
		# the removal was not lost and no reload was needed to make it stick (AC2).
		self.assertEqual([row.card_id for row in self._rows()], ["CARD-A"])
		self.assertEqual(frappe.local.message_log, [])


class TestTheManifestCheckInGoesThroughTheSameReplay(FrappeTestCase):
	"""The supervisor's sheet writes one shared manifest, chip after chip."""

	def test_the_check_in_api_replays_a_lost_race(self):
		import inspect

		from one_fm.one_fm.api.doc_methods import transportation_manifest

		source = inspect.getsource(transportation_manifest.update_manifest_row_checkin)
		self.assertIn("retry_on_stale_timestamp(", source)

	def test_the_read_and_the_save_are_both_inside_the_replay(self):
		# A retry that reuses the copy it already read would save the same stale
		# document and fail again, so the get_doc has to live in the replayed half.
		import inspect

		from one_fm.one_fm.api.doc_methods import transportation_manifest

		replayed = inspect.getsource(transportation_manifest._apply_row_checkin)
		self.assertIn('frappe.get_doc("Transportation Manifest", parent_manifest)', replayed)
		self.assertIn("doc.save()", replayed)

		entry = inspect.getsource(transportation_manifest.update_manifest_row_checkin)
		self.assertNotIn("doc.save()", entry)


class TestTheBoardNoLongerStartsTheRace(FrappeTestCase):
	"""AC2's half: the client stops overlapping its own saves."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_schedule",
			"transportation_schedule.js"))
		cls.sheet = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_manifest_page",
			"transportation_manifest_page.js"))

	def test_a_save_asked_for_mid_flight_waits_its_turn(self):
		self.assertIn("if (this._saveInFlight) {", self.canvas)
		self.assertIn("this._savePending = true;", self.canvas)

	def test_the_flag_is_cleared_however_the_save_ends(self):
		# always() covers success, failure and "no connection" alike. Clearing it in
		# the success callback alone would jam the board after one failed save.
		self.assertIn("always: () => {\n                        this._saveInFlight = false;",
					  self.canvas)

	def test_a_failed_save_drops_what_was_queued_behind_it(self):
		# The error handler reloads the plan; replaying a payload built before that
		# reload would push the rejected state straight back at the server.
		self.assertIn("this._savePending = false;\n                        this._savePendingOnError = null;",
					  self.canvas)

	def test_the_check_in_sheet_queues_its_writes(self):
		self.assertIn("function queueCheckIn(callOpts)", self.sheet)
		self.assertIn("function drainCheckInQueue()", self.sheet)
		# Both writers of the manifest go through it - the chip toggles and the
		# reliever confirmation - because they write the same parent document.
		self.assertEqual(self.sheet.count("queueCheckIn({"), 2)

	def test_the_sheet_keeps_every_queued_write(self):
		# Unlike the board, two taps are usually two different rows, so the queue is
		# FIFO and nothing may be coalesced away.
		self.assertIn("checkInQueue.push(callOpts);", self.sheet)
		self.assertIn("checkInQueue.shift();", self.sheet)


# ── Several planners on one plan ────────────────────────────────────────────


def _board(plan):
	"""What a board holds after loading the plan: its items and the versions it saw."""
	from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
		load_assignments,
	)

	loaded = load_assignments(plan)
	return loaded["swim_items"], {i["cardId"]: i["rowModified"] for i in loaded["swim_items"]}


def _card(card_id, vehicle, start="06:00", end="07:00", trip=None, headcount=1):
	return {
		"cardId": card_id, "vehicleId": vehicle, "direction": "OUTBOUND",
		"start": f"2026-11-01T{start}:00.000Z", "end": f"2026-11-01T{end}:00.000Z",
		"tripId": trip, "tripName": trip, "headcount": headcount,
	}


def _save_board(plan, items, known=None):
	return save_assignments(
		plan, json.dumps(items), "[]", "{}", json.dumps(known) if known is not None else None
	)


def _placed(plan):
	from one_fm.operations.doctype.route_plan.route_plan import get_plan_rows

	return {row.card_id: row.vehicle for row in get_plan_rows(plan, fields=["card_id", "vehicle"])}


class TestAStaleBoardNeverUndoesAnotherPlanner(FrappeTestCase):
	def setUp(self):
		from one_fm.operations.doctype.route_plan_assignment.test_route_plan_assignment import (
			make_route_plan,
		)

		vehicles = frappe.get_all("Vehicle", limit=2, pluck="name", order_by="name asc")
		if len(vehicles) < 2:
			self.skipTest("needs two vehicles")
		self.v1, self.v2 = vehicles
		self.plan = make_route_plan()
		_save_board(self.plan, [_card("CARD-X", self.v1), _card("CARD-Y", self.v1, "09:00", "10:00")])

	def test_a_card_moved_by_another_planner_stays_where_they_put_it(self):
		first, first_known = _board(self.plan)
		second, second_known = _board(self.plan)
		for item in second:
			if item["cardId"] == "CARD-X":
				item["vehicleId"] = self.v2
		_save_board(self.plan, second, second_known)

		result = _save_board(self.plan, first, first_known)

		self.assertEqual(_placed(self.plan)["CARD-X"], self.v2)
		self.assertEqual([i["cardId"] for i in result["stale"]], ["CARD-X"])
		self.assertEqual(result["stale"][0]["vehicleId"], self.v2)

	def test_a_card_another_planner_placed_is_not_deleted(self):
		first, first_known = _board(self.plan)
		second, second_known = _board(self.plan)
		_save_board(self.plan, second + [_card("CARD-Z", self.v2)], second_known)

		result = _save_board(self.plan, first, first_known)

		self.assertIn("CARD-Z", _placed(self.plan))
		self.assertEqual([i["cardId"] for i in result["stale"]], ["CARD-Z"])

	def test_a_board_that_sends_no_versions_still_saves_as_before(self):
		items, _known = _board(self.plan)

		_save_board(self.plan, [i for i in items if i["cardId"] != "CARD-Y"])

		self.assertEqual(set(_placed(self.plan)), {"CARD-X"})

	def test_a_trip_split_across_vehicles_is_refused_with_todays_message(self):
		_save_board(self.plan, [_card("CARD-X", self.v1, trip="T-1"),
								_card("CARD-Y", self.v1, "06:30", "07:30", trip="T-1")])

		with self.assertRaises(frappe.ValidationError) as caught:
			_save_board(self.plan, [_card("CARD-X", self.v1, trip="T-1"),
									_card("CARD-Y", self.v2, "06:30", "07:30", trip="T-1")])

		self.assertIn("are split across vehicles", str(caught.exception))


class TestTheDeskFormIsHeldToThePlanRules(FrappeTestCase):
	VEHICLE = "VHL-L-0022"

	def test_an_assignment_that_overloads_a_bus_is_refused_with_todays_message(self):
		from one_fm.operations.doctype.route_plan.test_route_plan import pin_three_passenger_seats
		from one_fm.operations.doctype.route_plan_assignment.test_route_plan_assignment import (
			make_route_plan,
		)

		if not frappe.db.exists("Vehicle", self.VEHICLE):
			self.skipTest(f"Fixture vehicle {self.VEHICLE} missing on this site")
		pin_three_passenger_seats(self.VEHICLE)
		plan = make_route_plan()
		_save_board(plan, [_card("CARD-1", self.VEHICLE, trip="T-1", headcount=2)])

		row = frappe.get_doc({
			"doctype": "Route Plan Assignment", "route_plan": plan, "card_id": "CARD-2",
			"vehicle": self.VEHICLE, "direction": "OUTBOUND", "trip_group": "T-1",
			"trip_name": "T-1", "headcount": 2,
			"start_time": "2026-11-01T06:00:00.000Z", "end_time": "2026-11-01T07:00:00.000Z",
		})
		with self.assertRaises(frappe.ValidationError) as caught:
			row.insert()

		self.assertIn("Capacity Exceeded", str(caught.exception))


class _Planner(threading.Thread):
	"""A second planner: its own connection, its own transaction, committed at the end."""

	def __init__(self, work):
		super().__init__(daemon=True)
		self.work = work
		self.site = frappe.local.site
		self.sites_path = frappe.local.sites_path
		self.error = self.result = None
		self.elapsed = None

	def run(self):
		frappe.init(site=self.site, sites_path=self.sites_path)
		frappe.connect()
		frappe.set_user("Administrator")
		frappe.db.sql("set session innodb_lock_wait_timeout = 15")
		started = time.monotonic()
		try:
			self.result = self.work()
			frappe.db.commit()
		except Exception as e:
			self.error = e
			frappe.db.rollback()
		finally:
			self.elapsed = time.monotonic() - started
			frappe.destroy()


class TestPlannersOnDifferentVehiclesDoNotWait(FrappeTestCase):
	"""Two real connections, so the fixtures are committed and removed by hand."""

	VEHICLE = "VHL-L-0022"

	def setUp(self):
		from one_fm.operations.doctype.route_plan_assignment.test_route_plan_assignment import (
			make_route_plan,
		)

		vehicles = frappe.get_all("Vehicle", filters={"name": ["!=", self.VEHICLE]}, limit=2,
								  pluck="name", order_by="name asc")
		if len(vehicles) < 2 or not frappe.db.exists("Vehicle", self.VEHICLE):
			self.skipTest("needs three vehicles, one of them the 4-seat fixture")
		self.v1, self.v2 = vehicles
		self.seats = frappe.db.get_value(
			"Vehicle", self.VEHICLE,
			["seats", "custom_includes_driver_seat", "custom_max_passenger_capacity"], as_dict=True,
		)
		self.plan = make_route_plan()
		_save_board(self.plan, [_card("CARD-A", self.v1), _card("CARD-B", self.v2),
								_card("CARD-C", self.VEHICLE, trip="T-C")])
		frappe.db.commit()

	def tearDown(self):
		frappe.db.rollback()
		frappe.db.delete("Route Plan Assignment", {"route_plan": self.plan})
		frappe.db.delete("Route Plan", {"name": self.plan})
		frappe.db.set_value("Vehicle", self.VEHICLE, dict(self.seats), update_modified=False)
		frappe.db.commit()

	def _hold(self, vehicles):
		"""This connection takes the vehicle locks a save would, and keeps them."""
		from one_fm.operations.doctype.route_plan.route_plan import get_plan_rows

		get_plan_rows(self.plan, vehicles=vehicles, for_update=True)

	def test_a_save_on_another_vehicle_finishes_without_waiting(self):
		self._hold([self.v1])
		other = _Planner(lambda: _save_board(self.plan, [
			_card("CARD-A", self.v1), _card("CARD-B", self.v2, "06:30", "07:30"),
			_card("CARD-C", self.VEHICLE, trip="T-C"),
		]))
		other.start()
		other.join(20)
		frappe.db.rollback()

		self.assertIsNone(other.error)
		self.assertLess(other.elapsed, 2)
		start = frappe.db.get_value("Route Plan Assignment",
									{"route_plan": self.plan, "card_id": "CARD-B"}, "start_time")
		self.assertTrue(start.startswith("2026-11-01T06:30"), start)

	def test_a_save_on_the_same_vehicle_is_judged_on_the_first_ones_result(self):
		from one_fm.operations.doctype.route_plan.test_route_plan import pin_three_passenger_seats

		pin_three_passenger_seats(self.VEHICLE)
		frappe.db.commit()
		items, known = _board(self.plan)
		# Each save alone fits a 3-seat bus (1 + 2); together they carry 5.
		mine = items + [_card("CARD-D", self.VEHICLE, trip="T-C", headcount=2)]
		theirs = items + [_card("CARD-E", self.VEHICLE, trip="T-C", headcount=2)]

		_save_board(self.plan, mine, known)
		other = _Planner(lambda: _save_board(self.plan, theirs, known))
		other.start()
		time.sleep(1)
		frappe.db.commit()
		other.join(20)

		self.assertIsInstance(other.error, frappe.ValidationError)
		self.assertIn("Capacity Exceeded", str(other.error))
		self.assertNotIn("CARD-E", _placed(self.plan))

	def test_the_same_card_on_two_vehicles_goes_to_the_first(self):
		items, known = _board(self.plan)

		_save_board(self.plan, items + [_card("CARD-NEW", self.v1, "11:00", "12:00")], known)
		other = _Planner(lambda: _save_board(
			self.plan, items + [_card("CARD-NEW", self.v2, "11:00", "12:00")], known
		))
		other.start()
		time.sleep(1)
		frappe.db.commit()
		other.join(20)

		self.assertIsInstance(other.error, frappe.ValidationError)
		self.assertIn("was just placed by another planner", str(other.error))
		self.assertEqual(_placed(self.plan)["CARD-NEW"], self.v1)
