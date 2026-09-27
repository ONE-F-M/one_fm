# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""one vehicle, several runs, and an attendance check that leaked between them.

A Transportation Manifest is one VEHICLE for one DAY, and a vehicle drives several runs
in a day. The attendance-check pointer was a single Int on the manifest, so triggering
the check on S-801 advanced the number S-802 was reading as well: locking one run locked
its neighbour, and completing one reopened the other.

The pointer is now kept per run. The thing that needed the most care is the manifest that
is already half-checked when this ships: it carries one number for the whole vehicle, and
starting every run at 0 would silently REOPEN stops a supervisor had already verified.
Every run inherits the old number the first time the map is read instead, so nothing that
was locked comes unlocked.
"""

import json
import pathlib
import shutil
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_manifest.manifest_sheet import (
	_run_stop_sequences,
)

SHEET = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_manifest_page",
	"transportation_manifest_page.js"
))


def _manifest(rows, active=0, by_trip=None):
	"""A manifest carrying `rows` of (trip_id, stop_sequence), not saved."""
	doc = frappe.new_doc("Transportation Manifest")
	doc.schedule_date = frappe.utils.today()
	doc.active_stop_sequence = active
	if by_trip is not None:
		doc.active_stop_by_trip = json.dumps(by_trip)
	for trip_id, seq in rows:
		doc.append("transportation_manifest_details", {
			"trip_id": trip_id,
			"stop_sequence": seq,
			"employee_action": "Boarding",
		})
	return doc


class TestThePointerIsPerRun(FrappeTestCase):
	"""AC1: S-801's lock state is S-801's alone."""

	def test_each_run_keeps_its_own_pointer(self):
		doc = _manifest([("S-801", 1), ("S-802", 1)], by_trip={"S-801": 2})

		self.assertEqual(doc.active_stop_for("S-801"), 2)
		self.assertEqual(doc.active_stop_for("S-802"), 0)

	def test_the_runs_are_listed_in_the_order_the_rows_mention_them(self):
		doc = _manifest([("S-802", 1), ("S-801", 1), ("S-802", 2)])

		self.assertEqual(doc.trip_keys(), ["S-802", "S-801"])

	def test_a_row_with_no_run_still_has_somewhere_to_keep_state(self):
		doc = _manifest([(None, 1)], by_trip={"": 3})

		self.assertEqual(doc.trip_keys(), [""])
		self.assertEqual(doc.active_stop_for(None), 3)

	def test_an_unreadable_map_does_not_take_the_manifest_down(self):
		doc = _manifest([("S-801", 1)])
		doc.active_stop_by_trip = "{not json"

		self.assertEqual(doc.active_stop_map(), {})


class TestAnInFlightManifestKeepsItsLocks(FrappeTestCase):
	"""The migration case: nothing that was verified comes unlocked."""

	def test_every_run_inherits_the_old_vehicle_wide_pointer(self):
		# Stop 1 was checked and locked on both runs under the old single pointer.
		doc = _manifest([("S-801", 1), ("S-802", 1)], active=2)

		self.assertEqual(doc.active_stop_map(), {"S-801": 2, "S-802": 2})
		self.assertEqual(doc.active_stop_for("S-801"), 2)
		self.assertEqual(doc.active_stop_for("S-802"), 2)

	def test_a_manifest_that_never_started_checks_stays_empty(self):
		doc = _manifest([("S-801", 1), ("S-802", 1)], active=0)

		self.assertEqual(doc.active_stop_map(), {})

	def test_the_split_map_wins_once_it_exists(self):
		# After the first per-run write the legacy field is only a high-water mark.
		doc = _manifest([("S-801", 1), ("S-802", 1)], active=9, by_trip={"S-801": 1})

		self.assertEqual(doc.active_stop_map(), {"S-801": 1})
		self.assertEqual(doc.active_stop_for("S-802"), 0)


class TestTheLockFreezesOnlyItsOwnRun(FrappeTestCase):
	"""enforce_stop_locking judges a row against ITS run's pointer."""

	def _saved(self, rows, by_trip):
		doc = _manifest(rows, by_trip=by_trip)
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		return doc

	def test_a_completed_stop_on_one_run_cannot_be_edited(self):
		doc = self._saved([("S-801", 1)], by_trip={"S-801": 2})
		doc.reload()
		doc.transportation_manifest_details[0].attendance_status = "Absent"

		with self.assertRaises(frappe.ValidationError):
			doc.save()

	def test_the_same_stop_number_on_another_run_stays_editable(self):
		# The defect: S-802's stop 1 was frozen because S-801 had moved past stop 1.
		doc = self._saved([("S-801", 1), ("S-802", 1)], by_trip={"S-801": 2})
		doc.reload()
		s802 = [r for r in doc.transportation_manifest_details if r.trip_id == "S-802"][0]
		s802.attendance_status = "Present"

		doc.save()   # must not throw

		doc.reload()
		after = [r for r in doc.transportation_manifest_details if r.trip_id == "S-802"][0]
		self.assertEqual(after.attendance_status, "Present")

	def test_nothing_is_frozen_before_any_check_starts(self):
		doc = self._saved([("S-801", 1)], by_trip={})
		doc.reload()
		doc.transportation_manifest_details[0].attendance_status = "Present"

		doc.save()   # the compiler and dispatchers still populate freely


class TestMovingOneRunsPointer(FrappeTestCase):
	"""set_active_stop_for writes the map and leaves the others alone."""

	def _saved(self):
		doc = _manifest([("S-801", 1), ("S-802", 1)])
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		return doc

	def test_only_the_named_run_moves(self):
		doc = self._saved()

		doc.set_active_stop_for("S-801", 1)
		doc.reload()

		self.assertEqual(doc.active_stop_for("S-801"), 1)
		self.assertEqual(doc.active_stop_for("S-802"), 0)

	def test_the_flat_field_follows_the_furthest_run(self):
		# Kept in step for anything still reading it; no lock is decided from it now.
		doc = self._saved()

		doc.set_active_stop_for("S-801", 1)
		doc.set_active_stop_for("S-802", 3)
		doc.reload()

		self.assertEqual(int(doc.active_stop_sequence), 3)


class TestTheSheetSaysWhichRun(FrappeTestCase):
	"""AC2 + AC3, and the endpoints carrying the run."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.sheet = SHEET.read_text()

	def test_the_trigger_button_names_its_run(self):
		self.assertIn("Trigger Attendance Check${runSuffix}", self.sheet)
		self.assertIn("const runSuffix = tripLabel ? ` — ${escHtml(tripLabel)}` : \"\";",
					  self.sheet)

	def test_the_lock_button_names_its_run(self):
		self.assertIn("Complete &amp; Lock Stop ${seq}${lockSuffix}", self.sheet)
		self.assertIn("const lockSuffix = tripLabel ? ` (${escHtml(tripLabel)})` : \"\";",
					  self.sheet)

	def test_a_departure_nobody_boards_at_offers_no_check(self):
		# AC3: a return-only run leaving its camp empty has nobody to verify, and
		# triggering it would advance that run past a stop with nothing in it.
		self.assertIn("const nobodyBoards = employees.length === 0;", self.sheet)
		self.assertIn("if (manifestName && canTrigger && !nobodyBoards) {", self.sheet)

	def test_the_lock_button_is_still_offered_on_an_active_stop(self):
		# Suppression is for the TRIGGER only - a supervisor must still be able to
		# close a stop they have already opened.
		self.assertIn("} else if (manifestName && isActive) {", self.sheet)

	def test_both_endpoints_are_told_which_run(self):
		self.assertIn("trip_id: tripId || \"\"", self.sheet)
		self.assertEqual(self.sheet.count("trip_id: tripId || \"\""), 2)

	def test_the_page_reads_the_per_run_map(self):
		self.assertIn("const activeByTrip = meta.active_stop_by_trip || {};", self.sheet)
		self.assertIn('const activeStop = parseInt(activeByTrip[trip.id || ""], 10) || 0;',
					  self.sheet)

	def test_the_vehicle_wide_pointer_no_longer_drives_the_lock(self):
		self.assertNotIn("const activeStop = meta.active_stop_sequence || 0;", self.sheet)


TRIGGER_HARNESS = frappe.get_app_path("one_fm", "tests", "js", "depart_trigger_harness.js")


def can_trigger(isMixed=True, isActive=False, **args):
	"""Run the SHIPPED canTrigger decision from renderDepartCard."""
	out = subprocess.run(
		["node", TRIGGER_HARNESS,
		 json.dumps(dict(args, isMixed=isMixed, isActive=isActive))],
		capture_output=True, text=True, env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
		check=True,
	)
	return json.loads(out.stdout)["canTrigger"]


class TestEveryRunCanStartItsOwnCheck(FrappeTestCase):
	"""Six of seven runs on a vehicle had no Trigger button, and a second camp had none ever.

	Two faults, both from reading ``stop_sequence`` as something it is not. It is numbered
	across the VEHICLE, not within a run: S-401 loads at stops 1 and 5 while S-402 is stop
	2 and S-403 is stop 3.

	* The button was offered when ``seq === 1``, so only a run whose boarders happen to
	  start at stop 1 ever had one. On VHL-L-0004 that was S-101 alone - S-102 to S-107
	  carry seqs 3, 5, 8, 9, 3 and 13.
	* A merged run was pinned to its FIRST camp and nowhere else, on the reading that it
	  leaves one origin. It can load at two, and then the second camp's passengers could
	  never mark attendance at all - S-401's Mangaf card stayed "Locked until triggered"
	  for the rest of the day, with six people aboard.

	Both now walk the run's own camps by POSITION. The original concern still holds, and
	the tests below are mostly about that: a camp is offered only once the one before it
	is COMPLETE, never merely triggered.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not shutil.which("node"):
			raise cls.failureException("node is needed to run the shipped rule")

	def test_a_run_starting_at_stop_one_can_trigger(self):
		self.assertTrue(can_trigger(activeStop=0, campIndex=0, activeIndex=0))

	def test_a_run_starting_further_along_can_trigger_too(self):
		# S-102's camp carries seq 3. Its seq is irrelevant - it is the run's first pickup.
		self.assertTrue(can_trigger(activeStop=0, campIndex=0, activeIndex=0))

	def test_a_second_camp_is_not_offered_before_the_first(self):
		self.assertFalse(can_trigger(activeStop=0, campIndex=1, activeIndex=0))

	def test_an_open_camp_is_completed_not_triggered_again(self):
		self.assertFalse(can_trigger(activeStop=1, campIndex=0, activeIndex=0, isActive=True))

	def test_a_second_camp_waits_while_the_first_is_still_open(self):
		# Triggered is not completed. That concern must survive.
		self.assertFalse(can_trigger(activeStop=1, campIndex=1, activeIndex=0))

	def test_a_second_camp_opens_once_the_first_is_complete(self):
		# The reported gap: S-401's Mangaf camp, six passengers, previously unreachable.
		self.assertTrue(can_trigger(activeStop=2, campIndex=1, activeIndex=1))

	def test_a_completed_camp_is_not_offered_again(self):
		self.assertFalse(can_trigger(activeStop=2, campIndex=0, activeIndex=1))

	def test_nothing_is_offered_once_every_camp_is_done(self):
		self.assertFalse(can_trigger(activeStop=6, campIndex=1, activeIndex=-1))

	def test_the_decision_is_a_position_not_a_seq(self):
		page = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_manifest_page",
			"transportation_manifest_page.js"))
		self.assertIn("position === activeIndex && !isActive", page)
		self.assertNotIn("(seq === 1 && !activeStop)", page)

	def test_both_loops_step_over_the_other_runs_stops(self):
		page = frappe.read_file(frappe.get_app_path(
			"one_fm", "one_fm", "page", "transportation_manifest_page",
			"transportation_manifest_page.js"))
		self.assertEqual(page.count(">= activeStop)"), 1)
		self.assertEqual(page.count(">= o.activeStop)"), 1)


class TestTheRunWalksItsOwnStops(FrappeTestCase):
	"""The server half: "the next stop of this run", read off the run's own rows.

	``active + 1`` assumed a run's stops were contiguous. They are not - S-401 holds 1 and
	5 - so completing stop 1 left the pointer at 2 and stop 5 failed the test. The second
	camp was unreachable through the API as well as through the button.
	"""

	def _doc(self, *rows):
		return frappe._dict(transportation_manifest_details=[
			frappe._dict(trip_id=tid, stop_sequence=seq) for tid, seq in rows
		])

	def test_a_runs_stops_are_read_off_its_own_rows(self):
		doc = self._doc(("T1", 1), ("T1", 5), ("T2", 2), ("T3", 3))

		self.assertEqual(_run_stop_sequences(doc, "T1"), [1, 5])

	def test_another_runs_stops_are_not_borrowed(self):
		doc = self._doc(("T1", 1), ("T1", 5), ("T2", 2))

		self.assertEqual(_run_stop_sequences(doc, "T2"), [2])

	def test_duplicate_rows_at_one_stop_are_one_stop(self):
		# Every passenger boarding there has a row.
		doc = self._doc(("T1", 1), ("T1", 1), ("T1", 5))

		self.assertEqual(_run_stop_sequences(doc, "T1"), [1, 5])

	def test_a_run_with_no_rows_has_no_stops(self):
		self.assertEqual(_run_stop_sequences(self._doc(("T1", 1)), "T9"), [])

	def test_rows_without_a_sequence_are_skipped(self):
		doc = self._doc(("T1", 1), ("T1", None), ("T1", 0))

		self.assertEqual(_run_stop_sequences(doc, "T1"), [1])
