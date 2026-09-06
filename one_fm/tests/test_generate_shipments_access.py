# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002162: who may press "Generate Shipments" on the Transportation Schedule.

The button lives on the transport team's own board, but the whitelisted method behind
it was gated on System Manager, so the supervisor running the board was told "You do
not have enough permissions to access this resource".
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import GENERATE_ROLES
from one_fm.patches.v15_0.grant_transportation_manager_schedule_access import execute

ROLE = "Transportation Manager"


class TestGenerateShipmentsIsTheTransportTeams(FrappeTestCase):
	def test_both_transport_roles_may_refresh_the_cards(self):
		self.assertIn("Transportation Manager", GENERATE_ROLES)
		self.assertIn("Transportation Supervisor", GENERATE_ROLES)

	def test_system_manager_keeps_the_access_it_had(self):
		self.assertIn("System Manager", GENERATE_ROLES)

	def _page_roles(self):
		name = frappe.db.get_value("Custom Role", {"page": "transportation-schedule"}, "name")
		return [row.role for row in frappe.get_doc("Custom Role", name).roles]

	def test_the_patch_opens_the_page_and_the_plan_to_the_manager(self):
		# Relaxing the method's role gate alone is not enough: the page is
		# role-restricted and the board is a Route Plan, so without both grants a
		# Transportation Manager never reaches the button to be refused by it.
		if not frappe.db.exists("Role", ROLE):
			self.skipTest(f"{ROLE} role missing on this site")

		execute()

		roles = self._page_roles()
		self.assertIn(ROLE, roles)
		self.assertIn("Transportation Supervisor", roles)  # not disturbed
		self.assertTrue(frappe.db.exists(
			"Custom DocPerm", {"parent": "Route Plan", "role": ROLE}
		))

	def test_running_the_patch_twice_grants_nothing_twice(self):
		if not frappe.db.exists("Role", ROLE):
			self.skipTest(f"{ROLE} role missing on this site")

		execute()
		execute()

		self.assertEqual(self._page_roles().count(ROLE), 1)
		self.assertEqual(frappe.db.count(
			"Custom DocPerm", {"parent": "Route Plan", "role": ROLE}
		), 1)
