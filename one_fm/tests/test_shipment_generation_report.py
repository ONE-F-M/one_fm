# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Generate Shipments leaves no eligible employee without a card, or says why.

- The run kept deleting the overflow cards it had just made: their `#n` keys are never
  produced and the prune's keep set held only the cards that existed before the run.
- A checked-out employee still produced demand, so they stayed on a card.
- Mahboula camps were keyed under whichever check-in the SQL returned first.
- Riders who left or went on leave stayed on placed cards the roster no longer produces.
- A skipped employee left no trace; a scheduled run now logs and emails the reasons.
"""

from contextlib import nullcontext
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from one_fm.one_fm.doctype.transportation_shipment import shipment_generator as gen
from one_fm.one_fm.page.transportation_schedule import traceability_matrix as matrix
from one_fm.one_fm.page.transportation_schedule import transportation_schedule as ts
from one_fm.tests.test_shipment_rider_reconcile import DEMAND, ReconcileCase, _key, _roster


def _demand(tail, *ids):
	return dict(DEMAND, group_token=f"RECONCILE-TEST|{tail}", employees=_roster(*ids))


def _tables(shifts, employees, checkin_labels, stops, card_keys=(), roster=None):
	"""A frappe.get_all stand-in for the demand builder's reads.

	``employees`` is ``{employee: master shift}``; ``roster`` is today's Employee Schedule
	rows, by default one Working Basic row on the master shift.
	"""
	if roster is None:
		roster = [_row(e, s) for e, s in employees.items() if s]

	def get_all(doctype, filters=None, fields=None, pluck=None, **kwargs):
		if doctype == "Operations Shift":
			return [frappe._dict(name=s, site="SITE") for s in shifts]
		if doctype == "Employee Schedule":
			wanted = (filters or {}).get("employee_availability")
			return [r for r in roster if not wanted or r.employee_availability == wanted]
		if doctype == "Employee":
			if pluck:
				return list(employees)
			rows = [frappe._dict(name=e, shift=s) for e, s in employees.items()]
			if "shift" in (filters or {}):
				rows = [r for r in rows if r.shift in filters["shift"][1]]
			return rows
		if doctype == "Transportation Shipment":
			return list(card_keys)
		if doctype == "Accommodation":
			if pluck:
				wanted = set(filters["accommodation"][1])
				return [name for name, label in checkin_labels.items() if label in wanted]
			if "transport_stop_location" in (fields or []):
				return [frappe._dict(name=a, transport_stop_location="LOC") for a in stops]
			return [frappe._dict(name=a, accommodation=label) for a, label in checkin_labels.items()]
		return []

	return get_all


def _row(emp, shift, availability="Working", roster_type="Basic"):
	return frappe._dict(employee=emp, shift=shift, employee_availability=availability, roster_type=roster_type)


def _checkin(emp, acc, checked_out=0):
	return frappe._dict(employee=emp, accommodation=acc, checked_out=checked_out)


class TestTheDemand(ReconcileCase):
	def _grouped(self, get_all, checkins, skipped=None):
		with patch.object(ts.frappe, "get_all", side_effect=get_all), \
				patch.object(ts, "apply_to_shift_map", side_effect=lambda m: m), \
				patch.object(matrix, "_latest_checkins", return_value=checkins):
			return ts.get_grouped_employees_by_accommodation(skipped=skipped)

	def test_a_checked_out_employee_produces_no_demand_and_leaves_the_card(self):
		get_all = _tables(["S1"], {"E1": "S1", "E2": "S1"}, {"ACC-1": "Camp One"}, ["ACC-1"])
		skipped = {}
		nested = self._grouped(
			get_all, {"E1": _checkin("E1", "ACC-1"), "E2": _checkin("E2", "ACC-1", checked_out=1)}, skipped
		)

		self.assertEqual(nested["ACC-1"]["shifts"], {"S1": ["E1"]})
		self.assertIn("E2", skipped)

		demand = _demand("CO", *nested["ACC-1"]["shifts"]["S1"])
		key, _pair = gen._generation_key(demand, "Outward")
		card = self._card(key, ["E1", "E2"])
		self._distribute(self._cards(card), key, demand["employees"])
		self.assertEqual(self._riders(card), ["E1"])

	def test_the_mahboula_id_does_not_follow_the_newest_check_in(self):
		labels = {"ACC-13": "Mahboula 13", "ACC-03": "Mahboula 3"}
		keys = ["OPS|ACC-03|S1|LOC|Direct|Outward", "OPS|ACC-03|S1|LOC|Direct|Return"]
		get_all = _tables(["S1"], {"E1": "S1", "E2": "S1"}, labels, ["ACC-03", "ACC-13"], keys)
		# The newest row first: the old query picked this camp's id for the whole group.
		checkins = {"E1": _checkin("E1", "ACC-13"), "E2": _checkin("E2", "ACC-03")}

		nested = self._grouped(get_all, checkins)

		self.assertEqual(nested["Mahboula Camp"]["lookup_id"], "ACC-03")
		self.assertEqual(sorted(nested["Mahboula Camp"]["shifts"]["S1"]), ["E1", "E2"])

	def test_with_no_card_the_lowest_mahboula_id_is_used(self):
		get_all = _tables([], {}, {"ACC-13": "Mahboula 13", "ACC-03": "Mahboula 3"}, [])
		with patch.object(ts.frappe, "get_all", side_effect=get_all):
			self.assertEqual(ts._mahboula_lookup_id({"Mahboula 3", "Mahboula 13"}), "ACC-03")

	def test_no_roster_row_and_an_inactive_rostered_shift_are_named(self):
		get_all = _tables(["S1"], {"E1": "S1", "E2": "S1"}, {}, [], roster=[_row("E2", "S-OLD")])
		skipped = {}
		self._grouped(get_all, {}, skipped)

		self.assertEqual(skipped["E1"], "Not rostered to work today")
		self.assertEqual(skipped["E2"], "Rostered shift S-OLD is not Active")

	def test_demand_follows_todays_roster_not_the_master_shift(self):
		# All four share master shift S1, as every Jazeera employee shares Morning-5.
		employees = {"E1": "S1", "E2": "S1", "E3": "S1", "E4": "S1"}
		roster = [
			_row("E1", "S2"),
			_row("E2", "S3"),
			_row("E3", "S1", availability="Day Off"),
			_row("E4", "S3", roster_type="Over-Time"),
			_row("E4", "S2"),
		]
		get_all = _tables(["S1", "S2", "S3"], employees, {"ACC-1": "Camp One"}, ["ACC-1"], roster=roster)
		checkins = {e: _checkin(e, "ACC-1") for e in employees}
		skipped = {}

		nested = self._grouped(get_all, checkins, skipped)

		shifts = {s: sorted(ids) for s, ids in nested["ACC-1"]["shifts"].items()}
		self.assertEqual(shifts, {"S2": ["E1", "E4"], "S3": ["E2"]})
		self.assertEqual(skipped, {"E3": "Not rostered to work today"})

	def test_a_reliever_rides_the_shift_they_cover(self):
		get_all = _tables(["S1", "S2"], {"E1": "S1", "R1": "S1"}, {"ACC-1": "Camp One"}, ["ACC-1"])
		checkins = {e: _checkin(e, "ACC-1") for e in ("E1", "R1")}
		relieve = {"R1": {"shift": "S2", "relieving_employee": "E1"}}
		with patch("one_fm.one_fm.doctype.transportation_shipment.roster_overlay.absent_employees", return_value={}), \
				patch("one_fm.one_fm.doctype.transportation_shipment.roster_overlay.relieving_assignments", return_value=relieve), \
				patch.object(ts.frappe, "get_all", side_effect=get_all), \
				patch.object(matrix, "_latest_checkins", return_value=checkins):
			nested = ts.get_grouped_employees_by_accommodation()

		self.assertEqual(nested["ACC-1"]["shifts"], {"S2": ["R1"]})


class TestSkipReasons(FrappeTestCase):
	def test_a_site_at_zero_zero_is_skipped_with_the_no_route_reason(self):
		def get_all(doctype, **kwargs):
			return {
				"Operations Shift": [frappe._dict(
					name="S1", site="SITE-1", start_time="08:00:00", end_time="16:00:00",
					expected_arrival_time_at_site=None,
				)],
				"Operations Site": [frappe._dict(name="SITE-1", site_location="LOC-ZERO")],
			}.get(doctype, [])

		skipped = {}
		with patch.object(gen.frappe, "get_all", side_effect=get_all), \
				patch.object(gen, "driver_employees", return_value=set()), \
				patch.object(gen, "get_coords", side_effect=lambda dt, name: (29.1, 48.1) if dt == "Accommodation" else None):
			demands = gen.build_demand_descriptors(
				{"ACC-T": {"lookup_id": "ACC-T", "shifts": {"S1": ["E1", "E2"]}}}, skipped=skipped
			)

		self.assertEqual(demands, [])
		self.assertEqual(set(skipped), {"E1", "E2"})
		self.assertIn("SITE-1", skipped["E1"])
		self.assertIn("no route", skipped["E1"])

	def test_zero_coordinates_count_as_none(self):
		with patch.object(ts.frappe.db, "get_value", return_value=(0.0, 0.0)):
			self.assertIsNone(ts.get_coords("Location", "LOC-ZERO"))

	def test_the_summary_lists_missing_rows_with_their_reason(self):
		rows = [
			{"id": "E1", "name": "One", "status": matrix.STATUS_MISSING},
			{"id": "E2", "name": "Two", "status": matrix.STATUS_MISSING},
			{"id": "E3", "name": "Three", "status": matrix.STATUS_MISSING},
			{"id": "E4", "name": "Four", "status": matrix.STATUS_POOL},
		]
		with patch.object(matrix, "_build_rows", return_value=rows):
			unplaced = gen._unplaced({"E1": "Camp X has no transport stop"}, {"E3": {}})

		self.assertEqual(
			[(r["employee"], r["reason"]) for r in unplaced],
			[("E1", "Camp X has no transport stop"), ("E2", "Demand produced but no card; see Error Log")],
		)

	def test_the_matrix_says_why(self):
		self.assertEqual(matrix._missing_reason({}, None, "A", "B", "Shift A is not Active"), "Shift A is not Active")
		self.assertIsNone(matrix._missing_reason({}, None, "A", "B"))


class TestTheRunKeepsWhatItMade(ReconcileCase):
	def _run(self, demands, cards, **patches):
		with patch.object(gen, "get_grouped_employees_by_accommodation", return_value={"x": 1}), \
				patch.object(gen, "build_demand_descriptors", return_value=demands), \
				patch.object(gen, "reliever_context", return_value={}), \
				patch.object(gen, "_live_cards", side_effect=lambda: self._cards(*cards) if cards else {}), \
				patch.object(gen.frappe.db, "commit"):
			with patch.multiple(gen, **patches) if patches else nullcontext():
				return gen.generate_transportation_shipments()

	def test_a_joiner_with_no_seat_ends_on_a_live_overflow_card(self):
		demand = _demand("OV", "E1", "E2")
		key, _pair = gen._generation_key(demand, "Outward")
		parent = self._card(key, ["E1"])

		# The real prune. The site's own pool keys are added so it only judges this run's cards.
		real_prune = gen._prune_stale
		pool = set(frappe.get_all(
			"Transportation Shipment",
			filters={"source_doctype": "Operations Shift", "status": "Unassigned"},
			pluck="generation_key",
		)) - {None}

		def prune(current_keys, keep=None):
			return real_prune(set(current_keys) | pool, keep=keep)

		with patch.object(gen._SeatCheck, "room", return_value=0):
			summary = self._run([demand], [parent], _prune_stale=prune)

		overflow = frappe.get_all(
			"Transportation Shipment", filters={"generation_key": f"{key}#2"}, fields=["name", "status"]
		)
		self.assertEqual(summary["overflowed"], 1)
		self.assertEqual(len(overflow), 1, "the run deleted the overflow card it made")
		self.assertEqual(overflow[0].status, "Unassigned")
		self.assertEqual(self._riders(overflow[0].name), ["E2"])
		self.assertEqual(self._riders(parent), ["E1"])

	def test_a_failing_demand_lands_in_failed_and_the_rest_complete(self):
		good, bad = _demand("GOOD", "E1"), _demand("BAD", "E2")
		real_write = gen._write_shipment

		def write(doc, demand, *args, **kwargs):
			if demand is bad:
				raise RuntimeError("Stop is broken")
			return real_write(doc, demand, *args, **kwargs)

		summary = self._run([good, bad], [], _write_shipment=write, _prune_stale=lambda *a, **k: 0)

		self.assertEqual(summary["created"], 2)
		self.assertEqual(summary["generated"], 2)
		self.assertEqual([r["employee"] for r in summary["failed"]], ["E2"])
		self.assertIn("Stop is broken", summary["failed"][0]["reason"])

	def test_an_orphan_card_drops_lapsed_and_on_leave_riders_only(self):
		stale = self._card(_key("LV"), ["E1", "E2", "E3"])

		with patch.object(gen, "_lapsed", return_value={"E1"}), \
				patch.object(gen, "absent_employees", return_value={"E2": (today(), today())}):
			gen._settle_orphans(self._cards(stale), set(), {}, self._summary())

		self.assertEqual(self._riders(stale), ["E3"])
		self.assertIn("E3", self.flags[stale])


class TestTheAlert(FrappeTestCase):
	ROW = {"employee": "E1", "employee_name": "Rider E1", "reason": "Shift S1 is not Active"}

	def _run(self, unplaced, user="Administrator", boom=False):
		demand = patch.object(gen, "get_grouped_employees_by_accommodation", return_value={})
		if boom:
			demand = patch.object(gen, "get_grouped_employees_by_accommodation", side_effect=RuntimeError("boom"))
		self.addCleanup(setattr, frappe.session, "user", frappe.session.user)
		frappe.session.user = user
		with demand, \
				patch.object(gen, "build_demand_descriptors", return_value=[]), \
				patch.object(gen, "_expire_single_day_rows", return_value=0), \
				patch.object(gen, "_unplaced", return_value=unplaced), \
				patch.object(gen.frappe, "only_for"), \
				patch.object(gen.frappe.db, "get_single_value", return_value="alerts@example.com"), \
				patch.object(gen.frappe, "sendmail") as sendmail, \
				patch.object(gen.frappe, "log_error") as log_error, \
				patch.object(gen.frappe.db, "rollback"), \
				patch.object(gen.frappe.db, "commit"):
			try:
				summary = gen.generate_transportation_shipments()
			except RuntimeError:
				summary = None
		return summary, sendmail, log_error

	def test_a_scheduled_run_with_skips_emails_once_and_logs_once(self):
		summary, sendmail, log_error = self._run([self.ROW])

		self.assertEqual(summary["skipped"], [self.ROW])
		sendmail.assert_called_once()
		self.assertEqual(sendmail.call_args.kwargs["recipients"], ["alerts@example.com"])
		self.assertIn("Shift S1 is not Active", sendmail.call_args.kwargs["message"])
		log_error.assert_called_once()
		self.assertIn("1 skipped, 0 failed", log_error.call_args.kwargs["title"])

	def test_a_clean_run_sends_nothing(self):
		_summary, sendmail, log_error = self._run([])

		sendmail.assert_not_called()
		log_error.assert_not_called()

	def test_a_button_run_sends_no_email(self):
		summary, sendmail, _log_error = self._run([self.ROW], user="dispatcher@example.com")

		self.assertEqual(summary["skipped"], [self.ROW])
		sendmail.assert_not_called()

	def test_a_run_that_raises_is_logged_emailed_and_re_raised(self):
		summary, sendmail, log_error = self._run([], boom=True)

		self.assertIsNone(summary)
		log_error.assert_called_once()
		sendmail.assert_called_once()

	def test_a_button_run_that_raises_is_logged_not_emailed(self):
		_summary, sendmail, log_error = self._run([], user="dispatcher@example.com", boom=True)

		log_error.assert_called_once()
		sendmail.assert_not_called()

	def test_the_recipient_field_and_its_patch_ship(self):
		meta = frappe.get_meta("Transportation Settings")
		self.assertEqual(meta.get_field("shipment_alert_user").options, "User")
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.set_transportation_shipment_alert_user", patches)
