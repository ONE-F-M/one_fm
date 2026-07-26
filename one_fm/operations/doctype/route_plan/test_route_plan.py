# Copyright (c) 2026, oneaborance and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.operations.doctype.route_plan.route_plan import (
	_date_ranges_overlap,
	_detect_retention_conflict,
	_format_lock_until,
	_time_windows_overlap,
	_windows_overlap,
)

DAY = "2026-07-20"
NEXT_DAY = "2026-07-21"


def _shipment(name, *, retention=0, from_date=DAY, to_date=DAY,
			  start="08:00:00", end="14:00:00", source=None):
	"""Build an in-memory retention-window dict as _get_shipment_windows returns."""
	return frappe._dict({
		"name": name,
		"requires_vehicle_retention": retention,
		"from_date": from_date,
		"to_date": to_date,
		"start_time": start,
		"end_time": end,
		"source_docname": source,
	})


class TestRetentionOverlapLogic(FrappeTestCase):
	"""TR4-7: pure date-range × daily-time overlap detection, no fixtures needed."""

	def test_date_ranges_overlap_true_and_false(self):
		self.assertTrue(_date_ranges_overlap(DAY, DAY, DAY, DAY))
		self.assertTrue(_date_ranges_overlap("2026-07-18", "2026-07-22", DAY, DAY))
		self.assertFalse(_date_ranges_overlap(DAY, DAY, NEXT_DAY, NEXT_DAY))

	def test_date_ranges_open_ended_bounds_always_overlap(self):
		# A standing card with no from/to date is active on every calendar day.
		self.assertTrue(_date_ranges_overlap(None, None, DAY, DAY))
		self.assertTrue(_date_ranges_overlap(DAY, None, "2030-01-01", "2030-01-01"))

	def test_time_windows_overlap_when_they_intersect(self):
		# Retention 08:00-14:00 vs grocery run 11:30-12:30 -> overlap.
		self.assertTrue(_time_windows_overlap("08:00:00", "14:00:00", "11:30:00", "12:30:00"))

	def test_time_windows_touching_edges_do_not_overlap(self):
		# A return leg that starts exactly when the lock releases is allowed.
		self.assertFalse(_time_windows_overlap("08:00:00", "14:00:00", "14:00:00", "16:00:00"))

	def test_time_windows_disjoint_do_not_overlap(self):
		self.assertFalse(_time_windows_overlap("08:00:00", "14:00:00", "15:00:00", "16:00:00"))

	def test_windows_overlap_requires_both_date_and_time(self):
		lock = _shipment("A", retention=1)
		# Same time window but a different day -> no overlap.
		other_other_day = _shipment("B", from_date=NEXT_DAY, to_date=NEXT_DAY,
									 start="11:30:00", end="12:30:00")
		self.assertFalse(_windows_overlap(lock, other_other_day))
		# Same day, overlapping time -> overlap.
		other_same_day = _shipment("B", start="11:30:00", end="12:30:00")
		self.assertTrue(_windows_overlap(lock, other_same_day))


class TestRetentionConflictDetection(FrappeTestCase):
	"""TR4-7: which co-assigned shipment set trips the STANDBY lock."""

	def test_retention_blocks_overlapping_adhoc_drop(self):
		# The acceptance-criteria scenario: a fingerprint retention lock (08:00-14:00)
		# and a grocery run at 11:30 land on the same vehicle.
		fingerprint = _shipment("SHIP-FP", retention=1, source="TRQ-FINGERPRINT")
		grocery = _shipment("SHIP-GROC", start="11:30:00", end="12:30:00")
		shipment_map = {"SHIP-FP": fingerprint, "SHIP-GROC": grocery}

		conflict = _detect_retention_conflict({"SHIP-FP", "SHIP-GROC"}, shipment_map)
		self.assertIsNotNone(conflict)
		self.assertEqual(conflict.name, "SHIP-FP")

	def test_no_conflict_when_times_are_disjoint(self):
		fingerprint = _shipment("SHIP-FP", retention=1)
		evening = _shipment("SHIP-EVE", start="15:00:00", end="18:00:00")
		shipment_map = {"SHIP-FP": fingerprint, "SHIP-EVE": evening}
		self.assertIsNone(_detect_retention_conflict({"SHIP-FP", "SHIP-EVE"}, shipment_map))

	def test_no_conflict_when_dates_are_disjoint(self):
		fingerprint = _shipment("SHIP-FP", retention=1)
		next_week = _shipment("SHIP-NW", from_date="2026-07-27", to_date="2026-07-27",
							   start="11:30:00", end="12:30:00")
		shipment_map = {"SHIP-FP": fingerprint, "SHIP-NW": next_week}
		self.assertIsNone(_detect_retention_conflict({"SHIP-FP", "SHIP-NW"}, shipment_map))

	def test_lone_retention_card_never_conflicts_with_itself(self):
		# A single retention card (even placed on two rows) collapses to one name.
		fingerprint = _shipment("SHIP-FP", retention=1)
		self.assertIsNone(_detect_retention_conflict({"SHIP-FP"}, {"SHIP-FP": fingerprint}))

	def test_two_non_retention_overlaps_do_not_trip_the_lock(self):
		# Without a retention flag there is no STANDBY hold to enforce here.
		a = _shipment("SHIP-A", start="08:00:00", end="14:00:00")
		b = _shipment("SHIP-B", start="11:30:00", end="12:30:00")
		self.assertIsNone(_detect_retention_conflict({"SHIP-A", "SHIP-B"}, {"SHIP-A": a, "SHIP-B": b}))

	def test_two_overlapping_retention_trips_conflict(self):
		# "Any overlapping drop" is blocked, including another retention trip.
		a = _shipment("SHIP-A", retention=1)
		b = _shipment("SHIP-B", retention=1, start="11:30:00", end="12:30:00")
		conflict = _detect_retention_conflict({"SHIP-A", "SHIP-B"}, {"SHIP-A": a, "SHIP-B": b})
		self.assertIsNotNone(conflict)


class TestLockUntilLabel(FrappeTestCase):
	def test_formats_afternoon_time_as_12_hour(self):
		self.assertEqual(_format_lock_until("14:00:00"), "02:00 PM")

	def test_formats_morning_time_as_12_hour(self):
		self.assertEqual(_format_lock_until("08:30:00"), "08:30 AM")

	def test_blank_time_yields_empty_label(self):
		self.assertEqual(_format_lock_until(None), "")


class TestRoutePlanRetentionSave(FrappeTestCase):
	"""TR4-7: the before-save hook rejects the drop end to end on the plan."""

	def _make_shipment(self, retention, *, start, end, source=None,
					   from_date=DAY, to_date=DAY):
		"""Insert a minimal Transportation Shipment, bypassing Trip Request rules."""
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = "Unassigned"
		doc.trip_direction = "Outward"
		doc.routing_type_badge = "Direct"
		doc.requires_vehicle_retention = retention
		doc.from_date = from_date
		doc.to_date = to_date
		doc.start_time = start
		doc.end_time = end
		if source:
			doc.source_doctype = "Trip Request"
			doc.source_docname = source
		doc.flags.ignore_validate = True
		# source_docname is a Dynamic Link to a Trip Request that this unit test
		# does not provision, so skip link existence checks for the fixture.
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def _make_plan(self, rows):
		"""Build (not insert) a Route Plan with the given assignment rows.

		Vehicle links and mandatory checks are skipped so the retention hook — which
		runs first in the controller validate() — is what the save exercises.
		"""
		doc = frappe.new_doc("Route Plan")
		doc.title = frappe.generate_hash("RP-TEST", 8)
		doc.status = "Draft"
		doc.effective_from = DAY
		for row in rows:
			doc.append("assignments", row)
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		return doc

	def test_save_blocks_overlapping_drop_on_retained_vehicle(self):
		lock = self._make_shipment(1, start="08:00:00", end="14:00:00", source="TRQ-FINGERPRINT")
		grocery = self._make_shipment(0, start="11:30:00", end="12:30:00")

		plan = self._make_plan([
			{"card_id": f"TSHIP-{lock}", "transportation_shipment": lock,
			 "vehicle": "VHL-0002", "direction": "OUTBOUND"},
			{"card_id": f"TSHIP-{grocery}", "transportation_shipment": grocery,
			 "vehicle": "VHL-0002", "direction": "OUTBOUND"},
		])

		with self.assertRaises(frappe.ValidationError) as cm:
			plan.insert(ignore_permissions=True)
		message = str(cm.exception)
		self.assertIn("VHL-0002", message)
		self.assertIn("locked on STANDBY", message)
		self.assertIn("TRQ-FINGERPRINT", message)
		self.assertIn("02:00 PM", message)

	def test_save_allows_non_overlapping_drop(self):
		lock = self._make_shipment(1, start="08:00:00", end="14:00:00", source="TRQ-FINGERPRINT")
		evening = self._make_shipment(0, start="15:00:00", end="18:00:00")

		plan = self._make_plan([
			{"card_id": f"TSHIP-{lock}", "transportation_shipment": lock,
			 "vehicle": "VHL-0002", "direction": "OUTBOUND"},
			{"card_id": f"TSHIP-{evening}", "transportation_shipment": evening,
			 "vehicle": "VHL-0002", "direction": "OUTBOUND"},
		])
		# No overlap -> save succeeds without raising.
		plan.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Route Plan", plan.name))

	def test_save_allows_overlap_on_different_vehicles(self):
		lock = self._make_shipment(1, start="08:00:00", end="14:00:00", source="TRQ-FINGERPRINT")
		grocery = self._make_shipment(0, start="11:30:00", end="12:30:00")

		plan = self._make_plan([
			{"card_id": f"TSHIP-{lock}", "transportation_shipment": lock,
			 "vehicle": "VHL-0002", "direction": "OUTBOUND"},
			{"card_id": f"TSHIP-{grocery}", "transportation_shipment": grocery,
			 "vehicle": "VHL-0009", "direction": "OUTBOUND"},
		])
		# The grocery run overlaps in time but sits on a different vehicle.
		plan.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Route Plan", plan.name))
