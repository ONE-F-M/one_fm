# Copyright (c) 2026, ONE FM and contributors
# See license.txt

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
