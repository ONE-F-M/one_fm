# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime


def make_object(last_service_date=None, commissioning_date=None):
	"""Create a minimal Object asset for testing.

	ignore_mandatory keeps the deep Object Template / Space chain out of scope;
	only the date fields that drive the schedule calculation matter here.
	"""
	obj = frappe.get_doc({
		"doctype": "Object",
		"object_name": "TEST-MSE-OBJ",
		"last_service_date": last_service_date,
		"commissioning_date": commissioning_date,
	})
	obj.insert(ignore_mandatory=True, ignore_permissions=True)
	return obj


def make_frequency(days):
	name = f"Test Freq {days}"
	if frappe.db.exists("Maintenance Frequency", name):
		return frappe.get_doc("Maintenance Frequency", name)
	freq = frappe.get_doc({
		"doctype": "Maintenance Frequency",
		"maintenance_frequency_name": name,
		"frequency_days": days,
	})
	freq.insert(ignore_permissions=True)
	return freq


def make_schedule_entry(object_name, frequency=None, **kwargs):
	entry = frappe.get_doc({
		"doctype": "Maintenance Schedule Entry",
		"object": object_name,
		"status": "Open",
		"maintenance_frequency": frequency,
		**kwargs,
	})
	# ignore_mandatory skips the reqd Space (out of scope) while still running validate().
	entry.insert(ignore_mandatory=True, ignore_permissions=True)
	return entry


class TestMaintenanceScheduleEntry(FrappeTestCase):
	def test_planned_datetime_uses_last_service_date(self):
		"""Rule 1: Last Service Date + Frequency (Days) at 08:00."""
		obj = make_object(last_service_date="2026-06-01", commissioning_date="2026-05-10")
		freq = make_frequency(30)

		entry = make_schedule_entry(obj.name, freq.name)

		self.assertEqual(
			get_datetime(entry.planned_execution_datetime),
			get_datetime("2026-07-01 08:00:00"),
		)

	def test_planned_datetime_falls_back_to_commissioning_date(self):
		"""Rule 2: blank Last Service Date -> Commissioning Date + Frequency."""
		obj = make_object(last_service_date=None, commissioning_date="2026-05-10")
		freq = make_frequency(30)

		entry = make_schedule_entry(obj.name, freq.name)

		self.assertEqual(
			get_datetime(entry.planned_execution_datetime),
			get_datetime("2026-06-09 08:00:00"),
		)

	def test_planned_datetime_falls_back_to_creation_date(self):
		"""Rule 3: both dates blank -> Object Creation Date + Frequency."""
		obj = make_object(last_service_date=None, commissioning_date=None)
		# Pin the system creation date to a known value for a deterministic assertion.
		frappe.db.set_value("Object", obj.name, "creation", "2026-06-29 10:00:00")
		freq = make_frequency(7)

		entry = make_schedule_entry(obj.name, freq.name)

		self.assertEqual(
			get_datetime(entry.planned_execution_datetime),
			get_datetime("2026-07-06 08:00:00"),
		)

	def test_frequency_days_fetched_from_frequency(self):
		"""Frequency (Days) is resolved from the linked Maintenance Frequency."""
		obj = make_object(last_service_date="2026-06-01")
		freq = make_frequency(30)

		entry = make_schedule_entry(obj.name, freq.name)

		self.assertEqual(entry.frequency_days, 30)

	def test_planned_datetime_not_computed_without_frequency(self):
		"""No frequency -> no planned datetime derived."""
		obj = make_object(last_service_date="2026-06-01")

		entry = make_schedule_entry(obj.name, frequency=None)

		self.assertFalse(entry.planned_execution_datetime)

	def test_existing_planned_datetime_is_preserved(self):
		"""A manually set Planned Execution Datetime is not overwritten."""
		obj = make_object(last_service_date="2026-06-01")
		freq = make_frequency(30)

		entry = make_schedule_entry(
			obj.name, freq.name, planned_execution_datetime="2026-12-25 14:30:00"
		)

		self.assertEqual(
			get_datetime(entry.planned_execution_datetime),
			get_datetime("2026-12-25 14:30:00"),
		)
