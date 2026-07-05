# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, get_datetime, now_datetime

from one_fm.one_fm.doctype.maintenance_work_order import maintenance_work_order as mwo

# Reuse the asset / frequency / schedule / checklist factories from the
# Maintenance Schedule Entry test suite so the SLA tests stay focused on the
# Work Order behaviour rather than re-building the whole maintenance data chain.
from one_fm.one_fm.doctype.maintenance_schedule_entry.test_maintenance_schedule_entry import (
	make_category,
	make_checklist,
	make_frequency,
	make_object,
	make_object_for_schedule,
	make_schedule_entry,
)


# ─────────────────────────────────────────────────────────────────────────────
# Local factories
# ─────────────────────────────────────────────────────────────────────────────

# Target windows used across the suite (minutes).
TARGET_RESPONSE_MINUTES = 60
TARGET_RESOLUTION_MINUTES = 120


def make_issue_priority(name="_Test WO Priority"):
	"""Create (once) an Issue Priority used by the SLA and the Work Orders."""
	if frappe.db.exists("Issue Priority", name):
		return name
	doc = frappe.new_doc("Issue Priority")
	doc.name = name  # Issue Priority is Prompt-named
	doc.description = name
	doc.insert(ignore_permissions=True)
	return name


def get_test_customer():
	"""Return an existing Customer to use as the SLA entity, creating a minimal
	one only if the site has none. Reusing a real customer keeps the entity-match
	SLA test deterministic on a populated site.
	"""
	existing = frappe.db.get_value("Customer", {}, "name")
	if existing:
		return existing
	cust = frappe.get_doc({
		"doctype": "Customer",
		"customer_name": "_Test WO Customer",
		"customer_type": "Individual",
	})
	cust.insert(ignore_permissions=True)
	return cust.name


def make_holiday_list(name="TEST-WO-HOLIDAYS"):
	"""Create (once) a Maintenance Holiday List for the SLA's reqd holiday_list."""
	if frappe.db.exists("Maintenance Holiday List", name):
		return name
	doc = frappe.get_doc({
		"doctype": "Maintenance Holiday List",
		"holiday_list_name": name,
		"from_date": "2026-01-01",
		"to_date": "2026-12-31",
	})
	doc.insert(ignore_permissions=True)
	return doc.name


# Every weekday counts as working hours so the trigger reliably resolves to a
# working shift; the priority-only fallback in _fetch_sla_targets copies the
# targets regardless, so exact shift matching is not required for the tests.
_ALL_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def make_sla(
	priority,
	response_minutes=TARGET_RESPONSE_MINUTES,
	resolution_minutes=TARGET_RESOLUTION_MINUTES,
	shift_type="Working Hours",
	as_default=True,
	entity=None,
):
	"""Create and submit an active Maintenance Service Level Agreement.

	response_time / resolution_time are Duration fields stored in seconds, so the
	minute inputs are multiplied by 60. Exactly one priority row must be flagged
	as the default and carry maintenance-hours bounds (SLA validation rules).
	sla_fulfilled_on, holiday_list and support_and_resolution are mandatory.

	Pass ``entity`` (a Customer) to build an entity-scoped SLA (default off) that
	_find_matching_sla resolves before any site-wide default.
	"""
	sla = frappe.get_doc({
		"doctype": "Maintenance Service Level Agreement",
		"service_level": f"TEST-SLA-{frappe.generate_hash(length=6)}",
		"document_type": "Maintenance Work Order",
		"enabled": 1,
		"default_service_level_agreement": 0 if entity else (1 if as_default else 0),
		"entity_type": "Customer" if entity else None,
		"entity": entity,
		"holiday_list": make_holiday_list(),
		"priorities": [{
			"priority": priority,
			"default_priority": 1,
			"sla_shift_type": shift_type,
			"maintenance_hours_from": "00:00:00",
			"maintenance_hours_to": "23:59:59",
			"response_time": response_minutes * 60,
			"resolution_time": resolution_minutes * 60,
		}],
		"sla_fulfilled_on": [{"status": "Completed"}],
		"support_and_resolution": [
			{"workday": day, "start_time": "00:00:00", "end_time": "23:59:59"}
			for day in _ALL_WEEKDAYS
		],
	})
	sla.insert(ignore_permissions=True)
	sla.submit()
	return sla


def make_holiday_list_with_items(name, items):
	"""Create (once) a Maintenance Holiday List carrying explicit holiday rows.

	``items`` is an iterable of ``(holiday_date, weekly_off, public_holiday)``.
	The Maintenance Holiday Item ``description`` is mandatory, so a placeholder
	is supplied for each row.
	"""
	if frappe.db.exists("Maintenance Holiday List", name):
		return name
	doc = frappe.get_doc({
		"doctype": "Maintenance Holiday List",
		"holiday_list_name": name,
		"from_date": "2026-01-01",
		"to_date": "2026-12-31",
		"holidays": [
			{
				"holiday_date": holiday_date,
				"weekly_off": weekly_off,
				"public_holiday": public_holiday,
				"description": "Test calendar entry",
			}
			for (holiday_date, weekly_off, public_holiday) in items
		],
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def make_sla_with_calendar(
	priority,
	working_hours,
	holiday_list,
	resolution_minutes=TARGET_RESOLUTION_MINUTES,
	shift_type="Working Hours",
):
	"""Create and submit a default SLA with an explicit working-hours calendar.

	``working_hours`` is an iterable of ``(workday, start_time, end_time)`` used
	to build the Service Day rows that drive the Planned Deadline projection.
	"""
	sla = frappe.get_doc({
		"doctype": "Maintenance Service Level Agreement",
		"service_level": f"TEST-SLA-{frappe.generate_hash(length=6)}",
		"document_type": "Maintenance Work Order",
		"enabled": 1,
		"default_service_level_agreement": 1,
		"holiday_list": holiday_list,
		"priorities": [{
			"priority": priority,
			"default_priority": 1,
			"sla_shift_type": shift_type,
			"maintenance_hours_from": "00:00:00",
			"maintenance_hours_to": "23:59:59",
			"response_time": TARGET_RESPONSE_MINUTES * 60,
			"resolution_time": resolution_minutes * 60,
		}],
		"sla_fulfilled_on": [{"status": "Completed"}],
		"support_and_resolution": [
			{"workday": day, "start_time": start, "end_time": end}
			for (day, start, end) in working_hours
		],
	})
	sla.insert(ignore_permissions=True)
	sla.submit()
	return sla


def make_work_order(
	object_name,
	schedule_name=None,
	priority=None,
	sla_master=None,
	status="Open",
	maintenance_type="Preventive Maintenance",
	**kwargs,
):
	"""Insert a Maintenance Work Order.

	ignore_mandatory keeps the reqd Space / Checklist out of scope for the
	SLA-focused tests (before_save still runs). Pass an ``object_name`` created
	via make_object_for_schedule + a category checklist when the test needs a
	submittable Work Order.
	"""
	wo = frappe.get_doc({
		"doctype": "Maintenance Work Order",
		"maintenance_type": maintenance_type,
		"status": status,
		"object": object_name,
		"maintenance_schedule": schedule_name,
		"priority": priority,
		"sla_master": sla_master,
		**kwargs,
	})
	wo.insert(ignore_mandatory=True, ignore_permissions=True)
	return wo


# ─────────────────────────────────────────────────────────────────────────────
# AC1 (contract copy) + AC2 (timeline freeze)
# ─────────────────────────────────────────────────────────────────────────────


class TestPreventiveSlaContractAndTimeline(FrappeTestCase):
	def test_doctype_is_registered(self):
		meta = frappe.get_meta("Maintenance Work Order")
		self.assertIsNotNone(meta)
		self.assertEqual(meta.name, "Maintenance Work Order")

	def test_active_sla_and_targets_are_copied(self):
		"""AC1: the active client SLA is linked and the priority's target
		response / resolution windows are copied onto the Work Order.

		Uses an entity-scoped SLA matched by the Work Order's client so it
		resolves ahead of any site-wide default SLA.
		"""
		priority = make_issue_priority()
		customer = get_test_customer()
		sla = make_sla(priority, entity=customer)
		# A space-less Object so fetch_object_details does not overwrite the client.
		obj = make_object(last_service_date="2026-06-01")
		entry = make_schedule_entry(obj.name, make_frequency(30).name)

		# sla_master is left blank so _find_matching_sla resolves it by client.
		wo = make_work_order(
			obj.name, schedule_name=entry.name, priority=priority, client=customer
		)

		self.assertEqual(wo.sla_master, sla.name)
		self.assertEqual(wo.target_response_minutes, TARGET_RESPONSE_MINUTES)
		self.assertEqual(wo.target_resolution_minutes, TARGET_RESOLUTION_MINUTES)

	def test_trigger_time_uses_schedule_planned_datetime(self):
		"""AC2: SLA Trigger Time aligns with the schedule slot's planned start."""
		priority = make_issue_priority()
		sla = make_sla(priority)
		obj = make_object(last_service_date="2026-06-01")
		entry = make_schedule_entry(obj.name, make_frequency(30).name)

		wo = make_work_order(
			obj.name, schedule_name=entry.name, priority=priority, sla_master=sla.name
		)

		self.assertEqual(
			get_datetime(wo.sla_trigger_time),
			get_datetime(entry.planned_execution_datetime),
		)

	def test_trigger_time_fallback_last_service_date(self):
		"""AC2: with no planned datetime, trigger = Last Service Date + Frequency @ 08:00."""
		priority = make_issue_priority()
		sla = make_sla(priority)
		obj = make_object(last_service_date="2026-06-01", commissioning_date="2026-05-10")
		entry = make_schedule_entry(obj.name, make_frequency(30).name)
		# Force the Work Order's own fallback computation branch.
		frappe.db.set_value(
			"Maintenance Schedule Entry", entry.name, "planned_execution_datetime", None,
			update_modified=False,
		)

		wo = make_work_order(
			obj.name, schedule_name=entry.name, priority=priority, sla_master=sla.name
		)

		self.assertEqual(
			get_datetime(wo.sla_trigger_time), get_datetime("2026-07-01 08:00:00")
		)

	def test_trigger_time_fallback_object_creation_date(self):
		"""AC2: both asset dates blank -> Object Creation Date + Frequency @ 08:00."""
		priority = make_issue_priority()
		sla = make_sla(priority)
		obj = make_object(last_service_date=None, commissioning_date=None)
		frappe.db.set_value("Object", obj.name, "creation", "2026-06-29 10:00:00")
		entry = make_schedule_entry(obj.name, make_frequency(7).name)
		frappe.db.set_value(
			"Maintenance Schedule Entry", entry.name, "planned_execution_datetime", None,
			update_modified=False,
		)

		wo = make_work_order(
			obj.name, schedule_name=entry.name, priority=priority, sla_master=sla.name
		)

		self.assertEqual(
			get_datetime(wo.sla_trigger_time), get_datetime("2026-07-06 08:00:00")
		)

	def test_priority_outside_sla_blocks_save(self):
		"""A priority not configured in the linked SLA is rejected on save."""
		priority = make_issue_priority()
		other = make_issue_priority("_Test WO Priority Other")
		sla = make_sla(priority)
		obj = make_object(last_service_date="2026-06-01")

		with self.assertRaises(frappe.ValidationError):
			make_work_order(obj.name, priority=other, sla_master=sla.name)


# ─────────────────────────────────────────────────────────────────────────────
# AC3: live-clock countdown statuses (Pre-Start / Active Counting / Fail)
# ─────────────────────────────────────────────────────────────────────────────


class TestPreventiveSlaCountdown(FrappeTestCase):
	def _make_wo(self, planned):
		priority = make_issue_priority()
		sla = make_sla(priority)
		obj = make_object(last_service_date="2026-06-01")
		entry = make_schedule_entry(
			obj.name, make_frequency(30).name, planned_execution_datetime=planned
		)
		return make_work_order(
			obj.name, schedule_name=entry.name, priority=priority, sla_master=sla.name
		)

	def test_pre_start_before_trigger(self):
		"""AC3: before the trigger time both statuses default to 'Pre-Start'."""
		trigger = "2026-08-01 08:00:00"
		wo = self._make_wo(trigger)

		wo.refresh_sla_statuses(as_of=add_to_date(get_datetime(trigger), minutes=-5))

		self.assertEqual(wo.sla_response_status, "Pre-Start")
		self.assertEqual(wo.sla_resolution_status, "Pre-Start")

	def test_active_counting_after_trigger(self):
		"""AC3: at/after the trigger (within target) both go to 'Active Counting'."""
		trigger = "2026-08-01 08:00:00"
		wo = self._make_wo(trigger)

		wo.refresh_sla_statuses(as_of=add_to_date(get_datetime(trigger), minutes=5))

		self.assertEqual(wo.sla_response_status, "Active Counting")
		self.assertEqual(wo.sla_resolution_status, "Active Counting")

	def test_response_status_fail_when_target_exceeded(self):
		"""AC3: passing the response target before check-in flips response to 'Fail'."""
		trigger = "2026-08-01 08:00:00"
		wo = self._make_wo(trigger)

		wo.refresh_sla_statuses(
			as_of=add_to_date(get_datetime(trigger), minutes=TARGET_RESPONSE_MINUTES + 1)
		)

		self.assertEqual(wo.sla_response_status, "Fail")

	def test_resolution_status_fail_when_target_exceeded(self):
		"""AC3: passing the resolution target before completion flips resolution to 'Fail'."""
		trigger = "2026-08-01 08:00:00"
		wo = self._make_wo(trigger)

		wo.refresh_sla_statuses(
			as_of=add_to_date(get_datetime(trigger), minutes=TARGET_RESOLUTION_MINUTES + 1)
		)

		self.assertEqual(wo.sla_resolution_status, "Fail")

	def test_scheduler_engine_advances_status(self):
		"""AC3: the background engine recomputes the live status on its own.

		frappe.db.commit is patched out so the FrappeTestCase transaction still
		rolls back at the end of the test.
		"""
		planned = add_to_date(now_datetime(), minutes=-10)  # trigger just passed
		wo = self._make_wo(planned)

		# Reset to Pre-Start so the scheduler has something to advance.
		frappe.db.set_value(
			"Maintenance Work Order", wo.name, "sla_response_status", "Pre-Start",
			update_modified=False,
		)

		with patch("frappe.db.commit"):
			mwo.update_active_sla_statuses()

		wo.reload()
		self.assertEqual(wo.sla_response_status, "Active Counting")


# ─────────────────────────────────────────────────────────────────────────────
# AC4 (audit logs) + AC5 (response compliance)
# ─────────────────────────────────────────────────────────────────────────────


class TestPreventiveSlaCheckInAndCompletion(FrappeTestCase):
	def _make_wo(self, minutes_before_now):
		priority = make_issue_priority()
		sla = make_sla(priority)
		obj = make_object(last_service_date="2026-06-01")
		planned = add_to_date(now_datetime(), minutes=minutes_before_now)
		entry = make_schedule_entry(
			obj.name, make_frequency(30).name, planned_execution_datetime=planned
		)
		return make_work_order(
			obj.name, schedule_name=entry.name, priority=priority, sla_master=sla.name
		)

	def test_check_in_stamps_time_and_passes(self):
		"""AC4/AC5: first check-in stamps the time; within target -> 'Pass'."""
		wo = self._make_wo(minutes_before_now=-10)  # trigger 10 min ago

		result = mwo.check_in(work_order=wo.name)

		self.assertFalse(result["already_checked_in"])
		wo.reload()
		self.assertTrue(wo.first_check_in_time)
		self.assertAlmostEqual(wo.actual_response_minutes, 10, delta=1)
		self.assertEqual(wo.sla_response_status, "Pass")

	def test_check_in_fails_when_late(self):
		"""AC5: check-in beyond the response target -> 'Fail'."""
		wo = self._make_wo(minutes_before_now=-(TARGET_RESPONSE_MINUTES + 60))

		mwo.check_in(work_order=wo.name)

		wo.reload()
		self.assertAlmostEqual(
			wo.actual_response_minutes, TARGET_RESPONSE_MINUTES + 60, delta=1
		)
		self.assertEqual(wo.sla_response_status, "Fail")

	def test_check_in_is_idempotent(self):
		"""AC4: the first click wins; a repeat check-in never overwrites the time."""
		wo = self._make_wo(minutes_before_now=-10)

		first = mwo.check_in(work_order=wo.name)
		second = mwo.check_in(work_order=wo.name)

		self.assertFalse(first["already_checked_in"])
		self.assertTrue(second["already_checked_in"])
		self.assertEqual(
			get_datetime(first["first_check_in_time"]),
			get_datetime(second["first_check_in_time"]),
		)

	def test_completion_time_stamped_on_submit(self):
		"""AC4: submitting the Work Order stamps the Completion Time."""
		priority = make_issue_priority()
		sla = make_sla(priority)
		cat = make_category()
		make_checklist(cat, [("Inspect filter", 30)])
		# Object with Space + Category so the reqd Space / Checklist auto-fill and
		# the Work Order becomes submittable.
		obj = make_object_for_schedule(object_category=cat, last_service_date="2026-06-01")
		planned = add_to_date(now_datetime(), minutes=-30)
		entry = make_schedule_entry(
			obj.name, make_frequency(30).name, planned_execution_datetime=planned
		)
		wo = make_work_order(
			obj.name, schedule_name=entry.name, priority=priority, sla_master=sla.name
		)

		wo.submit()

		wo.reload()
		self.assertTrue(wo.completion_time)
		self.assertEqual(wo.docstatus, 1)


# ─────────────────────────────────────────────────────────────────────────────
# AC6: analytics (Total Paused Minutes, Net Resolution Minutes)
# ─────────────────────────────────────────────────────────────────────────────


class TestPreventiveSlaAnalytics(FrappeTestCase):
	def test_total_paused_minutes_accumulates_across_hold(self):
		"""AC6: time spent in 'On Hold - Parts Required' accrues to Total Paused Minutes."""
		obj = make_object(last_service_date="2026-06-01")
		wo = make_work_order(obj.name, status="Open")

		# Enter the hold — the pause clock starts.
		wo.status = "On Hold - Parts Required"
		wo.save()
		# Backdate the hold start by 15 minutes to simulate an elapsed pause window.
		frappe.db.set_value(
			"Maintenance Work Order", wo.name, "hold_started_on",
			add_to_date(now_datetime(), minutes=-15), update_modified=False,
		)
		wo.reload()

		# Leave the hold — the elapsed pause is banked.
		wo.status = "Dispatched"
		wo.save()

		self.assertAlmostEqual(wo.total_paused_minutes, 15, delta=1)
		self.assertFalse(wo.hold_started_on)

	def test_net_resolution_minutes_excludes_paused_time(self):
		"""AC6: Net Resolution = (Completion - Trigger) - Total Paused Minutes."""
		priority = make_issue_priority()
		sla = make_sla(priority)
		cat = make_category()
		make_checklist(cat, [("Inspect filter", 30)])
		obj = make_object_for_schedule(object_category=cat, last_service_date="2026-06-01")
		planned = add_to_date(now_datetime(), minutes=-100)  # trigger 100 min ago
		entry = make_schedule_entry(
			obj.name, make_frequency(30).name, planned_execution_datetime=planned
		)
		wo = make_work_order(
			obj.name, schedule_name=entry.name, priority=priority, sla_master=sla.name
		)
		# 10 minutes already banked as paused.
		frappe.db.set_value(
			"Maintenance Work Order", wo.name, "total_paused_minutes", 10,
			update_modified=False,
		)
		wo.reload()

		wo.submit()

		wo.reload()
		# ~100 minutes elapsed minus 10 paused = ~90.
		self.assertAlmostEqual(wo.net_resolution_minutes, 90, delta=1)
		self.assertEqual(wo.sla_resolution_status, "Pass")  # 90 <= 120 target


# ─────────────────────────────────────────────────────────────────────────────
# Planned Deadline — automated working-calendar aware completion target
# ─────────────────────────────────────────────────────────────────────────────

# Every day of the example week (Mon–Fri + Sun) works an 08:00–17:00 shift;
# Saturday is deliberately omitted so the team is off that day.
_DAY_SHIFT_NO_SATURDAY = [
	(day, "08:00:00", "17:00:00")
	for day in ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
]

_DAY_SHIFT_ALL_WEEK = [
	(day, "08:00:00", "17:00:00")
	for day in _ALL_WEEKDAYS
]


class TestPlannedDeadline(FrappeTestCase):
	def _make_wo(self, sla, trigger, priority):
		"""Build a Preventive Work Order whose SLA Trigger Time equals ``trigger``.

		The trigger is fed through the schedule slot's planned execution datetime,
		which set_preventive_sla freezes onto the Work Order.
		"""
		obj = make_object(last_service_date="2026-06-01")
		entry = make_schedule_entry(
			obj.name, make_frequency(30).name, planned_execution_datetime=trigger
		)
		return make_work_order(
			obj.name, schedule_name=entry.name, priority=priority, sla_master=sla.name
		)

	def test_field_is_read_only(self):
		"""AC3: the Planned Deadline field is strictly read-only."""
		meta = frappe.get_meta("Maintenance Work Order")
		field = meta.get_field("planned_deadline")
		self.assertIsNotNone(field)
		self.assertEqual(field.read_only, 1)

	def test_simple_addition_within_working_window(self):
		"""AC1: trigger 2026-06-30 10:00 + 120 min → 2026-06-30 12:00.

		Uses a 24/7 SLA (all weekdays 00:00–23:59:59, no holidays) so the whole
		resolution window fits inside a single working day.
		"""
		priority = make_issue_priority()
		# Default make_sla builds all-weekday 00:00–23:59:59 windows.
		sla = make_sla(priority, resolution_minutes=120)
		wo = self._make_wo(sla, "2026-06-30 10:00:00", priority)

		self.assertEqual(
			get_datetime(wo.planned_deadline), get_datetime("2026-06-30 12:00:00")
		)

	def test_skips_weekend_and_non_working_hours(self):
		"""AC2 (worked example): trigger Fri 2026-07-03 16:00, 180 min, shift
		08:00–17:00, Saturday off → deadline Sun 2026-07-05 10:00.

		1 hour is consumed Friday (16:00→17:00), Saturday is skipped entirely,
		and the remaining 2 hours resume Sunday from 08:00.
		"""
		priority = make_issue_priority()
		holidays = make_holiday_list_with_items("TEST-WO-CAL-SAT-OFF", [])
		sla = make_sla_with_calendar(
			priority, _DAY_SHIFT_NO_SATURDAY, holidays, resolution_minutes=180
		)
		wo = self._make_wo(sla, "2026-07-03 16:00:00", priority)

		self.assertEqual(
			get_datetime(wo.planned_deadline), get_datetime("2026-07-05 10:00:00")
		)

	def test_skips_public_holiday(self):
		"""AC2: a public holiday between the trigger and the deadline is skipped.

		Trigger Thu 2026-07-02 16:00, 180 min, shift 08:00–17:00 every day, with
		Fri 2026-07-03 flagged as a public holiday. 1 hour is spent Thursday, the
		Friday holiday is skipped, and the remaining 2 hours resume Sat 08:00 →
		deadline Sat 2026-07-04 10:00.
		"""
		priority = make_issue_priority()
		holidays = make_holiday_list_with_items(
			"TEST-WO-CAL-PUBLIC-HOL", [("2026-07-03", 0, 1)]
		)
		sla = make_sla_with_calendar(
			priority, _DAY_SHIFT_ALL_WEEK, holidays, resolution_minutes=180
		)
		wo = self._make_wo(sla, "2026-07-02 16:00:00", priority)

		self.assertEqual(
			get_datetime(wo.planned_deadline), get_datetime("2026-07-04 10:00:00")
		)

	def test_trigger_before_shift_start_rolls_to_opening(self):
		"""A trigger before the working window opens counts from the shift start.

		Trigger 2026-07-06 06:00 (Monday, before 08:00), 120 min, shift
		08:00–17:00 → counting starts at 08:00 → deadline 2026-07-06 10:00.
		"""
		priority = make_issue_priority()
		holidays = make_holiday_list_with_items("TEST-WO-CAL-PRE-SHIFT", [])
		sla = make_sla_with_calendar(
			priority, _DAY_SHIFT_ALL_WEEK, holidays, resolution_minutes=120
		)
		wo = self._make_wo(sla, "2026-07-06 06:00:00", priority)

		self.assertEqual(
			get_datetime(wo.planned_deadline), get_datetime("2026-07-06 10:00:00")
		)

	def test_deadline_recomputed_on_resave(self):
		"""Recompute each save: the deadline stays consistent after re-saving."""
		priority = make_issue_priority()
		sla = make_sla(priority, resolution_minutes=120)
		wo = self._make_wo(sla, "2026-06-30 10:00:00", priority)

		first = get_datetime(wo.planned_deadline)
		wo.save()
		wo.reload()

		self.assertEqual(get_datetime(wo.planned_deadline), first)
		self.assertEqual(first, get_datetime("2026-06-30 12:00:00"))
