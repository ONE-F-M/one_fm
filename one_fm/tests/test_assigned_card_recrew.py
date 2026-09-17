# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002591 AC5: Generate Shipments brings a PLACED card's crew up to date.

A Transportation Shipment answers two different questions. WHERE the bus goes is the
Route Plan's once the card is on a lane; WHO rides it belongs to the roster and changes
every day - a reliever steps in, somebody is transferred.

The generator used to answer neither for a placed card. ``Assigned -> leave untouched``
meant a crew change after placement never reached the driver's manifest, and the only way
to pick it up was to unassign the card and re-plan the run.

The refresh moves the roster and the headcount and NOTHING else. generation_key and
pair_group are what the Route Plan Assignment row points at; rewriting them would orphan
the very placement this is meant to preserve. These tests pin both halves: the crew does
change, and the identity does not.
"""

import inspect

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment import shipment_generator
from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
	_refresh_assigned_roster,
)


def _emp(emp_id, name, mobile="000"):
	return {"id": emp_id, "name": name, "mobile": mobile, "site": None}


# The link fields are left blank on purpose: what is under test is the roster swap,
# and pinning it to real Accommodation/Site masters would make these tests depend on
# whichever ones happen to exist on the bench.
DEMAND = {
	"accommodation": None,
	"operations_shift": None,
	"operations_site": None,
	"stop_location": None,
	"routing": "Direct",
	"start_time": None,
	"end_time": None,
}


class TestRecrewingAPlacedCard(FrappeTestCase):
	def _card(self, roster, status="Assigned"):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = status
		doc.trip_direction = "Outward"
		doc.generation_key = frappe.generate_hash("GEN", 10)
		doc.pair_group = frappe.generate_hash("PAIR", 10)
		doc.headcount = len(roster)
		for emp in roster:
			doc.append("transportation_shipment_employee", {
				"employee_id": emp["id"], "employee_name": emp["name"],
			})
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		return doc

	def test_a_reliever_stepping_in_reaches_the_placed_card(self):
		card = self._card([_emp("EMP-A", "Original Person")])

		changed = _refresh_assigned_roster(
			card.name, DEMAND, [_emp("EMP-B", "Reliever Person")]
		)

		self.assertTrue(changed)
		card.reload()
		self.assertEqual(
			[(r.employee_id, r.employee_name) for r in card.transportation_shipment_employee],
			[("EMP-B", "Reliever Person")],
		)

	def test_the_headcount_follows_the_crew(self):
		card = self._card([_emp("EMP-A", "A")])

		_refresh_assigned_roster(card.name, DEMAND, [_emp("EMP-A", "A"), _emp("EMP-C", "C")])

		card.reload()
		self.assertEqual(int(card.headcount), 2)

	def test_the_placement_keys_are_never_rewritten(self):
		# generation_key/pair_group are what the Route Plan Assignment row points at.
		card = self._card([_emp("EMP-A", "A")])
		before = (card.generation_key, card.pair_group, card.status)

		_refresh_assigned_roster(card.name, DEMAND, [_emp("EMP-B", "B")])

		card.reload()
		self.assertEqual((card.generation_key, card.pair_group, card.status), before)

	def test_an_unchanged_crew_is_not_written_at_all(self):
		# Otherwise every run of the daily job would bump `modified` on every placed
		# card, and the canvas would fight it (see WI-002538).
		card = self._card([_emp("EMP-A", "A")])
		modified_before = frappe.db.get_value("Transportation Shipment", card.name, "modified")

		changed = _refresh_assigned_roster(card.name, DEMAND, [_emp("EMP-A", "A")])

		self.assertFalse(changed)
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", card.name, "modified"),
			modified_before,
		)

	def test_order_matters_so_a_swap_is_seen(self):
		# Two people exchanged between cards is a real roster change even though the
		# count is identical.
		card = self._card([_emp("EMP-A", "A"), _emp("EMP-B", "B")])

		self.assertTrue(_refresh_assigned_roster(
			card.name, DEMAND, [_emp("EMP-B", "B"), _emp("EMP-A", "A")]))


class TestTheGeneratorWiring(FrappeTestCase):
	"""The button and the nightly job are one function, and now they re-crew."""

	def test_one_entry_point_serves_the_button_and_the_scheduler(self):
		# AC5 asks for an on-demand fallback for the nightly job. It already IS the
		# nightly job - the canvas button calls the same whitelisted function.
		source = inspect.getsource(shipment_generator.generate_transportation_shipments)
		self.assertIn("Entry point for both the daily scheduler and the canvas", source)

		hooks = frappe.read_file(frappe.get_app_path("one_fm", "hooks.py"))
		self.assertIn(
			"one_fm.one_fm.doctype.transportation_shipment.shipment_generator"
			".generate_transportation_shipments",
			hooks,
		)

	def test_the_assigned_branch_no_longer_skips(self):
		# Matched on the call, not its argument list: the point is that the Assigned
		# branch DOES something now, and pinning the exact args means every later
		# parameter makes this fail without anything having regressed (it already did
		# once, when the reliever context was threaded through for AC2).
		source = inspect.getsource(shipment_generator.generate_transportation_shipments)
		self.assertIn("elif _refresh_assigned_roster(", source)
		self.assertNotIn("# Assigned → leave untouched", source)

	def test_recrewed_runs_are_counted_apart_from_rewritten_ones(self):
		source = inspect.getsource(shipment_generator.generate_transportation_shipments)
		self.assertIn('"refreshed": refreshed', source)

	def test_the_trip_request_generator_was_left_alone(self):
		# It has its own lifecycle and no placed-card refresh; a stray always-zero
		# counter there would be noise.
		other = inspect.getsource(shipment_generator.generate_shipments_from_trip_request)
		self.assertNotIn("refreshed", other)

	def test_both_writers_share_one_roster_shape(self):
		# A second copy of the child-row mapping is how the two drift. Matched on the
		# call rather than its arguments, for the same reason as above.
		self.assertIn("_write_roster(doc, demand, roster",
					  inspect.getsource(shipment_generator._write_shipment))
		self.assertIn("_write_roster(doc, demand, roster",
					  inspect.getsource(shipment_generator._refresh_assigned_roster))
