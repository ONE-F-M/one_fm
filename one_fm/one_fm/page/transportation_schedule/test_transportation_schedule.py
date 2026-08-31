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
	"""A direction mismatch is a flag to fix, not a card to send back to the pool.

	The mismatch fires whenever the browser's copy of the plan disagrees with the
	shipment — a tab left open across a merge or a data change, or two people editing
	the board at once. Reverting on it marked a card Unassigned while its block was
	still on the lane, and Generate Shipments deletes Unassigned shift-generated cards
	whose demand has moved on, so a stale tab could get a placed card deleted.
	"""

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
		# The case the revert branch is actually for: the block left the lane, so the
		# card goes back to the pool with its own direction.
		frappe.db.set_value("Transportation Shipment", self.leg, {
			"trip_direction": "Mixed", "pre_merge_trip_direction": "Outward"
		})

		_sync_shipment_statuses([], previously_linked={self.leg})

		reverted = self._read(self.leg)
		self.assertEqual(reverted.status, "Unassigned")
		self.assertEqual(reverted.trip_direction, "Outward")
		self.assertIsNone(reverted.pre_merge_trip_direction)

	def test_a_mismatched_card_is_still_not_newly_assigned(self):
		# The guard the check exists for is untouched: a mismatch never promotes a card
		# to Assigned, it only stops it being demoted.
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

	def test_the_stops_of_a_trip_stay_in_their_own_order(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			manifest_row_order,
		)

		second = self._row("MIX-a", 2, "2026-08-31T05:43:00Z", "2026-08-31T06:15:00Z")
		first = self._row("MIX-a", 1, "2026-08-31T05:27:00Z", "2026-08-31T05:43:00Z")

		ordered = manifest_row_order([second, first])

		self.assertEqual([row.stop_index for row in ordered], [1, 2])

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
