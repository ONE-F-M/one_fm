# Copyright (c) 2026, ONE FM and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


def make_shipment(**kwargs):
	"""Build an in-memory Transportation Shipment for controller-logic tests.

	The document is intentionally not inserted, so the pure population logic can
	be exercised without provisioning Employee/Site/Accommodation fixtures.
	"""
	doc = frappe.new_doc("Transportation Shipment")
	doc.update(kwargs)
	return doc


class TestTransportationShipment(FrappeTestCase):
	def test_default_status_is_unassigned(self):
		doc = make_shipment()
		doc.set_default_status()
		self.assertEqual(doc.status, "Unassigned")

	def test_default_status_not_overwritten(self):
		doc = make_shipment(status="Assigned")
		doc.set_default_status()
		self.assertEqual(doc.status, "Assigned")

	def test_headcount_matches_employee_rows(self):
		doc = make_shipment()
		for emp in ("EMP-A", "EMP-B", "EMP-C"):
			doc.append("transportation_shipment_employee", {"employee_id": emp})
		doc.calculate_headcount()
		self.assertEqual(doc.headcount, 3)

	def test_direct_copies_parent_accommodation_and_stop(self):
		doc = make_shipment(
			routing_type_badge="Direct",
			accommodation="ACC-001",
			stop_location="LOC-001",
		)
		doc.append("transportation_shipment_employee", {"employee_id": "EMP-A"})
		doc.append("transportation_shipment_employee", {"employee_id": "EMP-B"})
		doc.apply_routing_type()
		for row in doc.transportation_shipment_employee:
			self.assertEqual(row.accommodation, "ACC-001")
			self.assertEqual(row.stop_location, "LOC-001")

	def test_osm_and_olm_bind_header_stop_location(self):
		for routing in ("OSM", "OLM"):
			doc = make_shipment(routing_type_badge=routing, stop_location="LOC-DEST")
			doc.append("transportation_shipment_employee", {"employee_id": "EMP-A"})
			doc.apply_routing_type()
			self.assertEqual(
				doc.transportation_shipment_employee[0].stop_location,
				"LOC-DEST",
				msg=f"{routing} must bind rows to the header stop location",
			)

	def test_trip_request_source_requires_stop_location(self):
		doc = make_shipment(source_doctype="Trip Request")
		# No stop_location and no source_docname to fall back on.
		with self.assertRaises(frappe.ValidationError):
			doc.apply_trip_request_rules()

	def test_trip_request_source_clears_operations_site(self):
		doc = make_shipment(
			source_doctype="Trip Request",
			operations_site="SITE-001",
			stop_location="LOC-001",
		)
		doc.apply_trip_request_rules()
		self.assertFalse(doc.operations_site)

	def test_osm_keeps_distinct_row_stop(self):
		# OSM (One Site Many Locations): each rider keeps their own distinct stop
		# location; it must not be overwritten by the header.
		doc = make_shipment(routing_type_badge="OSM", stop_location="HEADER-STOP")
		doc.append(
			"transportation_shipment_employee",
			{"employee_id": "EMP-A", "stop_location": "ROW-STOP"},
		)
		doc.apply_routing_type()
		self.assertEqual(doc.transportation_shipment_employee[0].stop_location, "ROW-STOP")

	def test_olm_binds_all_rows_to_header_stop(self):
		# OLM (One Location Many Sites): every rider is bound to the single header
		# stop location even if the row carried a different one.
		doc = make_shipment(routing_type_badge="OLM", stop_location="HEADER-STOP")
		doc.append(
			"transportation_shipment_employee",
			{"employee_id": "EMP-A", "stop_location": "OTHER-STOP", "operation_site": "SITE-A"},
		)
		doc.apply_routing_type()
		row = doc.transportation_shipment_employee[0]
		self.assertEqual(row.stop_location, "HEADER-STOP")   # bound to header
		self.assertEqual(row.operation_site, "SITE-A")        # distinct site kept


class TestShipmentGenerator(FrappeTestCase):
	def test_minute_of_day(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import _minute_of_day

		self.assertEqual(_minute_of_day("06:30:00"), 6 * 3600 + 30 * 60)
		self.assertIsNone(_minute_of_day(None))

	def test_generation_key_shape(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import _generation_key

		demand = {
			"accommodation": "ACC-1",
			"group_token": "SHIFT-1",
			"stop_location": "LOC-1",
			"routing": "OSM",
		}
		key, pair = _generation_key(demand, "Outward")
		self.assertTrue(key.startswith("OPS|"))
		self.assertTrue(key.endswith("|Outward"))
		# The pair group is the key without the direction suffix and is shared
		# by the Outbound and Return records of the same demand.
		key_ret, pair_ret = _generation_key(demand, "Return")
		self.assertEqual(pair, pair_ret)
		self.assertNotEqual(key, key_ret)

	def test_attach_return_rosters_matches_finishing_shift(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import _attach_return_rosters

		# Two demands at the same stop/accommodation, different shifts. The one
		# starting at 14:00 should pick up the roster of the shift ending 14:00.
		morning = {
			"acc_name": "Camp A", "stop_location": "LOC-1", "group_token": "MORNING",
			"start_time": "06:00:00", "end_time": "14:00:00", "employees": [{"id": "M1"}],
		}
		evening = {
			"acc_name": "Camp A", "stop_location": "LOC-1", "group_token": "EVENING",
			"start_time": "14:00:00", "end_time": "22:00:00", "employees": [{"id": "E1"}],
		}
		_attach_return_rosters([morning, evening])
		# Evening outbound starts when morning ends -> return riders are the morning crew.
		self.assertEqual([e["id"] for e in evening["return_employees"]], ["M1"])


class TestTripRequestSplit(FrappeTestCase):
	"""MA 5 - 4: fragment a multi-camp Trip Request into per-camp demand cards."""

	def _make_trip_request(self, camp_headcounts):
		"""Build an in-memory Trip Request with passengers spread across camps.

		camp_headcounts: {camp_name: headcount}. Not inserted — used to exercise
		the pure clustering logic without provisioning Accommodation/Employee.
		"""
		doc = frappe.new_doc("Trip Request")
		for camp, count in camp_headcounts.items():
			for i in range(count):
				doc.append("transport_request_passenger", {
					"employee_id": f"{camp}-EMP-{i}",
					"employee_name": f"{camp} Worker {i}",
					"accommodation_camp": camp,
				})
		return doc

	def test_group_passengers_clusters_strictly_by_camp(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			_group_passengers_by_camp,
		)

		# 3 workers from Mahboula, 2 from Mangaf (the acceptance-criteria example).
		trq = self._make_trip_request({"Mahboula Camp": 3, "Mangaf Camp": 2})
		groups = _group_passengers_by_camp(trq)

		self.assertEqual(set(groups.keys()), {"Mahboula Camp", "Mangaf Camp"})
		self.assertEqual(len(groups["Mahboula Camp"]), 3)
		self.assertEqual(len(groups["Mangaf Camp"]), 2)

	def test_group_passengers_skips_rows_without_camp(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			_group_passengers_by_camp,
		)

		trq = self._make_trip_request({"Mahboula Camp": 2})
		# A passenger with no camp has no physical origin to cluster on.
		trq.append("transport_request_passenger", {"employee_id": "NO-CAMP", "employee_name": "X"})
		groups = _group_passengers_by_camp(trq)

		self.assertEqual(list(groups.keys()), ["Mahboula Camp"])
		self.assertEqual(len(groups["Mahboula Camp"]), 2)

	def test_generation_key_pairs_directions_per_camp(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			_trip_request_generation_key,
		)

		out_key, out_pair = _trip_request_generation_key("TRQ-001", "Mahboula Camp", "Outward")
		ret_key, ret_pair = _trip_request_generation_key("TRQ-001", "Mahboula Camp", "Return")

		self.assertTrue(out_key.startswith("TRQ|"))
		self.assertTrue(out_key.endswith("|Outward"))
		self.assertTrue(ret_key.endswith("|Return"))
		# Outward and Return of the same camp share a pair group but not a key.
		self.assertEqual(out_pair, ret_pair)
		self.assertNotEqual(out_key, ret_key)

	def test_different_camps_get_distinct_pair_groups(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			_trip_request_generation_key,
		)

		_, mahboula_pair = _trip_request_generation_key("TRQ-001", "Mahboula Camp", "Outward")
		_, mangaf_pair = _trip_request_generation_key("TRQ-001", "Mangaf Camp", "Outward")
		self.assertNotEqual(mahboula_pair, mangaf_pair)


class TestRetentionCardConversion(FrappeTestCase):
	"""MA-10: Vehicle Retention decides one combined vs two split cards per camp."""

	def test_retention_on_collapses_to_single_outward(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			_card_directions,
		)

		# Retention ON → exactly one combined Outward card (drop-off + return leg).
		self.assertEqual(_card_directions(1), ("Outward",))

	def test_retention_off_keeps_outward_and_return(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			_card_directions,
		)

		# Retention OFF → two separate master cards, Outward and Return.
		self.assertEqual(_card_directions(0), ("Outward", "Return"))


class SchedulerEntryPointTestCase(FrappeTestCase):
	"""A test case for the functions the scheduler calls, with their commit muted.

	`generate_transportation_shipments` and `deactivate_expired_shipments` are
	background jobs, so committing is right for them. Called from a test, that commit
	ends the transaction FrappeTestCase wraps every test in, and every fixture inserted
	afterwards is written to the database for real.
	"""

	def setUp(self):
		super().setUp()
		muted = patch.object(frappe.db, "commit")
		muted.start()
		self.addCleanup(muted.stop)


class TestNonFleetBypass(SchedulerEntryPointTestCase):
	"""Story 6: Taxi / Subcontractor Rental requests bypass the scheduling canvas.

	A Trip Request whose Transportation Method is anything other than "Company
	Fleet" must never materialize Transportation Shipment cards, so the canvas
	sidebar stays focused on company assets. Enforcement lives at submission time
	in generate_shipments_from_trip_request, before any card is built.
	"""

	def _make_non_fleet_request(self, method):
		"""Build a named, in-memory multi-camp Trip Request for the given method.

		Passengers carry an accommodation_camp so that, if the non-fleet bypass
		ever regressed, the generator would actually attempt to split the request
		into camp cards — making a created/errored count the proof the skip works.
		"""
		doc = frappe.new_doc("Trip Request")
		doc.name = f"TRQ-NONFLEET-{method.replace(' ', '-')}"
		doc.transportation_method = method
		for i in range(3):
			doc.append("transport_request_passenger", {
				"employee_id": f"EMP-{i}",
				"employee_name": f"Worker {i}",
				"accommodation_camp": "Mahboula Camp",
			})
		return doc

	def test_taxi_request_generates_no_shipments(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			generate_shipments_from_trip_request,
		)

		trq = self._make_non_fleet_request("Taxi")
		summary = generate_shipments_from_trip_request(trq)

		self.assertEqual(summary["created"], 0)
		self.assertEqual(summary["updated"], 0)
		self.assertEqual(summary["errors"], 0)
		self.assertFalse(
			frappe.get_all("Transportation Shipment", filters={"source_docname": trq.name}),
			msg="A Taxi Trip Request must not leave any shipment cards on the canvas",
		)

	def test_subcontractor_rental_request_generates_no_shipments(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			generate_shipments_from_trip_request,
		)

		trq = self._make_non_fleet_request("Subcontractor Rental")
		summary = generate_shipments_from_trip_request(trq)

		self.assertEqual(summary["created"], 0)
		self.assertEqual(summary["updated"], 0)
		self.assertEqual(summary["errors"], 0)
		self.assertFalse(
			frappe.get_all("Transportation Shipment", filters={"source_docname": trq.name}),
			msg="A Subcontractor Rental Trip Request must not leave any shipment cards on the canvas",
		)


class TestShipmentExpiry(SchedulerEntryPointTestCase):
	"""TR 3 - 9: past-to_date Unassigned cards are flagged Inactive by the engine."""

	def _make_shipment(self, status, to_date):
		"""Insert a minimal Trip Request sourced shipment for expiry testing."""
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = status
		doc.trip_direction = "Outward"
		doc.routing_type_badge = "Direct"
		doc.stop_location = None
		doc.to_date = to_date
		# Bypass the Trip Request controller rules — this is a standalone fixture
		# with no source document to pull a stop location from.
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_expired_unassigned_card_becomes_inactive(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			deactivate_expired_shipments,
		)

		name = self._make_shipment("Unassigned", "2026-01-01")
		deactivate_expired_shipments(as_of="2026-07-19")
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "status"), "Inactive"
		)

	def test_card_active_on_its_to_date(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			deactivate_expired_shipments,
		)

		# The card stays active on its own to_date; it only expires the day after.
		name = self._make_shipment("Unassigned", "2026-07-19")
		deactivate_expired_shipments(as_of="2026-07-19")
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "status"), "Unassigned"
		)

	def test_assigned_card_past_to_date_becomes_inactive(self):
		# TR-8: an Assigned card whose to_date has passed now expires too, so the
		# block leaves the canvas after its To Date (TR 3-9 left Assigned alone).
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			deactivate_expired_shipments,
		)

		name = self._make_shipment("Assigned", "2026-07-05")
		deactivate_expired_shipments(as_of="2026-07-19")
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "status"), "Inactive"
		)

	def test_assigned_card_before_to_date_stays_assigned(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			deactivate_expired_shipments,
		)

		name = self._make_shipment("Assigned", "2026-07-25")
		deactivate_expired_shipments(as_of="2026-07-19")
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "status"), "Assigned"
		)

	def test_assigned_card_without_to_date_never_expires(self):
		# A continuous (standing) Assigned card carries no to_date — AC2.
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			deactivate_expired_shipments,
		)

		name = self._make_shipment("Assigned", None)
		deactivate_expired_shipments(as_of="2026-07-19")
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "status"), "Assigned"
		)

	def _assign_to_plan(self, shipment, *, start_iso, end_iso):
		"""Place a shipment on a throwaway Route Plan with a lock window."""
		doc = frappe.new_doc("Route Plan")
		doc.title = frappe.generate_hash("RP-EXP", 8)
		doc.status = "Draft"
		doc.effective_from = "2026-07-01"
		doc.append("assignments", {
			"card_id": f"TSHIP-{shipment}", "transportation_shipment": shipment,
			"vehicle": "VHL-0005", "direction": "OUTBOUND",
			"start_time": start_iso, "end_time": end_iso,
		})
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_assigned_expires_on_edited_lock_end_not_to_date(self):
		# Dispatcher SHORTENED the lock: to_date is still in the future, but the
		# assignment's end_time date has passed -> expire on the lock end (TR-8).
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			deactivate_expired_shipments,
		)

		name = self._make_shipment("Assigned", "2026-07-30")
		self._assign_to_plan(name, start_iso="2026-07-01T06:00:00Z", end_iso="2026-07-05T07:00:00Z")
		deactivate_expired_shipments(as_of="2026-07-19")
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "status"), "Inactive"
		)

	def test_assigned_survives_when_lock_end_extended_past_to_date(self):
		# Dispatcher EXTENDED the lock: to_date has passed, but the assignment's
		# end_time date is still in the future -> the card stays Assigned.
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			deactivate_expired_shipments,
		)

		name = self._make_shipment("Assigned", "2026-07-05")
		self._assign_to_plan(name, start_iso="2026-07-01T06:00:00Z", end_iso="2026-07-25T07:00:00Z")
		deactivate_expired_shipments(as_of="2026-07-19")
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "status"), "Assigned"
		)

	def test_assigned_no_to_date_multiday_lock_expires(self):
		# The TS-0725 case: a shipment with NO to_date but a bounded multi-day
		# assignment lock whose end date has passed must expire — the assignment
		# lock end is authoritative, not the (absent) shipment to_date.
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			deactivate_expired_shipments,
		)

		name = self._make_shipment("Assigned", None)
		self._assign_to_plan(name, start_iso="2026-07-17T05:45:00Z", end_iso="2026-07-19T07:00:00Z")
		deactivate_expired_shipments(as_of="2026-07-20")
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "status"), "Inactive"
		)

	def test_assigned_no_to_date_single_day_lock_never_expires(self):
		# A single-day span with no to_date is an open-ended/continuous run — it
		# stays Assigned forever even though its lock date is in the past (AC2).
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			deactivate_expired_shipments,
		)

		name = self._make_shipment("Assigned", None)
		self._assign_to_plan(name, start_iso="2026-07-10T06:00:00Z", end_iso="2026-07-10T07:00:00Z")
		deactivate_expired_shipments(as_of="2026-07-20")
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "status"), "Assigned"
		)

	def test_standing_card_without_to_date_is_untouched(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			deactivate_expired_shipments,
		)

		# Standing Operations Shift cards carry no to_date and never expire.
		name = self._make_shipment("Unassigned", None)
		deactivate_expired_shipments(as_of="2026-07-19")
		self.assertEqual(
			frappe.db.get_value("Transportation Shipment", name, "status"), "Unassigned"
		)
