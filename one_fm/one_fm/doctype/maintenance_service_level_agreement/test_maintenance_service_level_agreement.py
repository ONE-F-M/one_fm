# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import ValidationError
from frappe.tests.utils import FrappeTestCase


def ensure_issue_priority(name):
	if not frappe.db.exists("Issue Priority", name):
		frappe.get_doc({"doctype": "Issue Priority", "name": name}).insert(
			ignore_permissions=True
		)


def ensure_customer(name):
	if not frappe.db.exists("Customer", name):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_group": "All Customer Groups",
				"territory": "All Territories",
			}
		).insert(ignore_permissions=True)
	return name


def ensure_holiday_list(name):
	if not frappe.db.exists("Maintenance Holiday List", name):
		frappe.get_doc(
			{
				"doctype": "Maintenance Holiday List",
				"holiday_list_name": name,
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
			}
		).insert(ignore_permissions=True)
	return name


class TestMaintenanceServiceLevelAgreement(FrappeTestCase):
	def make_sla(self, **overrides):
		"""Build an insertable Maintenance Service Level Agreement.

		Sensible defaults are provided for every mandatory field so callers can
		either call ``.validate()`` in isolation or ``.insert()`` a real record.
		"""
		doc = frappe.get_doc(
			{
				"doctype": "Maintenance Service Level Agreement",
				"document_type": "Issue",
				"service_level": "Default Service Level",
				"enabled": 1,
				"entity_type": "Customer",
				"entity": None,
				"start_date": "2026-01-01",
				"end_date": "2026-12-31",
				"holiday_list": None,
				"priorities": [
					{
						"priority": "Low",
						"default_priority": 1,
						"sla_shift_type": "Working Hours",
						"maintenance_hours_from": "09:00:00",
						"maintenance_hours_to": "17:00:00",
						"response_time": 3600,
					}
				],
				"sla_fulfilled_on": [{"status": "Closed"}],
				"support_and_resolution": [
					{
						"workday": "Monday",
						"start_time": "09:00:00",
						"end_time": "17:00:00",
					}
				],
			}
		)

		for key, value in overrides.items():
			doc.set(key, value)

		return doc

	# --- Existing validations -------------------------------------------------

	def test_validate_rejects_end_date_before_start_date(self):
		doc = self.make_sla(start_date="2026-12-31", end_date="2026-01-01")

		with self.assertRaises(ValidationError):
			doc.validate()

	def test_validate_rejects_multiple_default_priorities(self):
		doc = self.make_sla(
			priorities=[
				{
					"priority": "Low",
					"default_priority": 1,
				},
				{
					"priority": "High",
					"default_priority": 1,
				},
			]
		)

		with self.assertRaises(ValidationError):
			doc.validate()

	# --- Single enabled SLA per client ---------------------------------------

	def test_blocks_second_enabled_sla_for_same_client(self):
		ensure_issue_priority("Low")
		holiday_list = ensure_holiday_list("_Test Maintenance Holiday List")
		customer = ensure_customer("_Test SLA Cust Blocks")

		existing = self.make_sla(
			service_level="Blocks Primary",
			entity=customer,
			holiday_list=holiday_list,
		)
		existing.insert(ignore_permissions=True)

		second = self.make_sla(
			service_level="Blocks Secondary",
			entity=customer,
			holiday_list=holiday_list,
		)

		with self.assertRaises(ValidationError):
			second.validate()

	def test_allows_second_disabled_sla_for_same_client(self):
		ensure_issue_priority("Low")
		holiday_list = ensure_holiday_list("_Test Maintenance Holiday List")
		customer = ensure_customer("_Test SLA Cust Disabled")

		existing = self.make_sla(
			service_level="Disabled Primary",
			entity=customer,
			holiday_list=holiday_list,
		)
		existing.insert(ignore_permissions=True)

		second = self.make_sla(
			service_level="Disabled Secondary",
			entity=customer,
			holiday_list=holiday_list,
			enabled=0,
		)

		# A disabled agreement must not be blocked.
		second.validate()

	def test_allows_enabled_sla_for_different_client(self):
		ensure_issue_priority("Low")
		holiday_list = ensure_holiday_list("_Test Maintenance Holiday List")
		customer_a = ensure_customer("_Test SLA Cust DiffA")
		customer_b = ensure_customer("_Test SLA Cust DiffB")

		existing = self.make_sla(
			service_level="Diff Primary",
			entity=customer_a,
			holiday_list=holiday_list,
		)
		existing.insert(ignore_permissions=True)

		second = self.make_sla(
			service_level="Diff Secondary",
			entity=customer_b,
			holiday_list=holiday_list,
		)

		# A different client must not be blocked.
		second.validate()

	def test_allows_resaving_the_same_enabled_sla(self):
		ensure_issue_priority("Low")
		holiday_list = ensure_holiday_list("_Test Maintenance Holiday List")
		customer = ensure_customer("_Test SLA Cust Resave")

		existing = self.make_sla(
			service_level="Resave Primary",
			entity=customer,
			holiday_list=holiday_list,
		)
		existing.insert(ignore_permissions=True)

		# Re-validating the same record must not flag itself as a conflict.
		existing.validate()

	def test_rule_only_applies_to_customer_entity_type(self):
		ensure_issue_priority("Low")
		holiday_list = ensure_holiday_list("_Test Maintenance Holiday List")
		customer = ensure_customer("_Test SLA Cust EntityType")

		existing = self.make_sla(
			service_level="EntityType Primary",
			entity=customer,
			holiday_list=holiday_list,
		)
		existing.insert(ignore_permissions=True)

		# A non-Customer entity type is outside the "single client" rule.
		territory_sla = self.make_sla(
			service_level="EntityType Territory",
			entity_type="Territory",
			entity="All Territories",
			holiday_list=holiday_list,
		)

		territory_sla.validate()
