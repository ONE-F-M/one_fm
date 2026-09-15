# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import types

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, get_datetime, getdate, today

from one_fm.one_fm.doctype.maintenance_schedule_entry import (
	maintenance_schedule_entry as mse,
)


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


# ─────────────────────────────────────────────────────────────────────────────
# Preventive Maintenance Automation tests
# ─────────────────────────────────────────────────────────────────────────────


def make_space():
	"""Minimal Space so generated slots satisfy the reqd `space` field.

	A unique space_name is used per call because FrappeTestCase rolls back per
	test class (not per method), so fixed names would collide across methods.
	ignore_mandatory keeps the deep Floor -> Building -> Site -> Project chain
	out of scope for these schedule-generation tests.
	"""
	space = frappe.get_doc({
		"doctype": "Space",
		"space_name": f"TEST-MSE-{frappe.generate_hash(length=8)}",
	})
	space.insert(ignore_mandatory=True, ignore_permissions=True)
	return space


def make_category():
	"""Create a uniquely-named Object Category so each test's checklist is the
	only checklist matching that category.
	"""
	cat = frappe.get_doc({
		"doctype": "Object Category",
		"object_category_name": f"TEST-MSE-CAT-{frappe.generate_hash(length=8)}",
	})
	cat.insert(ignore_permissions=True)
	return cat.name


def make_checklist(object_category, tasks):
	"""Create an Object Maintenance Checklist for a category.

	`tasks` is a list of (task_description, frequency_days) tuples that become the
	child rows. `maintenance_frequency` is reqd on each row, so a Maintenance
	Frequency (carrying the given frequency_days, which may be 0) is always linked.
	"""
	items = []
	for idx, (desc, days) in enumerate(tasks):
		freq = make_frequency(days)
		items.append({
			"sequence_no": idx + 1,
			"task_description": desc,
			"maintenance_frequency": freq.name,
			"frequency_days": days,
		})

	checklist = frappe.get_doc({
		"doctype": "Object Maintenance Checklist",
		"checklist_name": "TEST-MSE-CHECKLIST",
		"object_category": object_category,
		"object_maintenance_checklist_items": items,
	})
	checklist.insert(ignore_permissions=True)
	return checklist


def make_object_for_schedule(object_category=None, last_service_date=None):
	"""Create an Object (with a Space and Category) for schedule generation."""
	space = make_space()
	obj = frappe.get_doc({
		"doctype": "Object",
		"object_name": "TEST-MSE-BUILD-OBJ",
		"object_category": object_category,
		"space": space.name,
		"last_service_date": last_service_date,
	})
	obj.insert(ignore_mandatory=True, ignore_permissions=True)
	return obj


def set_settings(months=None, lead_days=None):
	"""Set the global Maintenance Settings (save() clears the single-doc cache)."""
	settings = frappe.get_doc("Maintenance Settings")
	if months is not None:
		settings.schedule_generation_months = months
	if lead_days is not None:
		settings.work_order_generation_lead_time_days = lead_days
	settings.save(ignore_permissions=True)


def _expected_count(base_date, interval_days, months):
	"""Independently count occurrences of one task from base up to today + N months."""
	stop = getdate(add_months(today(), months))
	count = 0
	d = getdate(base_date)
	while True:
		d = add_days(d, interval_days)
		if getdate(d) > stop:
			break
		count += 1
	return count


class TestBuildSchedule(FrappeTestCase):
	def test_build_schedule_generates_a_slot_per_task_occurrence(self):
		"""One slot is created per checklist task per occurrence up to the stop line."""
		cat = make_category()
		make_checklist(cat, [("Inspect filter", 30), ("Replace belt", 90)])
		obj = make_object_for_schedule(object_category=cat, last_service_date=today())
		set_settings(months=6)

		created = mse.build_schedule(obj.name)

		expected = _expected_count(today(), 30, 6) + _expected_count(today(), 90, 6)
		self.assertEqual(created, expected)
		self.assertEqual(
			frappe.db.count("Maintenance Schedule Entry", {"object": obj.name}), expected
		)

		# Each generated slot carries its task + frequency and starts 'Open'.
		rows = frappe.get_all(
			"Maintenance Schedule Entry",
			filters={"object": obj.name},
			fields=["maintenance_task", "frequency_days", "status"],
		)
		self.assertTrue(all(r.status == "Open" for r in rows))
		self.assertEqual(
			{r.maintenance_task for r in rows}, {"Inspect filter", "Replace belt"}
		)
		for r in rows:
			expected_days = 30 if r.maintenance_task == "Inspect filter" else 90
			self.assertEqual(r.frequency_days, expected_days)

	def test_build_schedule_is_idempotent(self):
		"""Re-running never duplicates a slot (same object + task + planned date)."""
		cat = make_category()
		make_checklist(cat, [("Inspect filter", 30)])
		obj = make_object_for_schedule(object_category=cat, last_service_date=today())
		set_settings(months=6)

		first = mse.build_schedule(obj.name)
		second = mse.build_schedule(obj.name)

		self.assertGreater(first, 0)
		self.assertEqual(second, 0)
		self.assertEqual(
			frappe.db.count("Maintenance Schedule Entry", {"object": obj.name}), first
		)

	def test_build_schedule_starts_from_last_service_date(self):
		"""Occurrences begin at Last Service Date + frequency (per the agreed algorithm)."""
		base = add_days(today(), -100)
		cat = make_category()
		make_checklist(cat, [("Inspect filter", 30)])
		obj = make_object_for_schedule(object_category=cat, last_service_date=base)
		set_settings(months=3)

		mse.build_schedule(obj.name)

		planned = frappe.get_all(
			"Maintenance Schedule Entry", filters={"object": obj.name}, pluck="planned_execution_datetime"
		)
		earliest = min(getdate(p) for p in planned)
		self.assertEqual(earliest, getdate(add_days(base, 30)))
		for p in planned:
			self.assertLessEqual(getdate(p), getdate(add_months(today(), 3)))

	def test_build_schedule_no_checklist_creates_nothing(self):
		"""A category with no master checklist generates no slots."""
		cat = make_category()
		obj = make_object_for_schedule(object_category=cat, last_service_date=today())
		set_settings(months=3)

		self.assertEqual(mse.build_schedule(obj.name), 0)

	def test_build_schedule_skips_task_with_non_positive_frequency(self):
		"""Defensive guard: a task whose frequency_days is <= 0 is skipped.

		Maintenance Frequency validation forbids creating a zero-day frequency, so
		the corrupt interval is forced directly onto the checklist row to exercise
		the guard in build_schedule.
		"""
		cat = make_category()
		checklist = make_checklist(cat, [("Inspect filter", 30), ("Ad-hoc note", 90)])
		adhoc = next(
			row for row in checklist.object_maintenance_checklist_items
			if row.task_description == "Ad-hoc note"
		)
		frappe.db.set_value(
			"Object Maintenance Checklist Items", adhoc.name, "frequency_days", 0
		)
		obj = make_object_for_schedule(object_category=cat, last_service_date=today())
		set_settings(months=3)

		mse.build_schedule(obj.name)

		tasks = frappe.get_all(
			"Maintenance Schedule Entry", filters={"object": obj.name}, pluck="maintenance_task"
		)
		self.assertIn("Inspect filter", tasks)
		self.assertNotIn("Ad-hoc note", tasks)

	def test_build_schedule_zero_months_creates_nothing(self):
		"""Schedule Generation (Months) = 0 generates no slots."""
		cat = make_category()
		make_checklist(cat, [("Inspect filter", 30)])
		obj = make_object_for_schedule(object_category=cat, last_service_date=today())
		set_settings(months=0)

		self.assertEqual(mse.build_schedule(obj.name), 0)


class TestGenerateDueWorkOrders(FrappeTestCase):
	def setUp(self):
		# Deterministic Work Order stub so we can assert the slot-selection and
		# status-flip logic without the full Work Order data chain (priority,
		# team, checklist) which is out of scope here.
		self._orig = mse.create_work_order_from_entry
		mse.create_work_order_from_entry = lambda entry: types.SimpleNamespace(
			name=f"TEST-WO-{entry.name}"
		)

	def tearDown(self):
		mse.create_work_order_from_entry = self._orig

	def _make_open_slot(self, object_name, days_from_today):
		planned = get_datetime(f"{add_days(today(), days_from_today)} 08:00:00")
		return make_schedule_entry(
			object_name, frequency=None, planned_execution_datetime=planned
		)

	def test_only_slots_within_lead_window_get_work_orders(self):
		obj = make_object(last_service_date=today())
		set_settings(lead_days=5)

		past_due = self._make_open_slot(obj.name, -3)
		inside = self._make_open_slot(obj.name, 2)
		boundary = self._make_open_slot(obj.name, 5)
		outside = self._make_open_slot(obj.name, 10)

		created = mse.generate_due_work_orders(object_name=obj.name)

		self.assertEqual(created, 3)
		for name in (past_due.name, inside.name, boundary.name):
			row = frappe.db.get_value(
				"Maintenance Schedule Entry", name, ["status", "work_order"], as_dict=True
			)
			self.assertEqual(row.status, "Work Order Created")
			self.assertTrue(row.work_order)

		outside_row = frappe.db.get_value(
			"Maintenance Schedule Entry", outside.name, ["status", "work_order"], as_dict=True
		)
		self.assertEqual(outside_row.status, "Open")
		self.assertFalse(outside_row.work_order)

	def test_generate_due_work_orders_is_idempotent(self):
		obj = make_object(last_service_date=today())
		set_settings(lead_days=5)
		self._make_open_slot(obj.name, 2)

		first = mse.generate_due_work_orders(object_name=obj.name)
		second = mse.generate_due_work_orders(object_name=obj.name)

		self.assertEqual(first, 1)
		self.assertEqual(second, 0)


class TestWorkOrderCreationEndToEnd(FrappeTestCase):
	"""Exercises the real create_work_order_from_entry (no stub) now that
	priority / assigned_maintenance_team are optional on Maintenance Work Order.
	"""

	def test_real_work_order_is_created_and_slot_flipped(self):
		cat = make_category()
		# A category checklist must exist so the Work Order can auto-route its
		# (still reqd) object_maintenance_checklist.
		make_checklist(cat, [("Inspect filter", 30)])
		obj = make_object_for_schedule(object_category=cat, last_service_date=today())
		set_settings(lead_days=5)

		planned = get_datetime(f"{add_days(today(), 1)} 08:00:00")
		entry = make_schedule_entry(
			obj.name,
			frequency=None,
			maintenance_task="Inspect filter",
			planned_execution_datetime=planned,
		)

		created = mse.generate_due_work_orders(object_name=obj.name)
		self.assertEqual(created, 1)

		entry.reload()
		self.assertEqual(entry.status, "Work Order Created")
		self.assertTrue(entry.work_order)

		wo = frappe.get_doc("Maintenance Work Order", entry.work_order)
		self.assertEqual(wo.maintenance_type, "Preventive Maintenance")
		self.assertEqual(wo.status, "Open")
		self.assertEqual(wo.object, obj.name)
		self.assertEqual(wo.maintenance_schedule, entry.name)
		# Auto-routed from the object's category checklist.
		self.assertTrue(wo.object_maintenance_checklist)
