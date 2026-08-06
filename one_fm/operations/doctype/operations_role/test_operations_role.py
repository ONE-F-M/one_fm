# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and Contributors
# See license.txt
"""WI-001982: an Operations Role's Sale Item has to be one the project is contracted for."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from one_fm.operations.doctype.operations_role.operations_role import (
	get_contracted_sale_items,
	sale_item_query,
)

CONTRACT = "_TEST-ROLE-CONTRACT"
PROJECT = "_Test Role Contract Project"


def _a_non_stock_item(exclude=None):
	return frappe.db.get_value(
		"Item", {"is_stock_item": 0, "name": ["!=", exclude or ""]}, "name", order_by="name asc"
	)


class TestContractedSaleItems(FrappeTestCase):
	def setUp(self):
		self.project = self._project()
		self.contracted_item = _a_non_stock_item()
		self.off_contract_item = _a_non_stock_item(exclude=self.contracted_item)
		self.contract = self._contract()

	def _project(self):
		if frappe.db.exists("Project", PROJECT):
			return frappe.get_doc("Project", PROJECT)
		return frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": PROJECT,
				"company": frappe.db.get_value("Company", {}, "name"),
			}
		).insert(ignore_permissions=True)

	def _contract(self, workflow_state="Active"):
		"""An Active contract with one item, inserted raw.

		The Contracts controller commits in several paths, which would defeat the
		auto-rollback that keeps these tests isolated - and child rows outlive the
		parent delete, so the line item is cleared explicitly.
		"""
		frappe.db.delete("Contract Item", {"parent": CONTRACT})
		frappe.db.delete("Contracts", {"name": CONTRACT})

		contract = frappe.new_doc("Contracts")
		contract.name = CONTRACT
		contract.project = self.project.name
		contract.start_date = getdate("2026-01-01")
		contract.end_date = getdate("2026-12-31")
		contract.workflow_state = workflow_state
		contract.db_insert()

		item = frappe.new_doc("Contract Item")
		item.parent = CONTRACT
		item.parenttype = "Contracts"
		item.parentfield = "items"
		item.item_code = self.contracted_item
		item.idx = 1
		item.db_insert()

		return contract

	def test_the_contracted_items_are_read_off_active_contracts(self):
		self.assertEqual(get_contracted_sale_items(self.project.name), {self.contracted_item})

	def test_a_project_with_no_active_contract_is_unrestricted(self):
		"""None, not an empty set - otherwise an internal project could hold no post."""
		frappe.db.set_value("Contracts", CONTRACT, "workflow_state", "Inactive")

		self.assertIsNone(get_contracted_sale_items(self.project.name))

	def test_the_dropdown_offers_only_contracted_items(self):
		offered = [
			row[0]
			for row in sale_item_query(
				"Item", "", "name", 0, 20, {"project": self.project.name}
			)
		]

		self.assertEqual(offered, [self.contracted_item])

	def test_the_dropdown_is_unrestricted_without_an_active_contract(self):
		frappe.db.set_value("Contracts", CONTRACT, "workflow_state", "Inactive")

		offered = [
			row[0]
			for row in sale_item_query(
				"Item", "", "name", 0, 20, {"project": self.project.name}
			)
		]

		self.assertIn(self.off_contract_item, offered)

	def test_an_off_contract_item_is_refused_on_a_new_role(self):
		role = self._role(self.off_contract_item)

		with self.assertRaises(frappe.ValidationError) as caught:
			role.validate_sale_item_against_contract()
		self.assertIn("not on any Active contract", str(caught.exception))

	def test_a_contracted_item_is_accepted(self):
		self._role(self.contracted_item).validate_sale_item_against_contract()

	def test_an_existing_role_keeps_its_off_contract_item(self):
		"""422 roles on this site already hold one; editing them must not be blocked.

		Saved raw so the role exists holding an item its contract does not cover - the
		state those 422 are in - then saved again through the controller, which is the
		edit that must still go through.
		"""
		role_name = "_Test Legacy Operations Role"
		frappe.db.delete("Operations Role", {"name": role_name})

		role = self._role(self.off_contract_item)
		role.name = role_name
		role.post_abbrv = "TLOR"
		role.shift = frappe.db.get_value("Operations Shift", {}, "name")
		role.status = "Inactive"
		role.db_insert()

		frappe.get_doc("Operations Role", role_name).save()

		self.assertEqual(
			frappe.db.get_value("Operations Role", role_name, "sale_item"),
			self.off_contract_item,
		)

	def test_changing_the_item_on_an_existing_role_is_held_to_the_rule(self):
		role_name = "_Test Legacy Operations Role"
		frappe.db.delete("Operations Role", {"name": role_name})

		role = self._role(self.contracted_item)
		role.name = role_name
		role.post_abbrv = "TLOR"
		role.shift = frappe.db.get_value("Operations Shift", {}, "name")
		role.status = "Inactive"
		role.db_insert()

		saved = frappe.get_doc("Operations Role", role_name)
		saved.sale_item = self.off_contract_item

		with self.assertRaises(frappe.ValidationError):
			saved.save()

	def _role(self, sale_item):
		role = frappe.new_doc("Operations Role")
		role.update(
			{"post_name": "_Test Post", "sale_item": sale_item, "project": self.project.name}
		)
		return role
