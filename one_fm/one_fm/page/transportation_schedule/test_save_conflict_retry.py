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
			filters={"parent": self.plan},
			fields=["card_id"],
			order_by="idx",
		)

	def test_the_removal_persists_when_another_save_committed_first(self):
		self._save([
			{"cardId": "CARD-A", "vehicleId": "V-1", "direction": "OUTBOUND"},
			{"cardId": "CARD-B", "vehicleId": "V-1", "direction": "OUTBOUND"},
		])

		real_get_doc = frappe.get_doc
		interfered = []
		reads = []

		def get_doc_then_interfere(*args, **kwargs):
			doc = real_get_doc(*args, **kwargs)
			# save_assignments' own read of the plan. Frappe makes a second, locking
			# read inside save() (load_doc_before_save) - that one is the conflict
			# check, not an attempt, so it is not counted.
			if args and args[0] == "Route Plan" and not kwargs.get("for_update"):
				reads.append(args[1])
			if args and args[0] == "Route Plan" and not interfered:
				interfered.append(True)
				# Somebody else's save lands between this read and our save, exactly
				# as it did on 2026-09-10: `modified` moves and this copy is stale.
				frappe.db.set_value("Route Plan", self.plan, "last_modified_by_user",
									"Administrator")
			return doc

		frappe.local.message_log = []
		with patch.object(frappe, "get_doc", side_effect=get_doc_then_interfere):
			result = self._save([
				{"cardId": "CARD-A", "vehicleId": "V-1", "direction": "OUTBOUND"},
			])

		self.assertTrue(interfered, "the test never simulated a competing save")
		# Two reads of the plan means the first save really was rejected and replayed.
		# Without this the test would still pass if the conflict never fired at all.
		self.assertEqual(len(reads), 2, f"expected one replay, plan was read {len(reads)}x")
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
