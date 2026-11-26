# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Generate Shipments says what it changed on each card, and why.

Riders are compared by employee_id: the roster rewrite re-creates every child row, so a
Version diff would report every rider as removed and added again. An Unassigned card
whose demand did not change is no longer saved, and no longer counted as updated.
"""

from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment import shipment_generator as gen
from one_fm.one_fm.page.transportation_schedule import traceability_matrix as matrix
from one_fm.one_fm.page.transportation_schedule import transportation_schedule as ts
from one_fm.tests.test_shipment_rider_reconcile import DEMAND, ReconcileCase, _roster


def _sig(emp, name=None, covers=None):
	return (emp, name or f"Rider {emp}", covers, covers and f"Name {covers}", None, None, None)


def _crew(*sigs):
	return {sig[0]: sig for sig in sigs}


class TestCrewDiff(FrappeTestCase):
	def test_same_riders_in_a_new_order_is_no_change(self):
		self.assertEqual(gen._crew_diff(_crew(_sig("E1"), _sig("E2")), _crew(_sig("E2"), _sig("E1"))), [])

	def test_a_joiner_a_leaver_and_a_reliever_swap_each_give_one_change(self):
		changes = gen._crew_diff(
			_crew(_sig("E1"), _sig("E2"), _sig("R1", covers="A1")),
			_crew(_sig("E1"), _sig("E3"), _sig("R1", covers="A2")),
		)
		by_emp = {c["employee"]: c for c in changes}

		self.assertEqual(len(changes), 3)
		self.assertEqual((by_emp["E3"]["field"], by_emp["E3"]["old"], by_emp["E3"]["new"]), ("Rider", "", "Rider E3"))
		self.assertEqual((by_emp["E2"]["field"], by_emp["E2"]["old"], by_emp["E2"]["new"]), ("Rider", "Rider E2", ""))
		self.assertEqual(by_emp["R1"]["field"], "Covering")
		self.assertEqual((by_emp["R1"]["old"], by_emp["R1"]["new"]), ("Name A1", "Name A2"))


class TestHeaderDiff(FrappeTestCase):
	def test_a_timedelta_and_the_same_time_as_text_are_equal(self):
		doc = frappe._dict(start_time="07:00:00", end_time="15:00:00")
		self.assertEqual(gen._header_diff({"start_time": timedelta(hours=7), "end_time": timedelta(hours=15)}, doc), [])

	def test_a_changed_end_time_gives_old_and_new(self):
		doc = frappe._dict(start_time="07:00:00", end_time="16:00:00")
		changes = gen._header_diff({"start_time": timedelta(hours=7), "end_time": timedelta(hours=15)}, doc)

		self.assertEqual([(c["field"], c["old"], c["new"]) for c in changes], [("End Time", "15:00:00", "16:00:00")])


def _card(acc="ACC-1", shift="S1", overflow=0, aggregated=None):
	return {"accommodation": acc, "operations_shift": shift, "aggregated_shifts": aggregated,
			"is_split_overflow": overflow}


ADDED = {"employee": "E1", "field": "Rider", "old": "", "new": "Rider E1"}
REMOVED = {"employee": "E1", "field": "Rider", "old": "Rider E1", "new": ""}


class TestRiderReason(FrappeTestCase):
	def reason(self, change, old, new, shift="S1", skip=None):
		return gen._rider_reason(change, old, new, {"E1": shift}, skip)

	def test_a_new_rider_was_added_to_the_roster(self):
		self.assertEqual(self.reason(ADDED, None, _card()), "Employee added to roster")

	def test_another_camp_is_an_accommodation_change(self):
		self.assertEqual(self.reason(ADDED, _card("ACC-2"), _card()), "Accommodation changed")
		self.assertEqual(self.reason(REMOVED, _card(), _card("ACC-2")), "Accommodation changed")

	def test_another_shift_is_a_shift_change(self):
		self.assertEqual(self.reason(ADDED, _card(shift="S2"), _card(), shift="S1"), "Shift changed")
		self.assertEqual(self.reason(REMOVED, _card(shift="S2"), _card(), shift="S1"), "Shift changed")

	def test_an_aggregated_card_lists_its_shifts(self):
		old = _card(shift=None, aggregated="S0, S1")
		self.assertEqual(self.reason(ADDED, old, _card()), "Shift times, stop or route changed")

	def test_same_camp_and_shift_onto_an_overflow_card_is_a_full_bus(self):
		self.assertEqual(self.reason(ADDED, _card(), _card(overflow=1)), "Moved to overflow card (bus full)")

	def test_same_camp_and_shift_otherwise_is_times_stop_or_route(self):
		self.assertEqual(self.reason(ADDED, _card(), _card()), "Shift times, stop or route changed")

	def test_a_day_off_or_leave_is_stated_as_is(self):
		self.assertEqual(self.reason(REMOVED, _card(), None, skip="Day off applied (Day Off)"), "Day off applied (Day Off)")
		self.assertEqual(self.reason(REMOVED, _card(), None, skip="On approved leave"), "On approved leave")

	def test_a_removed_rider_carries_the_skip_reason(self):
		self.assertEqual(
			self.reason(REMOVED, _card(), None, skip="No roster entry"), "Employee removed from roster: No roster entry"
		)
		self.assertEqual(self.reason(REMOVED, _card(), None), "Employee removed from roster")

	def test_a_new_cover_is_a_reliever_change(self):
		self.assertEqual(self.reason({"employee": "E1", "field": "Covering", "old": "A", "new": "B"}, _card(), _card()),
						 "Reliever changed")


class TestBuilderReasons(FrappeTestCase):
	def test_an_employee_on_approved_leave_is_named(self):
		from one_fm.tests.test_shipment_generation_report import _checkin, _tables

		get_all = _tables(["S1"], {"E1": "S1", "E2": "S1"}, {"ACC-1": "Camp One"}, ["ACC-1"])
		skipped = {}
		with patch.object(ts.frappe, "get_all", side_effect=get_all), \
				patch.object(ts, "apply_to_shift_map", side_effect=lambda m, on_date=None: {}), \
				patch.object(ts, "absent_employees", return_value={"E1": (None, None)}), \
				patch.object(matrix, "_latest_checkins", return_value={"E1": _checkin("E1", "ACC-1")}):
			ts.get_grouped_employees_by_accommodation(skipped=skipped)

		self.assertEqual(skipped, {"E1": "On approved leave", "E2": "Day off applied (covered by a reliever)"})


def _demand(tail, shift, *ids):
	return dict(DEMAND, group_token=f"RECONCILE-TEST|{tail}", operations_shift=shift, employees=_roster(*ids))


class TestTheRunReportsEachCard(ReconcileCase):
	def _cards(self, *names):
		cards = super()._cards(*names)
		for row in frappe.get_all("Transportation Shipment", filters={"name": ["in", list(names)]},
								  fields=["name", "accommodation", "operations_shift", "aggregated_shifts"]):
			cards[row.name].update(row)
		return cards

	def _run(self, demands, cards, nested=None, prune=None):
		with patch.object(gen, "get_grouped_employees_by_accommodation", return_value=nested or {"x": 1}), \
				patch.object(gen, "build_demand_descriptors", return_value=demands), \
				patch.object(gen, "reliever_context", return_value={}), \
				patch.object(gen, "_live_cards", side_effect=lambda: self._cards(*cards)), \
				patch.object(gen, "_prune_stale", side_effect=prune or (lambda *a, **k: 0)), \
				patch.object(gen.frappe.db, "commit"):
			summary = gen.generate_transportation_shipments()
		names = [e["card"] for e in summary["cards"]]
		self.assertEqual(len(names), len(set(names)), "a card is listed twice")
		return summary, {e["card"]: e for e in summary["cards"]}

	def _shifts(self):
		shifts = frappe.get_all("Operations Shift", pluck="name", limit=2, order_by="name")
		if len(shifts) < 2:
			self.skipTest("needs two Operations Shifts")
		return shifts

	def test_an_unchanged_pool_card_is_not_saved_or_counted(self):
		demand = _demand("SAME", None, "E1", "E2")
		key, _pair = gen._generation_key(demand, "Outward")
		card = self._card(key, ["E1"], status="Unassigned")
		self._run([demand], [card])  # brings the card up to the demand
		modified = frappe.db.get_value("Transportation Shipment", card, "modified")

		summary, by_card = self._run([demand], [card])

		self.assertEqual(by_card[card]["action"], "unchanged")
		self.assertEqual(summary["counts"]["updated"], 0)
		self.assertEqual(summary["updated"], 0)
		self.assertEqual(frappe.db.get_value("Transportation Shipment", card, "modified"), modified)

	def test_a_rider_moving_shift_is_removed_and_added_as_a_shift_change(self):
		shift_a, shift_b = self._shifts()
		demand_a, demand_b = _demand("SA", shift_a, "E2"), _demand("SB", shift_b, "E3", "E1")
		card_a = self._card(gen._generation_key(demand_a, "Outward")[0], ["E1", "E2"])
		card_b = self._card(gen._generation_key(demand_b, "Outward")[0], ["E3"])
		frappe.db.set_value("Transportation Shipment", card_a, "operations_shift", shift_a)
		frappe.db.set_value("Transportation Shipment", card_b, "operations_shift", shift_b)
		nested = {"ACC": {"lookup_id": "ACC", "shifts": {shift_a: ["E2"], shift_b: ["E3", "E1"]}}}

		_summary, by_card = self._run([demand_a, demand_b], [card_a, card_b], nested=nested)

		removed = by_card[card_a]["changes"]
		added = by_card[card_b]["changes"]
		self.assertEqual([(c["employee"], c["old"], c["new"], c["reason"]) for c in removed],
						 [("E1", "Rider E1", "", "Shift changed")])
		self.assertEqual([(c["employee"], c["old"], c["new"], c["reason"], c["shift"]) for c in added],
						 [("E1", "", "Rider E1", "Shift changed", shift_b)])

	def test_a_placed_card_gaining_a_rider_is_updated(self):
		demand = _demand("GAIN", None, "E1", "E2")
		card = self._card(gen._generation_key(demand, "Outward")[0], ["E1"])

		summary, by_card = self._run([demand], [card])

		self.assertEqual(by_card[card]["action"], "updated")
		self.assertEqual([(c["employee"], c["reason"]) for c in by_card[card]["changes"]],
						 [("E2", "Employee added to roster")])
		self.assertEqual(summary["counts"]["updated"], 1)
		self.assertEqual(summary["updated"], 0, "the old key counts pool cards only")

	def test_a_pruned_card_is_cancelled(self):
		demand = _demand("KEEP", None, "E1")
		live = self._card(gen._generation_key(demand, "Outward")[0], ["E1"])
		stale = self._card(gen._generation_key(_demand("GONE", None), "Outward")[0], ["E9"], status="Unassigned")
		# The real prune, judging only this test's stale card.
		real_prune = gen._prune_stale
		pool = set(frappe.get_all(
			"Transportation Shipment",
			filters={"source_doctype": "Operations Shift", "status": "Unassigned", "name": ["!=", stale]},
			pluck="generation_key",
		)) - {None}

		def prune(current_keys, **kwargs):
			return real_prune(set(current_keys) | pool, **kwargs)

		summary, by_card = self._run([demand], [live, stale], prune=prune)

		self.assertEqual(by_card[stale]["action"], "cancelled")
		self.assertEqual(summary["deleted"], 1)
		self.assertEqual(summary["counts"]["cancelled"], 1)
		self.assertEqual(by_card[live]["action"], "unchanged")
		self.assertFalse(frappe.db.exists("Transportation Shipment", stale))
		self.seeded.remove(stale)

	def test_a_new_card_lists_every_rider_as_added(self):
		demand = _demand("NEW", None, "E1", "E2")

		summary, by_card = self._run([demand], [])

		created = [e for e in by_card.values() if e["action"] == "created"]
		self.seeded.extend(e["card"] for e in created)
		self.assertEqual(summary["counts"]["created"], 2)  # Outward and Return
		self.assertEqual(sorted(c["employee"] for c in created[0]["changes"]), ["E1", "E2"])
		self.assertEqual({c["reason"] for c in created[0]["changes"]}, {"Employee added to roster"})

	def test_an_orphan_that_loses_a_rider_is_updated_with_the_note(self):
		stale = self._card("OPS|RECONCILE-TEST|ORPHAN|Outward", ["E1", "E2"])
		summary = self._summary()

		with patch.object(gen, "_lapsed", return_value={"E1"}):
			gen._settle_orphans(self._cards(stale), set(), {}, summary)

		entry = summary["cards"][0]
		self.assertEqual(entry["action"], "updated")
		self.assertEqual([c["employee"] for c in entry["changes"]], ["E1"])
		self.assertTrue(entry["note"])
