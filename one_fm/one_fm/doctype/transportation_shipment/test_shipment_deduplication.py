# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002308: one set of cards per shift requirement.

A site configured under both One Site Many Locations and One Location Many Sites had
both arrangements generate, so the same employees appeared on two sets of cards at two
different stops - the board showing one shift's demand twice, with different names and
different headcounts.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
	_generation_key,
	build_demand_descriptors,
)
from one_fm.one_fm.page.transportation_schedule.transportation_schedule import get_coords


class TestOneArrangementPerShift(FrappeTestCase):
	"""AC1: OSM and OLM never both place the same shift.

	No site on this instance is configured under both today, so the pair is built here.
	Without the fix both branches run and this class fails - which is the point of it.
	"""

	def setUp(self):
		self.employees = frappe.get_all(
			"Employee", filters={"status": "Active"}, fields=["name"], limit=4, pluck="name"
		)
		if not self.employees:
			self.skipTest("no active employees on this site")

		self.accommodation = _first_with_coords("Accommodation")
		self.stop_a = _first_with_coords("Location")
		self.stop_b = _first_with_coords("Location", exclude=self.stop_a)
		if not self.accommodation or not self.stop_a or not self.stop_b:
			self.skipTest("this site has no geocoded Accommodation and two Locations")

		self.shift = frappe.db.get_value(
			"Operations Shift", {"status": "Active", "site": ["is", "set"]}, ["name", "site"], as_dict=True
		)
		if not self.shift:
			self.skipTest("no active Operations Shift with a site")

		_clear_stop_configuration(self.shift.site)
		self._configure_osm()
		self._configure_olm()

	def _configure_osm(self):
		"""The site picks its own staff up at stop A."""
		doc = frappe.new_doc("Site Transport Stop Location")
		doc.site_transport_stop_location_name = "WI-002308 OSM"
		doc.site_arrangement = "One Site Many Locations"
		doc.site = self.shift.site
		doc.append("transport_stop_locations", {"location": self.stop_a})
		doc.insert(ignore_permissions=True)

	def _configure_olm(self):
		"""And stop B is a shared stop that claims the same site."""
		doc = frappe.new_doc("Site Transport Stop Location")
		doc.site_transport_stop_location_name = "WI-002308 OLM"
		doc.site_arrangement = "One Location Many Sites"
		doc.transport_stop_location = self.stop_b
		doc.append("sites", {"sites": self.shift.site})
		doc.insert(ignore_permissions=True)

	def _demands(self):
		nested = {
			"Camp": {"lookup_id": self.accommodation, "shifts": {self.shift.name: self.employees}}
		}
		return build_demand_descriptors(nested)

	def test_only_one_arrangement_places_the_shift(self):
		routings = {d["routing"] for d in self._demands()}

		self.assertEqual(routings, {"OSM"}, f"two arrangements generated: {routings}")

	def test_nobody_is_carried_on_two_cards(self):
		"""The symptom the dispatcher sees: the same person counted twice, at two stops."""
		seen = set()
		for demand in self._demands():
			for emp in demand["employees"]:
				self.assertNotIn(emp["id"], seen, f"{emp['id']} is on two cards")
				seen.add(emp["id"])

	def test_the_shift_is_placed_at_the_site_specific_stop(self):
		"""One Site Many Locations is the more specific statement of where its staff
		are picked up, so it is the one that wins."""
		stops = {d["stop_location"] for d in self._demands()}

		self.assertEqual(stops, {self.stop_a})

	def test_an_olm_only_site_still_generates(self):
		"""The fix must not switch OLM off - only stop it doubling up with OSM."""
		_clear_stop_configuration(self.shift.site)
		self._configure_olm()

		demands = self._demands()
		self.assertEqual({d["routing"] for d in demands}, {"OLM"})
		self.assertEqual({d["stop_location"] for d in demands}, {self.stop_b})


class TestGenerationIsIdempotent(FrappeTestCase):
	"""AC2: running generation again re-uses the record instead of adding another."""

	def test_the_key_is_stable_for_the_same_demand(self):
		demand = {
			"accommodation": "ACC-01",
			"group_token": "SHIFT-01",
			"stop_location": "LOC-01",
			"routing": "OSM",
		}
		self.assertEqual(_generation_key(demand, "Outward"), _generation_key(demand, "Outward"))

	def test_the_two_directions_do_not_collide(self):
		"""They share a pair_group but must not share a key, or one overwrites the other."""
		demand = {
			"accommodation": "ACC-01",
			"group_token": "SHIFT-01",
			"stop_location": "LOC-01",
			"routing": "OSM",
		}
		out_key, out_pair = _generation_key(demand, "Outward")
		ret_key, ret_pair = _generation_key(demand, "Return")

		self.assertNotEqual(out_key, ret_key)
		self.assertEqual(out_pair, ret_pair)

	def test_the_key_field_is_long_enough_to_hold_one(self):
		"""Truncation is how Outward and Return collided before - the direction is the
		last segment, so a short field drops exactly the part that distinguishes them."""
		for fieldname in ("generation_key", "pair_group"):
			field = frappe.get_meta("Transportation Shipment").get_field(fieldname)
			self.assertGreaterEqual(int(field.length or 140), 500, fieldname)


def _first_with_coords(doctype, exclude=None):
	"""A record the generator will accept - it skips anything it cannot place on a map."""
	for row in frappe.get_all(doctype, fields=["name"], limit=60):
		if row.name != exclude and get_coords(doctype, row.name):
			return row.name
	return None


def _clear_stop_configuration(site):
	"""Take the site out of every existing stop arrangement, so the test starts from a
	site configured exactly the way the test configures it. Rolled back with the case."""
	for name in frappe.get_all(
		"Site Transport Stop Location", filters={"site": site}, pluck="name"
	):
		frappe.delete_doc("Site Transport Stop Location", name, ignore_permissions=True, force=True)

	for row in frappe.get_all(
		"Location To Site Mapping",
		filters={"parenttype": "Site Transport Stop Location", "sites": site},
		fields=["parent"],
	):
		if frappe.db.exists("Site Transport Stop Location", row.parent):
			frappe.delete_doc(
				"Site Transport Stop Location", row.parent, ignore_permissions=True, force=True
			)
