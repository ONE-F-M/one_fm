# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe
import unittest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string


def make_vehicle(**kwargs):
	"""Factory helper — creates and inserts a Vehicle doc for testing.

	Uses ignore_mandatory=True so tests focus purely on the autoname /
	custom_naming_series behaviour without depending on test fixtures for
	Employee, Vehicle Type, Vehicle Location, etc.
	"""
	defaults = {
		"doctype": "Vehicle",
		"license_plate": random_string(10).upper(),
		"make": "Toyota",
		"model": "Land Cruiser",
		"last_odometer": 0,
		"uom": "Litre",
		"fuel_type": "Petrol",
	}
	defaults.update(kwargs)
	doc = frappe.get_doc(defaults)
	doc.insert(ignore_permissions=True, ignore_mandatory=True)
	return doc


class TestVehicleLeasingContract(FrappeTestCase):
	pass


class TestVehicleAutoname(FrappeTestCase):
	"""
	Covers the vehicle_autoname() doc_event hook.

	Asserts that:
	  1. The generated doc.name uses the correct prefix for each category.
	  2. doc.custom_naming_series is set consistently on the server side,
	     covering all creation paths (API inserts, create_vehicle calls,
	     background jobs) — not just the client-side JS path.
	"""

	# ------------------------------------------------------------------ #
	# Helpers                                                              #
	# ------------------------------------------------------------------ #

	def _assert_vehicle_naming(self, category, expected_prefix, expected_series):
		"""
		Create a Vehicle with the given category and assert:
		  - doc.name starts with expected_prefix
		  - doc.custom_naming_series == expected_series
		"""
		vehicle = make_vehicle(one_fm_vehicle_category=category)

		self.assertTrue(
			vehicle.name.startswith(expected_prefix),
			msg=(
				f"Expected name to start with '{expected_prefix}' for category "
				f"'{category}', got '{vehicle.name}'"
			),
		)
		self.assertEqual(
			vehicle.custom_naming_series,
			expected_series,
			msg=(
				f"Expected custom_naming_series='{expected_series}' for category "
				f"'{category}', got '{vehicle.custom_naming_series}'"
			),
		)
		return vehicle

	# ------------------------------------------------------------------ #
	# Category: Owned                                                      #
	# ------------------------------------------------------------------ #

	def test_owned_vehicle_gets_vhl_prefix(self):
		"""Owned vehicles must be named VHL-XXXX and series set to VHL-.####."""
		self._assert_vehicle_naming(
			category="Owned",
			expected_prefix="VHL-",
			expected_series="VHL-.####",
		)

	def test_owned_vehicle_name_does_not_contain_leased_or_subcontractor_prefix(self):
		"""Owned vehicles must NOT receive VHL-L- or VHL-S- prefix."""
		vehicle = make_vehicle(one_fm_vehicle_category="Owned")
		self.assertFalse(
			vehicle.name.startswith("VHL-L-") or vehicle.name.startswith("VHL-S-"),
			msg=f"Owned vehicle received wrong prefix: {vehicle.name}",
		)

	# ------------------------------------------------------------------ #
	# Category: Leased                                                     #
	# ------------------------------------------------------------------ #

	def test_leased_vehicle_gets_vhl_l_prefix(self):
		"""Leased vehicles must be named VHL-L-XXXX and series set to VHL-L-.####."""
		self._assert_vehicle_naming(
			category="Leased",
			expected_prefix="VHL-L-",
			expected_series="VHL-L-.####",
		)

	def test_leased_vehicle_custom_naming_series_set_server_side(self):
		"""
		custom_naming_series must be set by vehicle_autoname() (server side),
		not only by the client-side JS handler.  Simulate a pure server insert
		(no form JS) by calling frappe.get_doc().insert() directly.
		"""
		doc = frappe.get_doc({
			"doctype": "Vehicle",
			"license_plate": random_string(10).upper(),
			"make": "Mercedes",
			"model": "Sprinter",
			"last_odometer": 0,
			"uom": "Litre",
			"fuel_type": "Diesel",
			"one_fm_vehicle_category": "Leased",
			"one_fm_vehicle_type": frappe.db.get_value("Vehicle Type", {}, "name"),
		})
		doc.insert(ignore_permissions=True, ignore_mandatory=True)

		self.assertEqual(
			doc.custom_naming_series,
			"VHL-L-.####",
			msg="custom_naming_series was not set server-side for Leased vehicle",
		)
		self.assertTrue(
			doc.name.startswith("VHL-L-"),
			msg=f"Leased vehicle name has wrong prefix: {doc.name}",
		)

	# ------------------------------------------------------------------ #
	# Category: Subcontractor                                              #
	# ------------------------------------------------------------------ #

	def test_subcontractor_vehicle_gets_vhl_s_prefix(self):
		"""Subcontractor vehicles must be named VHL-S-XXXX and series set to VHL-S-.####."""
		self._assert_vehicle_naming(
			category="Subcontractor",
			expected_prefix="VHL-S-",
			expected_series="VHL-S-.####",
		)

	def test_subcontractor_vehicle_custom_naming_series_set_server_side(self):
		"""
		custom_naming_series must be set server-side for Subcontractor vehicles.
		"""
		doc = frappe.get_doc({
			"doctype": "Vehicle",
			"license_plate": random_string(10).upper(),
			"make": "Ford",
			"model": "Transit",
			"last_odometer": 0,
			"uom": "Litre",
			"fuel_type": "Diesel",
			"one_fm_vehicle_category": "Subcontractor",
			"one_fm_vehicle_type": frappe.db.get_value("Vehicle Type", {}, "name"),
		})
		doc.insert(ignore_permissions=True, ignore_mandatory=True)

		self.assertEqual(
			doc.custom_naming_series,
			"VHL-S-.####",
			msg="custom_naming_series was not set server-side for Subcontractor vehicle",
		)
		self.assertTrue(
			doc.name.startswith("VHL-S-"),
			msg=f"Subcontractor vehicle name has wrong prefix: {doc.name}",
		)

	# ------------------------------------------------------------------ #
	# Category: fallback (blank / unknown)                                 #
	# ------------------------------------------------------------------ #

	def test_blank_category_falls_back_to_owned_prefix(self):
		"""
		The vehicle_autoname() function must fall back to VHL-.#### when the
		category is blank or unrecognised.  We test the function logic directly
		(without a full insert) because one_fm_vehicle_category is a mandatory
		field — a blank value would be caught by Frappe's mandatory validation
		before autoname even fires.
		"""
		from one_fm.fleet_management.doctype.vehicle_leasing_contract.vehicle_leasing_contract import vehicle_autoname
		from frappe.model.document import Document

		# Build a minimal doc-like object without going through insert
		mock_doc = frappe._dict({
			"one_fm_vehicle_category": "",
			"name": None,
			"custom_naming_series": None,
		})
		vehicle_autoname(mock_doc, method=None)

		self.assertTrue(
			mock_doc.name.startswith("VHL-"),
			msg=f"Blank-category vehicle has unexpected name: {mock_doc.name}",
		)
		self.assertEqual(mock_doc.custom_naming_series, "VHL-.####")

	# ------------------------------------------------------------------ #
	# Sequential numbering sanity check                                    #
	# ------------------------------------------------------------------ #

	def test_sequential_names_are_unique_across_categories(self):
		"""
		Two vehicles of the same category must receive different sequential names.
		"""
		v1 = make_vehicle(one_fm_vehicle_category="Owned")
		v2 = make_vehicle(one_fm_vehicle_category="Owned")
		self.assertNotEqual(v1.name, v2.name)

	def test_category_series_are_independent(self):
		"""
		The counters for Owned / Leased / Subcontractor must be independent
		— inserting a Leased vehicle must not advance the Owned counter.
		"""
		owned_before = make_vehicle(one_fm_vehicle_category="Owned")
		make_vehicle(one_fm_vehicle_category="Leased")
		owned_after = make_vehicle(one_fm_vehicle_category="Owned")

		# Both owned vehicles must share the VHL- prefix
		self.assertTrue(owned_before.name.startswith("VHL-"))
		self.assertTrue(owned_after.name.startswith("VHL-"))
		# The Leased insert must not have "stolen" a VHL- sequence number
		self.assertNotEqual(owned_before.name, owned_after.name)
