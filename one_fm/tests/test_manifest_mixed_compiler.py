# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002072: what the compiler writes onto a manifest for a merged trip."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	_inherit_trip_identity,
)


def _row(**kwargs):
	base = {"stop_name": "", "pickup_accommodation": "", "employee_action": "", "stop_sequence": 0}
	base.update(kwargs)
	return frappe._dict(base)


def _manifest(trip_direction, rows):
	doc = frappe.new_doc("Transportation Manifest")
	doc.trip_direction = trip_direction
	doc.transportation_manifest_details = rows
	return doc


class TestManifestHeaderSchema(FrappeTestCase):
	def test_the_header_can_hold_the_run_direction(self):
		field = frappe.get_meta("Transportation Manifest").get_field("trip_direction")

		self.assertIsNotNone(field)
		self.assertIn("Mixed", field.options.split("\n"))

	def test_the_header_can_hold_the_shared_group_key(self):
		self.assertIsNotNone(frappe.get_meta("Transportation Manifest").get_field("trip_group"))

	def test_a_passenger_row_keeps_its_source_card(self):
		# Second criterion: audit traceability back to the shift request.
		field = frappe.get_meta("Transportation Manifest Details").get_field("transportation_shipment")

		self.assertIsNotNone(field)
		self.assertEqual(field.options, "Transportation Shipment")


class TestTripIdentityInheritance(FrappeTestCase):
	def _assignment(self, direction, trip_group=None):
		return frappe._dict(direction=direction, trip_group=trip_group)

	def test_a_merged_run_makes_the_manifest_mixed(self):
		doc = frappe.new_doc("Transportation Manifest")

		changed = _inherit_trip_identity(doc, [self._assignment("MIXED", "MIX-abc")])

		self.assertTrue(changed)
		self.assertEqual(doc.trip_direction, "Mixed")
		self.assertEqual(doc.trip_group, "MIX-abc")

	def test_the_group_key_is_copied_from_the_plan(self):
		doc = frappe.new_doc("Transportation Manifest")

		_inherit_trip_identity(doc, [
			self._assignment("MIXED", "MIX-xyz"),
			self._assignment("MIXED", "MIX-xyz"),
		])

		self.assertEqual(doc.trip_group, "MIX-xyz")

	def test_one_merged_row_is_enough_to_make_the_run_mixed(self):
		doc = frappe.new_doc("Transportation Manifest")

		_inherit_trip_identity(doc, [
			self._assignment("OUTBOUND"),
			self._assignment("MIXED", "MIX-1"),
		])

		self.assertEqual(doc.trip_direction, "Mixed")
		self.assertEqual(doc.trip_group, "MIX-1")

	def test_an_outbound_only_run_stays_outward(self):
		doc = frappe.new_doc("Transportation Manifest")

		_inherit_trip_identity(doc, [self._assignment("OUTBOUND")])

		self.assertEqual(doc.trip_direction, "Outward")
		self.assertFalse(doc.trip_group)

	def test_a_return_only_run_stays_return(self):
		doc = frappe.new_doc("Transportation Manifest")

		_inherit_trip_identity(doc, [self._assignment("RETURN")])

		self.assertEqual(doc.trip_direction, "Return")

	def test_a_run_with_no_directions_is_left_alone(self):
		doc = frappe.new_doc("Transportation Manifest")

		self.assertFalse(_inherit_trip_identity(doc, []))
		self.assertFalse(doc.get("trip_direction"))

	def test_nothing_is_reported_changed_on_a_second_pass(self):
		doc = frappe.new_doc("Transportation Manifest")
		rows = [self._assignment("MIXED", "MIX-1")]

		self.assertTrue(_inherit_trip_identity(doc, rows))
		self.assertFalse(_inherit_trip_identity(doc, rows))


class TestStopNumberingForAMergedRun(FrappeTestCase):
	def _sequences(self, rows, trip_direction="Mixed"):
		doc = _manifest(trip_direction, rows)
		doc.populate_stop_sequence_and_pickup_accommodation()
		return [r.stop_sequence for r in rows]

	def test_a_drop_and_a_collect_at_one_stop_are_two_entries(self):
		# Fourth criterion: simultaneous drop-off and pick-up keep distinct sequences.
		rows = [
			_row(stop_name="Site A", employee_action="Dropping Off"),
			_row(stop_name="Site A", employee_action="Boarding"),
		]

		self.assertEqual(self._sequences(rows), [1, 2])

	def test_a_revisited_stop_takes_a_later_number(self):
		# Fifth criterion: morning drop-off 1, evening pickup 3.
		rows = [
			_row(stop_name="Site A", employee_action="Dropping Off"),
			_row(stop_name="Site B", employee_action="Dropping Off"),
			_row(stop_name="Site A", employee_action="Boarding"),
		]

		self.assertEqual(self._sequences(rows), [1, 2, 3])

	def test_everyone_at_one_visit_shares_its_number(self):
		rows = [
			_row(stop_name="Site A", employee_action="Dropping Off"),
			_row(stop_name="Site A", employee_action="Dropping Off"),
			_row(stop_name="Site A", employee_action="Boarding"),
		]

		self.assertEqual(self._sequences(rows), [1, 1, 2])

	def test_the_numbers_are_contiguous_from_one(self):
		rows = [
			_row(stop_name="A", employee_action="Dropping Off"),
			_row(stop_name="B", employee_action="Boarding"),
			_row(stop_name="C", employee_action="Dropping Off"),
		]

		self.assertEqual(self._sequences(rows), [1, 2, 3])

	def test_a_row_with_no_place_stays_at_the_head(self):
		rows = [_row(employee_action="Boarding")]

		self.assertEqual(self._sequences(rows), [1])

	def test_a_camp_stands_in_when_there_is_no_stop_name(self):
		rows = [
			_row(pickup_accommodation="Camp 1", employee_action="Boarding"),
			_row(pickup_accommodation="Camp 2", employee_action="Boarding"),
		]

		self.assertEqual(self._sequences(rows), [1, 2])

	def test_a_non_merged_manifest_keeps_the_per_camp_rule(self):
		# The per-camp banners and the sequential attendance unlock depend on it, so the
		# visit rule must not leak into an ordinary run.
		rows = [
			_row(pickup_accommodation="Camp 1", employee_action="Boarding"),
			_row(pickup_accommodation="Camp 1", employee_action="Dropping Off"),
		]

		self.assertEqual(self._sequences(rows, trip_direction="Outward"), [1, 1])

	def test_the_same_rows_number_differently_once_the_run_is_merged(self):
		def rows():
			return [
				_row(pickup_accommodation="Camp 1", employee_action="Boarding"),
				_row(pickup_accommodation="Camp 1", employee_action="Dropping Off"),
			]

		self.assertEqual(self._sequences(rows(), trip_direction="Outward"), [1, 1])
		self.assertEqual(self._sequences(rows(), trip_direction="Mixed"), [1, 2])
