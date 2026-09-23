# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002769: how many of a licence's employees are registered in each quota type."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.pam_license_details import pam_license_details as module
from one_fm.grd.doctype.pam_license_details.pam_license_details import (
	count_quota_employees,
	recount_quota_rows,
)

FIELDNAME = "registered_numbers_of_employees"
SOURCE = frappe.get_app_path(
	"one_fm", "grd", "doctype", "pam_license_details", "pam_license_details.py"
)


class TestTheCountItAsks(FrappeTestCase):
	def test_a_row_with_no_quota_type_counts_nobody(self):
		"""Falling back to everyone on the licence would put the whole workforce in
		whichever row an operator had not finished configuring, and it would look like a
		real figure."""
		self.assertEqual(count_quota_employees("2921143", None), 0)
		self.assertEqual(count_quota_employees("2921143", ""), 0)

	def test_a_licence_with_no_number_counts_nobody(self):
		self.assertEqual(count_quota_employees(None, "Basic"), 0)

	def test_it_runs_against_this_site(self):
		self.assertIsInstance(count_quota_employees("2921143", "Basic"), int)

	def test_it_joins_the_designation_for_the_quota_type(self):
		"""The quota type is not on the employee - it is on the PAM designation they hold,
		so the join is what makes the count possible at all."""
		block = SOURCE and frappe.read_file(SOURCE).split("def count_quota_employees", 1)[1]
		self.assertIn("Designation.quota_type == quota_type", block)
		self.assertIn("Employee.one_fm_pam_designation == Designation.name", block)

	def test_it_counts_the_licence_and_the_residency_like_every_other_figure(self):
		block = frappe.read_file(SOURCE).split("def count_quota_employees", 1)[1]
		self.assertIn("Employee.pam_file_number == license_number", block)
		self.assertIn("Employee.under_company_residency == 1", block)


class _Recorder:
	def __init__(self, licenses=(), rows=(), count=5):
		self.licenses = list(licenses)
		self.rows = list(rows)
		self.count = count
		self.written = []
		self.counted = []

	def get_all(self, doctype, filters=None, pluck=None, fields=None):
		if doctype == "PAM License Details":
			return list(self.licenses)
		return [dict(row) for row in self.rows]

	def set_value(self, doctype, name, values, update_modified=None):
		# WI-002771 writes the registered headcount and the issued visas in one call, so
		# the recorder takes the dict rather than a single fieldname.
		self.written.append((doctype, name, values, update_modified))

	def count_quota_employees(self, license_number, quota_type):
		self.counted.append((license_number, quota_type))
		return self.count

	def visas_issued_by_quota(self, license_name, license_number):
		return {}


class TestHowTheRowsAreWritten(FrappeTestCase):
	def _recount(self, licenses, rows, count=5):
		recorder = _Recorder(licenses, rows, count)
		originals = (
			module.frappe.get_all,
			module.frappe.db.set_value,
			module.count_quota_employees,
			module.visas_issued_by_quota,
		)
		module.frappe.get_all = recorder.get_all
		module.frappe.db.set_value = recorder.set_value
		module.count_quota_employees = recorder.count_quota_employees
		module.visas_issued_by_quota = recorder.visas_issued_by_quota
		try:
			recount_quota_rows("2921143")
		finally:
			(
				module.frappe.get_all,
				module.frappe.db.set_value,
				module.count_quota_employees,
				module.visas_issued_by_quota,
			) = originals
		return recorder

	def test_it_writes_the_headcount_onto_every_row(self):
		recorder = self._recount(
			["ONE FM Private"],
			[{"name": "row-1", "type_of_quota": "Basic"}, {"name": "row-2", "type_of_quota": "Light Driver"}],
		)
		self.assertEqual(
			[(row[1], row[2][FIELDNAME]) for row in recorder.written],
			[("row-1", "5"), ("row-2", "5")],
		)

	def test_it_counts_each_quota_type_once(self):
		"""Two licences carrying the same number hold the same employees."""
		recorder = self._recount(
			["ONE FM Private", "T4"],
			[{"name": "row-1", "type_of_quota": "Basic"}],
		)
		self.assertEqual(recorder.counted, [("2921143", "Basic")])
		self.assertEqual(len(recorder.written), 2)

	def test_it_does_not_bump_modified(self):
		recorder = self._recount(["ONE FM Private"], [{"name": "row-1", "type_of_quota": "Basic"}])
		self.assertIs(recorder.written[0][3], False)

	def test_a_number_no_licence_holds_writes_nothing(self):
		self.assertEqual(self._recount([], []).written, [])

	def test_a_missing_row_is_not_invented(self):
		"""A quota row exists because PAM allocated this licence a quota of that type.
		Inventing one from the employees who happen to hold such a designation would state
		an allocation nobody granted - unlike the sector rows, which PAM counts whether
		they are configured or not."""
		block = frappe.read_file(SOURCE).split("def recount_quota_rows", 1)[1]
		self.assertNotIn("add_quota_row", block)
		self.assertIn("inventing one", block.replace("\n", " ").lower())


class TestWhenItIsRecounted(FrappeTestCase):
	def setUp(self):
		self.source = frappe.read_file(SOURCE)

	def test_a_transfer_recounts_the_quota_rows(self):
		block = self.source.split("def update_counts_from_employee", 1)[1]
		self.assertIn("recount_quota_rows(license_number)", block)

	def test_moving_a_designation_between_quotas_recounts_too(self):
		"""The quota type is on the designation, so moving one moves everybody holding it -
		and no Employee is saved when that happens."""
		block = self.source.split("def update_counts_from_designation", 1)[1]
		self.assertIn('doc.has_value_changed("quota_type")', block)
		self.assertIn("recount_quota_rows(number)", block)

	def test_a_sector_move_still_recounts_the_sectors(self):
		"""The two groupings are independent; one must not switch the other off."""
		block = self.source.split("def update_counts_from_designation", 1)[1]
		self.assertIn('doc.has_value_changed("occupational_sector")', block)
		self.assertIn("recount_sector(number, sector)", block)

	def test_a_designation_that_moved_neither_is_left_alone(self):
		block = self.source.split("def update_counts_from_designation", 1)[1]
		self.assertIn("if not sector_moved and not quota_moved:", block)

	def test_saving_a_licence_derives_the_rows(self):
		self.assertIn("self.set_quota_registrations()", self.source)


class TestTheFieldIsDerived(FrappeTestCase):
	def test_nobody_types_it(self):
		definition = json.loads(
			frappe.read_file(
				frappe.get_app_path(
					"one_fm",
					"grd",
					"doctype",
					"quota_classification",
					"quota_classification.json",
				)
			)
		)
		field = next(f for f in definition["fields"] if f["fieldname"] == FIELDNAME)
		self.assertEqual(field["read_only"], 1)

	def test_the_allocated_quota_is_still_typed(self):
		"""It is the one figure on the row PAM sets and an operator enters."""
		definition = json.loads(
			frappe.read_file(
				frappe.get_app_path(
					"one_fm",
					"grd",
					"doctype",
					"quota_classification",
					"quota_classification.json",
				)
			)
		)
		field = next(f for f in definition["fields"] if f["fieldname"] == "allocated_quota")
		self.assertNotEqual(field.get("read_only"), 1)
