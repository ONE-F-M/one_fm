# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The total of every quota row's available quota."""

import json
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.pam_license_details import pam_license_details as module
from one_fm.grd.doctype.pam_license_details.pam_license_details import (
	available_quota,
	recount_quota_rows,
	total_available_quota,
)

FIELDNAME = "total_available_quota"
LICENSE = "ZZ-TEST-TOTAL-AVAILABLE-QUOTA"


def _rows(*figures):
	return [{"available_quota": figure} for figure in figures]


class TestTheSum(FrappeTestCase):
	def test_two_rows_of_one_hundred_total_two_hundred(self):
		"""AC2: Basic 100 and Heavy Driver 100."""
		self.assertEqual(total_available_quota(_rows("100", "100")), "200")

	def test_no_rows_total_zero(self):
		self.assertEqual(total_available_quota([]), "0")

	def test_blank_and_missing_figures_count_as_zero(self):
		self.assertEqual(total_available_quota(_rows("", None)), "0")
		self.assertEqual(total_available_quota([{}]), "0")

	def test_it_adds_unequal_rows(self):
		self.assertEqual(total_available_quota(_rows("57", "2", "10")), "69")

	def test_it_returns_a_whole_number_as_text(self):
		result = total_available_quota(_rows("1", "2"))
		self.assertIsInstance(result, str)
		self.assertNotIn(".", result)


class TestSavingALicence(FrappeTestCase):
	"""validate() run on an unsaved licence, with the two counts that read other
	doctypes mocked out so only the allocation drives the figures."""

	def _validate(self, doc):
		with (
			mock.patch.object(module, "count_quota_employees", return_value=0),
			mock.patch.object(module, "visas_issued_by_quota", return_value={}),
		):
			doc.validate()

	def _licence(self, *allocations):
		return frappe.get_doc(
			{
				"doctype": "PAM License Details",
				"quota_classification": [
					{"allocated_quota": allocation} for allocation in allocations
				],
			}
		)

	def test_two_rows_of_one_hundred_save_with_two_hundred(self):
		doc = self._licence("100", "100")
		self._validate(doc)
		self.assertEqual([row.available_quota for row in doc.quota_classification], ["100", "100"])
		self.assertEqual(doc.total_available_quota, "200")

	def test_removing_a_row_lowers_the_total(self):
		doc = self._licence("100", "100")
		self._validate(doc)
		doc.remove(doc.quota_classification[1])
		self._validate(doc)
		self.assertEqual(doc.total_available_quota, "100")

	def test_removing_every_row_gives_zero(self):
		doc = self._licence("100", "100")
		self._validate(doc)
		doc.set("quota_classification", [])
		self._validate(doc)
		self.assertEqual(doc.total_available_quota, "0")

	def test_updating_a_row_moves_the_total(self):
		doc = self._licence("100", "100")
		self._validate(doc)
		doc.quota_classification[0].allocated_quota = "150"
		self._validate(doc)
		self.assertEqual(doc.total_available_quota, "250")

	def test_it_is_summed_after_the_rows_are_derived(self):
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "grd", "doctype", "pam_license_details", "pam_license_details.py"
			)
		)
		validate = source.split("def validate(self):", 1)[1].split("\n\n", 1)[0]
		self.assertLess(
			validate.index("set_available_quota"), validate.index("total_available_quota")
		)


class TestTheRecount(FrappeTestCase):
	def _recount(self, rows):
		with (
			mock.patch.object(module.frappe.db, "exists", return_value=True),
			mock.patch.object(module.frappe, "get_all", return_value=rows),
			mock.patch.object(module, "count_quota_employees", return_value=0),
			mock.patch.object(module, "visas_issued_by_quota", return_value={}),
			mock.patch.object(module.frappe.db, "set_value") as set_value,
		):
			recount_quota_rows(LICENSE)
		return set_value

	def _row(self, name, allocated):
		return {
			"name": name,
			"type_of_quota": name,
			"allocated_quota": allocated,
			"number_of_transfer_requests": "",
		}

	def test_it_writes_the_parent_total_once_without_bumping_modified(self):
		set_value = self._recount([self._row("A", "100"), self._row("B", "100")])
		parent_writes = [
			call for call in set_value.call_args_list if call.args[0] == "PAM License Details"
		]
		self.assertEqual(len(parent_writes), 1)
		self.assertEqual(
			parent_writes[0],
			mock.call(
				"PAM License Details", LICENSE, FIELDNAME, "200", update_modified=False
			),
		)

	def test_the_total_is_written_after_the_rows(self):
		set_value = self._recount([self._row("A", "100")])
		self.assertEqual(set_value.call_args_list[-1].args[0], "PAM License Details")
		self.assertEqual(set_value.call_args_list[0].args[0], "Quota Classification")

	def test_a_licence_with_no_rows_is_written_as_zero(self):
		set_value = self._recount([])
		set_value.assert_called_once_with(
			"PAM License Details", LICENSE, FIELDNAME, "0", update_modified=False
		)

	def test_a_licence_that_is_not_there_writes_nothing(self):
		with (
			mock.patch.object(module.frappe.db, "exists", return_value=False),
			mock.patch.object(module.frappe.db, "set_value") as set_value,
		):
			recount_quota_rows(LICENSE)
		set_value.assert_not_called()

	def test_an_over_allocated_row_adds_nothing(self):
		"""The clamp at zero carries into the total: a row over its quota is 0, not
		a negative number taken off the others."""
		with (
			mock.patch.object(module, "count_quota_employees", return_value=12),
			mock.patch.object(module, "visas_issued_by_quota", return_value={}),
			mock.patch.object(module.frappe.db, "exists", return_value=True),
			mock.patch.object(
				module.frappe,
				"get_all",
				return_value=[self._row("A", "10"), self._row("B", "100")],
			),
			mock.patch.object(module.frappe.db, "set_value") as set_value,
		):
			recount_quota_rows(LICENSE)
		row_a = set_value.call_args_list[0]
		self.assertEqual(row_a.args[2]["available_quota"], "0")
		self.assertEqual(set_value.call_args_list[-1].args[3], "88")

	def test_an_over_allocated_row_reads_zero(self):
		row = {"allocated_quota": "10", "registered_numbers_of_employees": "12"}
		self.assertEqual(available_quota(row), "0")
		self.assertEqual(total_available_quota([{"available_quota": available_quota(row)}]), "0")


class TestTheFieldDefinition(FrappeTestCase):
	def setUp(self):
		self.definition = json.loads(
			frappe.read_file(
				frappe.get_app_path(
					"one_fm", "grd", "doctype", "pam_license_details", "pam_license_details.json"
				)
			)
		)
		self.fields = {f["fieldname"]: f for f in self.definition["fields"]}

	def test_the_field_is_data_with_the_ba_label_and_description(self):
		field = self.fields[FIELDNAME]
		self.assertEqual(field["fieldtype"], "Data")
		self.assertEqual(field["label"], "Total Available Quota")
		self.assertEqual(
			field["description"],
			"Total Number of Quota Available in Each PAM File, Including All Types of Quota",
		)

	def test_it_is_left_writable_with_no_default_as_the_ba_site_has_it(self):
		field = self.fields[FIELDNAME]
		self.assertNotIn("read_only", field)
		self.assertNotIn("default", field)

	def test_the_breaks_are_in_place(self):
		self.assertEqual(self.fields["column_break_ameo"]["fieldtype"], "Column Break")
		self.assertEqual(self.fields["section_break_uxvr"]["fieldtype"], "Section Break")

	def test_they_sit_between_the_headcount_and_the_quota_table(self):
		order = self.definition["field_order"]
		start = order.index("total_number_of_employees")
		self.assertEqual(
			order[start : start + 5],
			[
				"total_number_of_employees",
				"column_break_ameo",
				FIELDNAME,
				"section_break_uxvr",
				"quota_classification",
			],
		)

	def test_modified_is_bumped_so_migrate_picks_it_up(self):
		self.assertGreater(self.definition["modified"], "2026-09-30 12:00:00.000000")

	def test_every_field_in_the_order_is_defined(self):
		self.assertEqual(set(self.definition["field_order"]), set(self.fields))

	def test_none_of_the_ba_noise_came_across(self):
		for field in (self.fields[FIELDNAME], self.fields["section_break_uxvr"]):
			self.assertNotIn("row_format", field)
			self.assertNotIn("migration_hash", field)


class TestTheBackfill(FrappeTestCase):
	def test_the_patch_is_registered_after_model_sync(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		name = "one_fm.patches.v15_0.backfill_pam_license_total_available_quota"
		self.assertIn(name, patches)
		self.assertGreater(patches.index(name), patches.index("[post_model_sync]"))

	def test_it_recounts_every_licence(self):
		from one_fm.patches.v15_0 import backfill_pam_license_total_available_quota as patch

		with (
			mock.patch.object(patch.frappe, "get_all", return_value=["A", "B"]),
			mock.patch.object(patch, "recount_quota_rows") as recount,
		):
			patch.execute()
		self.assertEqual([call.args[0] for call in recount.call_args_list], ["A", "B"])
