# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Generate Shipments keeps riders added by hand from the Traceability Matrix.

A row with assignment_scope "Permanent" stays on its card on every run; "Today Only"
stays until the first run after its assigned_on date. Each case goes through
generate_transportation_shipments() on a pool of just the seeded cards, the way
test_shipment_rider_reconcile does. Needs the assignment_scope column (bench migrate).
"""

from unittest.mock import patch

import frappe
from frappe.utils import add_days, today

from one_fm.one_fm.doctype.transportation_shipment import shipment_generator as gen
from one_fm.tests.test_shipment_rider_reconcile import DEMAND, ReconcileCase, _key, _roster


def _demand(tail, *ids):
	return dict(DEMAND, group_token=f"RECONCILE-TEST|{tail}", employees=_roster(*ids))


class PinnedCase(ReconcileCase):
	def _pin(self, card, emp_id, scope="Permanent", on=None):
		doc = frappe.get_doc("Transportation Shipment", card)
		doc.append("transportation_shipment_employee", {
			"employee_id": emp_id, "employee_name": f"Rider {emp_id}",
			"assignment_scope": scope, "assigned_on": on or today(),
		})
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.save(ignore_permissions=True)

	def _cards(self, *names):
		cards = super()._cards(*names)
		for card in cards.values():
			card.pins = frappe.get_all(
				"Transportation Shipment Employee",
				filters={"parent": card.name, "assignment_scope": ["is", "set"]},
				pluck="employee_id",
			)
		return cards

	def _run(self, demands, *names, on_date=None):
		with patch.object(gen, "get_grouped_employees_by_accommodation", return_value={"x": 1}), \
				patch.object(gen, "build_demand_descriptors", return_value=demands), \
				patch.object(gen, "reliever_context", return_value={}), \
				patch.object(gen, "_live_cards", side_effect=lambda: self._cards(*names)), \
				patch.object(gen, "_prune_stale", return_value=0), \
				patch.object(gen, "_lapsed", return_value=set()), \
				patch.object(gen, "today", return_value=on_date or today()), \
				patch.object(gen.frappe.db, "commit"):
			return gen.generate_transportation_shipments()

	def _scope(self, card, emp_id):
		return frappe.db.get_value(
			"Transportation Shipment Employee", {"parent": card, "employee_id": emp_id}, "assignment_scope"
		)


class TestPermanentPins(PinnedCase):
	def test_a_permanent_rider_stays_on_a_pool_card_and_off_their_demand_card(self):
		demand = _demand("PA", "E1", "E2")
		key, _pair = gen._generation_key(demand, "Outward")
		own = self._card(key, ["E1", "E2"], status="Unassigned")
		pinned = self._card(_key("PA-OTHER"), [], status="Unassigned")
		self._pin(pinned, "E2")

		for _run in range(2):
			self._run([demand], own, pinned)
			self.assertEqual(self._riders(own), ["E1"])
			self.assertEqual(self._riders(pinned), ["E2"])

	def test_a_permanent_rider_stays_on_a_placed_card_without_churn(self):
		demand = _demand("PB", "E1", "E2")
		key, _pair = gen._generation_key(demand, "Outward")
		placed = self._card(key, ["E1"])
		self._pin(placed, "E3")

		self._run([demand], placed)
		self.assertEqual(self._riders(placed), ["E1", "E2", "E3"])
		modified = frappe.db.get_value("Transportation Shipment", placed, "modified")

		self._run([demand], placed)
		self.assertEqual(self._riders(placed), ["E1", "E2", "E3"])
		self.assertEqual(self._scope(placed, "E3"), "Permanent")
		self.assertEqual(frappe.db.get_value("Transportation Shipment", placed, "modified"), modified)

	def test_the_prune_keeps_a_card_with_a_pin(self):
		pinned = self._card(_key("PC-GONE"), [], status="Unassigned")
		self._pin(pinned, "E1")

		with patch.object(gen.frappe, "get_all",
						  return_value=[frappe._dict(name=pinned, generation_key=_key("PC-GONE"))]), \
				patch.object(gen, "_pins", return_value={("E1", "Outward"): pinned}):
			deleted = gen._prune_stale({_key("PC-OTHER")})

		self.assertEqual(deleted, 0)
		self.assertTrue(frappe.db.exists("Transportation Shipment", pinned))

	def test_settle_orphans_leaves_a_pinned_rider_on_an_orphaned_card(self):
		demand = _demand("PD", "E1", "E2")
		key, _pair = gen._generation_key(demand, "Outward")
		own = self._card(key, ["E1"])
		orphan = self._card(_key("PD-ORPHAN"), ["E1"])
		self._pin(orphan, "E2")

		self._run([demand], own, orphan)

		self.assertEqual(self._riders(own), ["E1"])
		self.assertEqual(self._riders(orphan), ["E2"])
		self.assertTrue(self.flags[orphan])


class TestTodayOnlyPins(PinnedCase):
	def test_a_today_only_rider_stays_today(self):
		demand = _demand("TA", "E1")
		key, _pair = gen._generation_key(demand, "Outward")
		card = self._card(key, ["E1"], status="Unassigned")
		self._pin(card, "E9", scope="Today Only")

		self._run([demand], card)

		self.assertEqual(self._riders(card), ["E1", "E9"])

	def test_a_today_only_rider_is_gone_the_next_day(self):
		demand = _demand("TB", "E1")
		key, _pair = gen._generation_key(demand, "Outward")
		card = self._card(key, ["E1"], status="Unassigned")
		self._pin(card, "E9", scope="Today Only")

		self._run([demand], card, on_date=add_days(today(), 1))

		self.assertEqual(self._riders(card), ["E1"])

	def test_a_today_only_rider_is_gone_on_a_night_with_no_demand(self):
		card = self._card(_key("TC"), ["E1"])
		self._pin(card, "E9", scope="Today Only")

		summary = self._run([], card, on_date=add_days(today(), 1))

		self.assertEqual(self._riders(card), ["E1"])
		self.assertEqual(summary["expired"], 1)
		self.assertFalse(summary["pruned"])

	def test_an_emptied_manual_pool_card_is_deleted(self):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = "Unassigned"
		doc.trip_direction = "Outward"
		doc.is_adhoc_journey = 1
		doc.append("transportation_shipment_employee", {
			"employee_id": "E9", "assignment_scope": "Today Only", "assigned_on": today(),
		})
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)

		with patch.object(gen.frappe.db, "commit"):
			gen._expire_single_day_rows(frappe.utils.getdate(add_days(today(), 1)))

		self.assertFalse(frappe.db.exists("Transportation Shipment", doc.name))


class TestLapsedPermanentPins(PinnedCase):
	def test_a_permanent_pin_for_someone_no_longer_active_is_dropped(self):
		card = self._card(_key("LA"), ["E1"])
		self._pin(card, "E9")

		with patch.object(gen, "_lapsed", return_value={"E9"}):
			removed = gen._expire_single_day_rows(frappe.utils.getdate(today()))

		self.assertEqual(removed, 1)
		self.assertEqual(self._riders(card), ["E1"])
