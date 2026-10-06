# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Generate Shipments keeps each rider on one live card per direction.

A card is found again each night by its generation_key - camp, shift or OLM window, stop,
arrangement and direction. Production showed three ways the same people ended up on two
buses:

- the merge-era re-key keyed merged cards `...|Mixed`, a key no run produces, so the next
  run built each of them a twin;
- a rider whose stop, shift, camp, window or arrangement changed got a new card while the
  placed one kept them;
- a split overflow's `#n` key is never produced, so the nightly refresh put every rider
  back on the parent (two parents held 112 riders each).

These tests seed their own cards and drive the reconcile steps on those cards only. The
generator commits, and running it against a site's real pool would reconcile every card
on it.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment import shipment_generator as gen

PREFIX = "OPS|RECONCILE-TEST"
DEMAND = {
	"accommodation": None,
	"operations_shift": None,
	"operations_site": None,
	"stop_location": None,
	"routing": "OLM",
	"start_time": None,
	"end_time": None,
}


def _emp(emp_id):
	return {"id": emp_id, "name": f"Rider {emp_id}", "mobile": "", "site": None}


def _roster(*ids):
	return [_emp(emp_id) for emp_id in ids]


def _key(tail, direction="Outward"):
	return f"{PREFIX}|{tail}|{direction}"


class ReconcileCase(FrappeTestCase):
	def setUp(self):
		self.seeded = []
		self.flags = {}
		flag = patch.object(gen, "_set_replan_flag", side_effect=self._record_flag)
		flag.start()
		self.addCleanup(flag.stop)

	def tearDown(self):
		for name in self.seeded:
			frappe.delete_doc("Transportation Shipment", name, force=True, ignore_permissions=True)
		frappe.db.delete("Transportation Shipment", {"generation_key": ["like", f"{PREFIX}%"]})

	def _record_flag(self, card, reason):
		self.flags[card.name] = reason

	def _card(self, key, riders, status="Assigned", direction="Outward", pre=None,
			  overflow_of=None):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = status
		doc.source_doctype = "Operations Shift"
		doc.trip_direction = direction
		doc.pre_merge_trip_direction = pre
		doc.generation_key = key
		doc.pair_group = key.rsplit("|", 1)[0]
		if overflow_of:
			doc.is_split_overflow = 1
			doc.split_parent = overflow_of
			doc.split_root = frappe.db.get_value(
				"Transportation Shipment", overflow_of, "split_root"
			) or overflow_of
		for emp_id in riders:
			doc.append("transportation_shipment_employee", {
				"employee_id": emp_id, "employee_name": f"Rider {emp_id}",
			})
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		self.seeded.append(doc.name)
		return doc.name

	def _cards(self, *names):
		"""What _live_cards returns, for the seeded cards only."""
		cards = {}
		for row in frappe.get_all(
			"Transportation Shipment",
			filters={"name": ["in", list(names)]},
			fields=["name", "status", "generation_key", "trip_direction",
					"pre_merge_trip_direction", "is_split_overflow", "split_root", "creation"],
			order_by="creation asc",
		):
			row.riders = self._riders(row.name)
			row.needs_replan = 0
			cards[row.name] = row
		return cards

	def _riders(self, name):
		return frappe.get_all(
			"Transportation Shipment Employee",
			filters={"parent": name, "parenttype": "Transportation Shipment"},
			pluck="employee_id", order_by="idx asc",
		)

	def _summary(self):
		return {"created": 0, "updated": 0, "refreshed": 0, "deleted": 0, "errors": 0,
				"repaired": 0, "overflowed": 0, "flagged": 0, "pruned": False}

	def _distribute(self, cards, gen_key, roster, room=None, direction="Outward"):
		seats = gen._SeatCheck()
		seats.room = room or (lambda card, staying, wanted: wanted)
		family = gen._families(cards, {gen_key})[gen_key]
		return gen._distribute(
			family, DEMAND, direction, roster, gen_key, gen_key.rsplit("|", 1)[0], {}, seats,
			self._summary(),
		)


class TestTheMixedKeyIsGivenBack(ReconcileCase):
	def test_a_merged_card_gets_its_own_direction_back(self):
		stale = self._card(_key("A", "Mixed"), ["E1"], direction="Mixed", pre="Outward")

		repaired = gen._repair_mixed_keys(self._cards(stale), {_key("A")})

		self.assertEqual(repaired, 1)
		self.assertEqual(frappe.db.get_value("Transportation Shipment", stale, "generation_key"), _key("A"))

	def test_two_legs_sharing_one_mixed_key_are_told_apart(self):
		# TS-0593/TS-0594 on production: an Outward and a Return merged into one run.
		out = self._card(_key("B", "Mixed"), ["E1"], direction="Mixed", pre="Outward")
		ret = self._card(_key("B", "Mixed"), ["E1"], direction="Mixed", pre="Return")

		gen._repair_mixed_keys(self._cards(out, ret), {_key("B"), _key("B", "Return")})

		self.assertEqual(frappe.db.get_value("Transportation Shipment", out, "generation_key"), _key("B"))
		self.assertEqual(frappe.db.get_value("Transportation Shipment", ret, "generation_key"),
						 _key("B", "Return"))

	def test_a_card_whose_twin_already_holds_the_key_is_left_alone(self):
		# Two cards under one key would make the lookup arbitrary and the prune delete one.
		stale = self._card(_key("C", "Mixed"), ["E1"], direction="Mixed", pre="Outward")
		twin = self._card(_key("C"), ["E1", "E2"])

		repaired = gen._repair_mixed_keys(self._cards(stale, twin), {_key("C")})

		self.assertEqual(repaired, 0)
		self.assertEqual(frappe.db.get_value("Transportation Shipment", stale, "generation_key"),
						 _key("C", "Mixed"))

	def test_a_key_today_does_not_produce_is_not_invented(self):
		stale = self._card(_key("D", "Mixed"), ["E1"], direction="Mixed", pre="Outward")

		self.assertEqual(gen._repair_mixed_keys(self._cards(stale), {_key("OTHER")}), 0)


class TestASplitIsOneFamily(ReconcileCase):
	def test_the_parent_gives_back_what_its_overflow_carries(self):
		# The 112-rider parents: the refresh had re-absorbed every overflow rider.
		parent = self._card(_key("S"), ["E1", "E2", "E3", "E4"])
		overflow = self._card(_key("S") + "#2", ["E3", "E4"], overflow_of=parent)

		self._distribute(self._cards(parent, overflow), _key("S"), _roster("E1", "E2", "E3", "E4"))

		self.assertEqual(self._riders(parent), ["E1", "E2"])
		self.assertEqual(self._riders(overflow), ["E3", "E4"])

	def test_an_unplaced_overflow_is_not_pruned(self):
		parent = self._card(_key("P"), ["E1"])
		overflow = self._card(_key("P") + "#2", ["E2"], status="Unassigned", overflow_of=parent)
		cards = self._cards(parent, overflow)
		produced = {card.name for family in gen._families(cards, {_key("P")}).values() for card in family}

		# The real prune, on a pool of just this card.
		with patch.object(gen.frappe, "get_all",
						  return_value=[frappe._dict(name=overflow, generation_key=_key("P") + "#2")]):
			deleted = gen._prune_stale({_key("P")}, keep=produced)

		self.assertEqual(deleted, 0)
		self.assertTrue(frappe.db.exists("Transportation Shipment", overflow))

	def test_a_leaver_comes_off_whichever_card_had_them(self):
		parent = self._card(_key("L"), ["E1", "E2"])
		overflow = self._card(_key("L") + "#2", ["E3"], overflow_of=parent)

		self._distribute(self._cards(parent, overflow), _key("L"), _roster("E1", "E3"))

		self.assertEqual(self._riders(parent), ["E1"])
		self.assertEqual(self._riders(overflow), ["E3"])

	def test_an_unplaced_overflow_nobody_rides_is_removed(self):
		parent = self._card(_key("U"), ["E1"])
		overflow = self._card(_key("U") + "#2", ["E2"], status="Unassigned", overflow_of=parent)

		self._distribute(self._cards(parent, overflow), _key("U"), _roster("E1"))

		self.assertFalse(frappe.db.exists("Transportation Shipment", overflow))

	def test_a_placed_card_left_empty_is_flagged(self):
		parent = self._card(_key("F"), ["E1"])
		overflow = self._card(_key("F") + "#2", ["E1"], overflow_of=parent)

		self._distribute(self._cards(parent, overflow), _key("F"), _roster("E1"))

		self.assertEqual(self._riders(parent), [])
		self.assertTrue(self.flags[parent])
		self.assertIsNone(self.flags[overflow])


class TestAJoinerNeverOverloadsABus(ReconcileCase):
	def test_with_no_seat_left_the_joiner_goes_to_a_new_pool_card(self):
		parent = self._card(_key("J"), ["E1"], direction="Mixed", pre="Outward")

		carried = self._distribute(self._cards(parent), _key("J"), _roster("E1", "E2"),
								   room=lambda card, staying, wanted: 0)

		self.assertEqual(self._riders(parent), ["E1"])
		overflow = carried["E2"]
		self.assertNotEqual(overflow, parent)
		new = frappe.get_doc("Transportation Shipment", overflow)
		self.seeded.append(overflow)
		self.assertEqual(new.status, "Unassigned")
		self.assertEqual(new.split_root, parent)
		self.assertTrue(new.generation_key.startswith(_key("J") + "#"))
		# The riders' own way, not the merged trip's Mixed.
		self.assertEqual(new.trip_direction, "Outward")
		self.assertFalse(new.trip_group)

	def test_the_bus_takes_what_fits_and_the_pool_the_rest(self):
		parent = self._card(_key("K"), ["E1"])

		carried = self._distribute(self._cards(parent), _key("K"), _roster("E1", "E2", "E3"),
								   room=lambda card, staying, wanted: 1)
		self.seeded.extend({carried["E3"]} - set(self.seeded))

		self.assertEqual(self._riders(parent), ["E1", "E2"])
		self.assertEqual(self._riders(carried["E3"]), ["E3"])

	def test_an_unplaced_overflow_takes_joiners_before_a_new_card_is_made(self):
		parent = self._card(_key("Q"), ["E1"])
		overflow = self._card(_key("Q") + "#2", ["E2"], status="Unassigned", overflow_of=parent)

		carried = self._distribute(self._cards(parent, overflow), _key("Q"),
								   _roster("E1", "E2", "E3"), room=lambda card, staying, wanted: 0)

		self.assertEqual(carried["E3"], overflow)
		self.assertEqual(self._riders(overflow), ["E2", "E3"])


class TestAPlacedCardTheRosterNoLongerProduces(ReconcileCase):
	def test_a_rider_carried_elsewhere_comes_off_and_the_card_is_flagged(self):
		# TS-0691 and TS-1028: the stale card and its regenerated twin on one trip.
		stale = self._card(_key("O", "Mixed"), ["E1", "E2"], direction="Mixed", pre="Outward")
		summary = self._summary()

		flagged = gen._settle_orphans(
			self._cards(stale), produced=set(), owner={("E1", "Outward"): "TS-TWIN"}, summary=summary,
		)

		self.assertEqual(flagged, 1)
		self.assertEqual(self._riders(stale), ["E2"])
		self.assertIn("E1 → TS-TWIN", self.flags[stale])
		self.assertIn("E2", self.flags[stale])

	def test_a_rider_with_no_card_today_is_kept(self):
		# An empty demand for someone can be a data gap; a bus is not emptied on one.
		stale = self._card(_key("G"), ["E1"])

		gen._settle_orphans(self._cards(stale), set(), {}, self._summary())

		self.assertEqual(self._riders(stale), ["E1"])
		self.assertTrue(self.flags[stale])

	def test_the_other_direction_is_not_a_duplicate(self):
		# An Outward card and a Return card with the same people are one round trip.
		stale = self._card(_key("R"), ["E1"])

		gen._settle_orphans(self._cards(stale), set(), {("E1", "Return"): "TS-RET"}, self._summary())

		self.assertEqual(self._riders(stale), ["E1"])

	def test_a_produced_or_unplaced_card_is_not_touched(self):
		live = self._card(_key("T"), ["E1"])
		pool = self._card(_key("V"), ["E2"], status="Unassigned")

		flagged = gen._settle_orphans(
			self._cards(live, pool), {live}, {("E1", "Outward"): "X", ("E2", "Outward"): "Y"},
			self._summary(),
		)

		self.assertEqual(flagged, 0)
		self.assertEqual(self._riders(live), ["E1"])
		self.assertEqual(self._riders(pool), ["E2"])


class TestTheSeatCheck(FrappeTestCase):
	def test_it_finds_the_most_that_fit_and_puts_the_count_back(self):
		card = frappe.new_doc("Transportation Shipment")
		card.flags.ignore_mandatory = True
		card.insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, "Transportation Shipment", card.name, force=True)
		before = frappe.db.get_value("Transportation Shipment", card.name, "headcount")

		seats = gen._SeatCheck()
		seen = []
		with patch.object(gen.frappe, "get_all", return_value=[frappe._dict(parent="RP", vehicle="V")]), \
				patch.object(seats, "_fits", side_effect=lambda plan, vehicle: seen.append(
					frappe.db.get_value("Transportation Shipment", card.name, "headcount")) or seen[-1] <= 6):
			room = seats.room(card.name, staying=3, wanted=10)

		self.assertEqual(room, 3)
		self.assertIn(6, seen)
		self.assertEqual(frappe.db.get_value("Transportation Shipment", card.name, "headcount"), before)

	def test_a_bus_already_over_takes_nobody(self):
		seats = gen._SeatCheck()
		with patch.object(gen.frappe, "get_all", return_value=[frappe._dict(parent="RP", vehicle="V")]), \
				patch.object(gen.frappe.db, "get_value", return_value=5), \
				patch.object(gen.frappe.db, "set_value"), \
				patch.object(seats, "_fits", return_value=False):
			self.assertEqual(seats.room("TS-X", staying=5, wanted=3), 0)

	def test_a_card_on_no_plan_has_no_bus_to_overload(self):
		with patch.object(gen.frappe, "get_all", return_value=[]):
			self.assertEqual(gen._SeatCheck().room("TS-X", staying=5, wanted=3), 3)


class TestTheRun(ReconcileCase):
	"""The steps wired together, on a pool of just the seeded cards."""

	def _run(self, demands, cards):
		with patch.object(gen, "get_grouped_employees_by_accommodation", return_value={"x": 1}), \
				patch.object(gen, "build_demand_descriptors", return_value=demands), \
				patch.object(gen, "reliever_context", return_value={}), \
				patch.object(gen, "_live_cards", return_value=cards) as live, \
				patch.object(gen, "_prune_stale", return_value=0) as prune, \
				patch.object(gen.frappe.db, "commit"):
			summary = gen.generate_transportation_shipments()
		return summary, prune, live

	def test_the_stale_twin_gives_up_its_riders_and_is_flagged(self):
		demand = dict(DEMAND, group_token="RECONCILE-TEST|W", employees=_roster("E1", "E2", "E3"))
		key, _pair = gen._generation_key(demand, "Outward")
		self.assertTrue(key.startswith("OPS|"))
		stale = self._card(key.replace("|Outward", "|Mixed"), ["E1", "E2"], direction="Mixed", pre="Outward")
		twin = self._card(key, ["E1", "E2", "E3"])
		cards = self._cards(stale, twin)

		summary, prune, _live = self._run([demand], cards)

		self.assertEqual(self._riders(stale), [])
		self.assertEqual(self._riders(twin), ["E1", "E2", "E3"])
		self.assertTrue(self.flags[stale])
		self.assertEqual(summary["flagged"], 1)
		self.assertEqual(summary["repaired"], 0)
		self.assertIn(twin, prune.call_args.kwargs["keep"])

	def test_a_run_with_no_demand_touches_no_card(self):
		stale = self._card(_key("Z"), ["E1"])

		summary, prune, live = self._run([], self._cards(stale))

		self.assertFalse(summary["pruned"])
		prune.assert_not_called()
		live.assert_not_called()
		self.assertEqual(self._riders(stale), ["E1"])
