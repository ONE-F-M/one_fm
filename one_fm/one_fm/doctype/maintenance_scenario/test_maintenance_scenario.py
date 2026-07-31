# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Maintenance Scenario master (WI-001802).

A scenario is what a client picks on the portal; the priority behind it is what the
system derives. The pair is per client, so the same scenario can carry a different
priority for a different customer.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.maintenance_scenario.maintenance_scenario import (
	get_scenario_priority,
)

SCENARIO = "Complete Power Outage"


def _a_client():
	return frappe.db.get_value("Customer", {"disabled": 0}, "name")


def _a_priority():
	return frappe.db.get_value("Issue Priority", {}, "name")


class TestMaintenanceScenario(FrappeTestCase):
	def setUp(self):
		self.client = _a_client()
		self.priority = _a_priority()
		if not (self.client and self.priority):
			self.skipTest("needs a Customer and an Issue Priority on this instance")

	def _scenario(self, **overrides):
		doc = frappe.get_doc(
			{
				"doctype": "Maintenance Scenario",
				"client": self.client,
				"scenario_name": SCENARIO,
				"priority": self.priority,
			}
		)
		doc.update(overrides)
		return doc

	def test_it_names_itself_from_the_series(self):
		doc = self._scenario().insert()
		self.assertTrue(doc.name.startswith("MSCN-"), msg=doc.name)

	def test_the_priority_is_looked_up_by_client_and_scenario(self):
		self._scenario().insert()
		self.assertEqual(get_scenario_priority(self.client, SCENARIO), self.priority)

	def test_an_unknown_pair_resolves_to_nothing(self):
		# The caller decides what to do; it must not fall back to a guessed priority.
		self.assertIsNone(get_scenario_priority(self.client, "_not a scenario_"))
		self.assertIsNone(get_scenario_priority(None, SCENARIO))
		self.assertIsNone(get_scenario_priority(self.client, None))

	def test_the_same_scenario_cannot_be_defined_twice_for_one_client(self):
		# A second record would make the priority behind a scenario ambiguous.
		self._scenario().insert()
		with self.assertRaises(frappe.ValidationError):
			self._scenario().insert()

	def test_client_scenario_and_priority_are_all_required(self):
		for missing in ("client", "scenario_name", "priority"):
			with self.assertRaises(frappe.exceptions.MandatoryError, msg=missing):
				self._scenario(**{missing: None}).insert()


class TestMaintenanceTicketType(FrappeTestCase):
	"""WI-001805 keys every SLA rule off this ticket type existing."""

	def test_the_maintenance_ticket_type_exists(self):
		self.assertTrue(frappe.db.exists("HD Ticket Type", "Maintenance"))
